"""Core del agente de Clínica Benitez.

Instancia `ChatOllama` con el modelo `agente-clinica`, conecta las herramientas
con `bind_tools` y ejecuta un bucle manual de tool-calling compatible con
LangChain 1.x. Solo devuelve la respuesta final: el razonamiento del modelo
nunca se expone al cliente.
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_ollama import ChatOllama

from app.agent.tools import AGENT_TOOLS, TOOL_MAP, buscar_protocolo

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "agente-clinica"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
MAX_TOOL_ROUNDS = 4

_THINKING_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.IGNORECASE | re.DOTALL)

_INVALID_UNICODE_PATTERNS = (
    (re.compile(r"\\u00fu"), "ú"),
    (re.compile(r"\\u00f(?![0-9a-fA-F])"), "ú"),
    (re.compile(r"\\u00e(?![0-9a-fA-F])"), "é"),
    (re.compile(r"\\u00a(?![0-9a-fA-F])"), "á"),
    (re.compile(r"\\u00i"), "í"),
    (re.compile(r"\\u00o"), "ó"),
    (re.compile(r"\\u00u"), "ú"),
    (re.compile(r"\\u00n"), "ñ"),
)

_EMERGENCY_TERMS = (
    "dolor de pecho",
    "dolor en el pecho",
    "duele el pecho",
    "dificultad para respirar",
    "no puedo respirar",
    "falta de aire",
    "desmayo",
    "desmaye",
    "convulsion",
    "convulsiones",
    "sangrado abundante",
    "infarto",
    "paro cardiaco",
    "acv",
    "derrame cerebral",
    "suicidio",
    "me quiero matar",
    "emergencia",
)

_EMERGENCY_PREFIX = (
    "Acudí ahora a la guardia o llamá al servicio de emergencias."
)

_TOOL_TEXT_FALLBACK = (
    "No encontré información institucional sobre esa consulta o no pude "
    "procesarla correctamente. ¿Podrías reformularla?"
)

_NO_PROTOCOL_PREFIX = "No encontré un protocolo específico documentado"

_NO_PROTOCOL_ANSWER = (
    "No encontré un protocolo específico documentado para ese procedimiento en la "
    "Clínica Benitez. La documentación disponible no contiene pautas específicas "
    "para ese caso. Si necesitás, puedo registrar una derivación administrativa "
    "para que lo evalúe el área correspondiente."
)

_INTERNAL_TERM_REPLACEMENTS = {
    "buscar_protocolo": "la búsqueda documental",
    "consultar_contacto_area": "la consulta de contactos",
    "derivar_solicitud": "la derivación",
}

_GREETING_RE = re.compile(
    r"^(hola|buen(?:os|as)\s+(?:d[ií]as|tardes|noches)|hey|qu[eé]\s+tal)[!. ]*$",
    re.IGNORECASE,
)

_GREETING_RESPONSE = (
    "¡Hola! Soy el Agente Clínica Benitez, asistente administrativo. "
    "Puedo ayudarte con horarios, trámites, requisitos, contactos y derivaciones. "
    "¿En qué puedo ayudarte?"
)

_HELP_RE = re.compile(
    r"^[\s¿¡]*(qu[eé] hago|qu[eé] debo hacer|que debo hacer|c[oó]mo me ayudas|"
    r"c[oó]mo pod[eé]s ayudar(?:me)?|en qu[eé] me puedes ayudar|"
    r"qu[eé] pod[eé]s hacer|qu[eé] puedo hacer|ayuda)\b",
    re.IGNORECASE,
)

_AMBIGUITY_TERMS = ("disponibilidad", "horario", "turno", "servicio", "atencion")

_SERVICE_HINTS = (
    "diagnostico",
    "imagenes",
    "laboratorio",
    "cardiologia",
    "quirurgico",
    "cirugia",
    "guardia",
    "auditoria",
    "facturacion",
    "gestion de pacientes",
    "direccion medica",
    "rayos",
    "resonancia",
    "tomografia",
    "extraccion",
    "especialidad",
    "consultorio",
    "derivacion",
    "traslado",
    "ambulancia",
    "internacion",
    "obras sociales",
)

_AMBIGUITY_RESPONSE = (
    "¿Qué servicio o área te interesa? Por ejemplo: Diagnóstico por Imágenes, "
    "Laboratorio de Análisis Clínicos, Cardiología o Centro Quirúrgico. "
    "Así puedo darte la información correcta."
)

_CONTACT_INTENT_TERMS = (
    "contacto",
    "telefono",
    "interno",
    "correo",
    "extension",
    "comunicar",
    "llamar",
    "derivacion",
)

_SYSTEM_TOOL_RULES = (
    "REGLAS OBLIGATORIAS DE OPERACIÓN:\n"
    "- La documentación institucional se recupera automáticamente y se te entrega "
    "como CONTEXTO INSTITUCIONAL. Usala como fuente principal para horarios, "
    "servicios, trámites, requisitos, protocolos y coberturas. No invoques "
    "herramientas para buscar documentación.\n"
    "- Si los fragmentos del CONTEXTO hablan de traslados o trámites generales pero "
    "NO mencionan específicamente la especialidad o procedimiento consultado (por "
    "ejemplo, trasplantes cardíacos), aclará primero que la Clínica Benitez no cuenta "
    "con un protocolo específico documentado para ese procedimiento, antes de "
    "mencionar las pautas generales de derivación si corresponden.\n"
    "- Si la documentación SÍ menciona explícitamente la práctica consultada (por "
    "ejemplo, resonancias magnéticas en la autorización de obras sociales), usá esos "
    "pasos y no respondas que falta información.\n"
    "- Usá consultar_contacto_area SOLO si el usuario pide explícitamente un "
    "contacto, teléfono, interno, correo o cómo comunicarse. No la uses para "
    "horarios, ubicación o disponibilidad que ya estén en el CONTEXTO.\n"
    "- Consulta clínica, síntomas, medicación, diagnóstico o emergencia: llamá a "
    "derivar_solicitud antes de responder; no brindes orientación médica.\n"
    "- Si la consulta es ambigua o no especifica el servicio, área o tipo de trámite, "
    "pedí aclaración ANTES de llamar herramientas o responder.\n"
    "- Si llamás a derivar_solicitud, incluí en la respuesta el número de ticket devuelto.\n"
    "- Si es una emergencia, tu PRIMERA frase debe indicar acudir a la guardia o llamar "
    "al servicio de emergencias, antes de cualquier otra aclaración.\n"
    "- Saludos simples, despedidas o preguntas de identidad: respondé directamente SIN "
    "usar herramientas.\n"
    "- Si el usuario pregunta qué hacés, cómo podés ayudarlo o qué debe hacer, "
    "presentate con un tono amable y explicá brevemente que sos el Asistente "
    "Administrativo de la Clínica Benitez y que podés brindar horarios, requisitos, "
    "contactos internos o generar derivaciones.\n"
    "- No menciones nombres de herramientas, funciones, modelos, bases vectoriales ni "
    "detalles técnicos. Respondé como asistente institucional.\n"
    "- No inventes horarios, contactos, tickets ni resultados de herramientas.\n"
)


def _normalize_text(text: str) -> str:
    """Minúsculas, sin acentos, para comparaciones deterministas."""
    decomposed = unicodedata.normalize("NFD", text or "")
    without_accents = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def _is_emergency(message: str) -> bool:
    normalized = _normalize_text(message)
    return any(term in normalized for term in _EMERGENCY_TERMS)


def _is_vague_service_request(message: str) -> bool:
    """Detecta consultas de disponibilidad/horario sin especificar el servicio."""
    normalized = _normalize_text(message)
    if not any(term in normalized for term in _AMBIGUITY_TERMS):
        return False
    return not any(term in normalized for term in _SERVICE_HINTS)


def _mentions_contact_intent(message: str) -> bool:
    normalized = _normalize_text(message)
    return any(term in normalized for term in _CONTACT_INTENT_TERMS)


def _apply_no_protocol_guard(
    answer: str,
    no_specific_protocol: bool,
    tools_used: list[str],
) -> str:
    """Inyecta el aviso solo si no hubo una acción de contacto/derivación."""
    only_rag_or_none = not tools_used or set(tools_used) <= {"buscar_protocolo"}
    if (
        no_specific_protocol
        and only_rag_or_none
        and "protocolo especifico" not in _normalize_text(answer)
    ):
        return _NO_PROTOCOL_ANSWER
    return answer


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\wáéíóúñü]+\b", text, flags=re.IGNORECASE))


def _previous_user_content(
    history: Sequence[Mapping[str, Any]] | None,
) -> str | None:
    for item in reversed(history or []):
        if not isinstance(item, Mapping):
            continue
        if str(item.get("role", "")).lower() not in ("user", "human"):
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return None


def _build_search_query(
    message: str,
    history: Sequence[Mapping[str, Any]] | None,
) -> str:
    """Combina el turno anterior si el mensaje actual es muy corto."""
    if _count_words(message) > 4:
        return message.strip()

    previous = _previous_user_content(history)
    if not previous or _GREETING_RE.match(previous):
        return message.strip()

    return f"{previous} {message.strip()}"


def _retrieve_context(query: str) -> tuple[str | None, bool]:
    """Ejecuta la recuperación documental antes de invocar al LLM."""
    try:
        result = buscar_protocolo.invoke({"query": query})
    except Exception:  # pragma: no cover - defensivo
        logger.exception("Falló la recuperación proactiva de documentación")
        return None, False

    if not isinstance(result, str) or not result.strip():
        return None, False
    if result.startswith("Error:"):
        return None, False

    return result, result.startswith(_NO_PROTOCOL_PREFIX)


def _sanitize_internal_terms(answer: str) -> str:
    """Evita que el usuario final vea nombres de herramientas internas."""
    for name, replacement in _INTERNAL_TERM_REPLACEMENTS.items():
        answer = re.sub(
            rf"{re.escape(name)}\s*\([^)]*\)",
            replacement,
            answer,
            flags=re.IGNORECASE,
        )
        answer = re.sub(
            re.escape(name),
            replacement,
            answer,
            flags=re.IGNORECASE,
        )
    return answer


def _ensure_emergency_ticket(
    message: str,
    tools_used: list[str],
    tool_results: list[str],
) -> None:
    """Registra una derivación si la emergencia no generó ticket por el modelo."""
    if not _is_emergency(message) or "derivar_solicitud" in tools_used:
        return

    tool = TOOL_MAP.get("derivar_solicitud")
    if tool is None:
        return

    try:
        result = tool.invoke(
            {
                "motivo": message.strip()[:300],
                "area": "urgencias",
            }
        )
    except Exception:  # pragma: no cover - defensivo
        logger.exception("No se pudo registrar la derivación de emergencia")
        return

    tools_used.append("derivar_solicitud")
    tool_results.append(str(result))


def _ensure_contact_answer(answer: str, contact_result: str | None) -> str:
    """Si el modelo omitió el interno recuperado, devuelve el contacto real."""
    if not contact_result:
        return answer

    match = re.search(r"Int\.\s*(\d+)", contact_result)
    if match and match.group(1) not in answer:
        return contact_result
    return answer


def _finalize_answer(
    message: str,
    answer: str,
    tools_used: list[str],
    tool_results: list[str],
    no_specific_protocol: bool,
    contact_result: str | None,
) -> str:
    _ensure_emergency_ticket(message, tools_used, tool_results)
    answer = _ensure_contact_answer(answer, contact_result)
    answer = _apply_no_protocol_guard(answer, no_specific_protocol, tools_used)
    answer = _apply_safety_guards(message, answer, tool_results)
    return _sanitize_internal_terms(answer)


def _apply_safety_guards(
    user_message: str,
    answer: str,
    tool_results: list[str],
) -> str:
    """Garantiza ticket visible y prioridad de la indicación de emergencia."""
    for result in reversed(tool_results):
        if "Derivación registrada correctamente" not in result:
            continue
        match = re.search(r"Ticket:\s*(\S+)", result)
        if match and match.group(1) not in answer:
            answer = f"{answer}\n\nTicket de derivación: {match.group(1)}"
        break

    if _is_emergency(user_message):
        inicio = _normalize_text(answer[:120])
        if "guardia" not in inicio and "emergencia" not in inicio:
            answer = f"{_EMERGENCY_PREFIX}\n\n{answer}"
    return answer


@dataclass(slots=True)
class AgentResult:
    """Resultado de una ejecución del agente."""

    respuesta: str
    herramientas_usadas: list[str] = field(default_factory=list)
    pasos: int = 0


def _build_llm() -> ChatOllama:
    return ChatOllama(
        model=os.getenv("OLLAMA_CHAT_MODEL", DEFAULT_MODEL),
        base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL),
        temperature=0.2,
    )


def _answer_onboarding(message: str) -> str:
    """Responde preguntas generales sin RAG y sin tools."""
    try:
        response = _build_llm().invoke(
            [
                SystemMessage(content=_SYSTEM_TOOL_RULES),
                HumanMessage(content=message.strip()),
            ]
        )
        answer = _content_to_text(response.content)
        if answer:
            return _sanitize_internal_terms(answer)
    except Exception:  # pragma: no cover - defensivo
        logger.exception("Falló la respuesta de onboarding")

    return _GREETING_RESPONSE


@lru_cache(maxsize=1)
def get_agent():
    """Devuelve el modelo con las herramientas enlazadas (singleton)."""
    return _build_llm().bind_tools(AGENT_TOOLS)


def _content_to_text(content: Any) -> str:
    """Normaliza `content` (str o bloques) y elimina etiquetas de razonamiento."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, Mapping):
                block_type = block.get("type")
                if block_type in (None, "text", "output_text"):
                    value = block.get("text")
                    if isinstance(value, str):
                        parts.append(value)
        text = "\n".join(parts)
    else:
        text = str(content or "")
    return _THINKING_RE.sub("", text).strip()


def _repair_invalid_unicode_escapes(text: str) -> str:
    for pattern, replacement in _INVALID_UNICODE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _extract_json_object(text: str) -> Mapping[str, Any] | None:
    """Extrae el primer objeto JSON válido embebido en texto.

    Soporta JSON dentro de bloques Markdown y texto adicional alrededor.
    """
    text = _repair_invalid_unicode_escapes(text)

    for start, character in enumerate(text):
        if character != "{":
            continue

        depth = 0
        in_string = False
        escaped = False

        for index in range(start, len(text)):
            current = text[index]

            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue

            if current == '"':
                in_string = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    try:
                        candidate = json.loads(text[start : index + 1])
                    except json.JSONDecodeError:
                        break
                    return candidate if isinstance(candidate, Mapping) else None

    return None


def _parse_text_tool_call(text: str) -> dict[str, Any] | None:
    """Convierte un JSON crudo en una tool call si la herramienta está registrada."""
    payload = _extract_json_object(text)
    if not payload:
        return None

    name = payload.get("name")
    if not isinstance(name, str) or name not in TOOL_MAP:
        return None

    raw_args = payload.get("parameters", payload.get("arguments"))
    if isinstance(raw_args, str):
        try:
            raw_args = json.loads(raw_args)
        except json.JSONDecodeError:
            return None

    if not isinstance(raw_args, Mapping):
        return None

    return {
        "name": name,
        "args": dict(raw_args),
        "id": f"fallback-{uuid.uuid4().hex[:8]}",
        "type": "tool_call",
    }


def _looks_like_tool_payload(text: str) -> bool:
    """Detecta un intento de tool call en texto para no exponer JSON crudo."""
    stripped = text.strip()
    if "{" not in stripped:
        return False
    lowered = stripped.lower()
    return (
        '"name"' in lowered
        or '"parameters"' in lowered
        or '"arguments"' in lowered
    )


def _history_to_messages(history: Sequence[Mapping[str, Any]] | None) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in history or []:
        if isinstance(item, BaseMessage):
            messages.append(item)
            continue
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("role") or item.get("type") or "").lower()
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if role in ("user", "human"):
            messages.append(HumanMessage(content=content.strip()))
        elif role in ("assistant", "ai"):
            messages.append(AIMessage(content=content.strip()))
        # Se ignoran roles system/tool enviados por el cliente: el SYSTEM prompt
        # vive en el Modelfile y las tools solo las ejecuta este módulo.
    return messages


def _final_answer_without_tools(messages: list[BaseMessage]) -> str:
    """Último recurso si se agota el presupuesto de rondas de herramientas."""
    try:
        response = _build_llm().invoke(
            [
                *messages,
                HumanMessage(
                    content=(
                        "Respondé ahora al usuario con la información disponible, "
                        "sin usar más herramientas. Sé breve y en español."
                    )
                ),
            ]
        )
        return _content_to_text(response.content)
    except Exception:  # pragma: no cover - depende del runtime de Ollama
        logger.exception("Falló la respuesta final sin herramientas")
        return (
            "No pude completar la solicitud en este intento. Por favor, reformulá "
            "la consulta o comunicate con Atención al Público."
        )


def run_agent(
    message: str,
    history: Sequence[Mapping[str, Any]] | None = None,
) -> AgentResult:
    """Ejecuta al agente con historial y devuelve la respuesta final.

    Args:
        message: Consulta actual del usuario.
        history: Mensajes previos con forma ``{"role": "user"|"assistant",
            "content": "..."}``.
    """
    if not message or not message.strip():
        raise ValueError("El mensaje del usuario no puede estar vacío.")

    if _GREETING_RE.match(message.strip()):
        return AgentResult(
            respuesta=_GREETING_RESPONSE,
            herramientas_usadas=[],
            pasos=0,
        )

    if _HELP_RE.match(message.strip()):
        return AgentResult(
            respuesta=_answer_onboarding(message),
            herramientas_usadas=[],
            pasos=1,
        )

    if _is_vague_service_request(message):
        return AgentResult(
            respuesta=_AMBIGUITY_RESPONSE,
            herramientas_usadas=[],
            pasos=0,
        )

    emergency = _is_emergency(message)
    rag_result: str | None = None
    no_specific_protocol = False

    if not emergency:
        search_query = _build_search_query(message, history)
        rag_result, no_specific_protocol = _retrieve_context(search_query)

    messages: list[BaseMessage] = [SystemMessage(content=_SYSTEM_TOOL_RULES)]

    if rag_result:
        messages.append(
            SystemMessage(
                content=(
                    "CONTEXTO INSTITUCIONAL RECUPERADO "
                    "(fuente principal; no menciones herramientas ni detalles "
                    "técnicos):\n\n"
                    f"{rag_result}"
                )
            )
        )

    messages.extend(_history_to_messages(history))
    messages.append(HumanMessage(content=message.strip()))

    agent = get_agent()
    tools_used: list[str] = (
        ["buscar_protocolo"]
        if rag_result and "[Fragmento" in rag_result
        else []
    )
    tool_results: list[str] = []
    contact_result: str | None = None

    for step in range(1, MAX_TOOL_ROUNDS + 1):
        response = agent.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        answer_text = _content_to_text(response.content)

        if not tool_calls:
            fallback_call = _parse_text_tool_call(answer_text)
            if fallback_call:
                logger.warning(
                    "Tool call embebido en texto detectado: %s",
                    fallback_call["name"],
                )
                # Se reemplaza el JSON crudo por un AIMessage estructurado para
                # respetar el protocolo de tool-calling y no exponerlo al usuario.
                messages[-1] = AIMessage(content="", tool_calls=[fallback_call])
                tool_calls = [fallback_call]
            elif _looks_like_tool_payload(answer_text):
                logger.warning(
                    "No se pudo interpretar una tool call embebida; se devuelve "
                    "un mensaje seguro."
                )
                answer = _finalize_answer(
                    message,
                    _TOOL_TEXT_FALLBACK,
                    tools_used,
                    tool_results,
                    no_specific_protocol,
                    contact_result,
                )
                return AgentResult(
                    respuesta=answer,
                    herramientas_usadas=tools_used,
                    pasos=step,
                )

        if not tool_calls:
            answer = answer_text
            if not answer:
                answer = (
                    "No pude generar una respuesta. ¿Podés reformular la consulta "
                    "con un poco más de detalle?"
                )
            answer = _finalize_answer(
                message,
                answer,
                tools_used,
                tool_results,
                no_specific_protocol,
                contact_result,
            )
            return AgentResult(
                respuesta=answer,
                herramientas_usadas=tools_used,
                pasos=step,
            )

        for call in tool_calls:
            name = str(call.get("name") or "")
            args = call.get("args") or {}
            tool = TOOL_MAP.get(name)
            logger.info("Paso %d: herramienta=%s args=%s", step, name, args)

            if (
                name == "consultar_contacto_area"
                and rag_result
                and not _mentions_contact_intent(message)
            ):
                logger.info(
                    "Se omite la consulta de contacto: no fue solicitada y el "
                    "contexto institucional ya responde."
                )
                result = (
                    "No es necesario consultar contactos para esta consulta. "
                    "Respondé usando el CONTEXTO INSTITUCIONAL."
                )
            elif tool is None:
                result = f"Error: la herramienta '{name}' no existe."
            else:
                try:
                    result = tool.invoke(args)
                    tools_used.append(name)
                except Exception as exc:  # pragma: no cover - defensivo
                    logger.exception("Error ejecutando la herramienta %s", name)
                    result = f"Error al ejecutar la herramienta '{name}': {exc}"

            result_text = str(result)
            if name == "consultar_contacto_area" and "Teléfono interno:" in result_text:
                contact_result = result_text
            if result_text.startswith(_NO_PROTOCOL_PREFIX):
                no_specific_protocol = True
            tool_results.append(result_text)
            messages.append(
                ToolMessage(
                    content=result_text,
                    tool_call_id=str(call.get("id") or name),
                )
            )

    logger.warning("Se agotaron las %d rondas de herramientas", MAX_TOOL_ROUNDS)
    answer = _finalize_answer(
        message,
        _final_answer_without_tools(messages),
        tools_used,
        tool_results,
        no_specific_protocol,
        contact_result,
    )
    return AgentResult(
        respuesta=answer,
        herramientas_usadas=tools_used,
        pasos=MAX_TOOL_ROUNDS,
    )


__all__ = ["AgentResult", "run_agent", "get_agent"]
