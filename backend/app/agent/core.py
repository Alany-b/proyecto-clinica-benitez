"""Core del agente de Clínica Benitez.

Instancia `ChatOllama` con el modelo `agente-clinica`, conecta las herramientas
con `bind_tools` y ejecuta un bucle manual de tool-calling compatible con
LangChain 1.x. Solo devuelve la respuesta final: el razonamiento del modelo
nunca se expone al cliente.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
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

from app.agent.tools import TOOL_MAP, TOOLS

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "agente-clinica"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
MAX_TOOL_ROUNDS = 4

_THINKING_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.IGNORECASE | re.DOTALL)

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

_SYSTEM_TOOL_RULES = (
    "REGLAS OBLIGATORIAS DE OPERACIÓN:\n"
    "- Consulta institucional (horarios, servicios, trámites, requisitos, protocolos, "
    "coberturas): llamá a buscar_protocolo antes de responder.\n"
    "- Consulta sobre el contacto de un área: llamá a consultar_contacto_area.\n"
    "- Consulta clínica, síntomas, medicación, diagnóstico o emergencia: llamá a "
    "derivar_solicitud antes de responder; no brindes orientación médica.\n"
    "- Si llamás a derivar_solicitud, incluí en la respuesta el número de ticket devuelto.\n"
    "- Si es una emergencia, tu PRIMERA frase debe indicar acudir a la guardia o llamar "
    "al servicio de emergencias, antes de cualquier otra aclaración.\n"
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


@lru_cache(maxsize=1)
def get_agent():
    """Devuelve el modelo con las herramientas enlazadas (singleton)."""
    return _build_llm().bind_tools(TOOLS)


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

    messages: list[BaseMessage] = [SystemMessage(content=_SYSTEM_TOOL_RULES)]
    messages.extend(_history_to_messages(history))
    messages.append(HumanMessage(content=message.strip()))

    agent = get_agent()
    tools_used: list[str] = []
    tool_results: list[str] = []

    for step in range(1, MAX_TOOL_ROUNDS + 1):
        response = agent.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            answer = _content_to_text(response.content)
            if not answer:
                answer = (
                    "No pude generar una respuesta. ¿Podés reformular la consulta "
                    "con un poco más de detalle?"
                )
            answer = _apply_safety_guards(message, answer, tool_results)
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

            if tool is None:
                result = f"Error: la herramienta '{name}' no existe."
            else:
                try:
                    result = tool.invoke(args)
                    tools_used.append(name)
                except Exception as exc:  # pragma: no cover - defensivo
                    logger.exception("Error ejecutando la herramienta %s", name)
                    result = f"Error al ejecutar la herramienta '{name}': {exc}"

            tool_results.append(str(result))
            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=str(call.get("id") or name),
                )
            )

    logger.warning("Se agotaron las %d rondas de herramientas", MAX_TOOL_ROUNDS)
    answer = _final_answer_without_tools(messages)
    answer = _apply_safety_guards(message, answer, tool_results)
    return AgentResult(
        respuesta=answer,
        herramientas_usadas=tools_used,
        pasos=MAX_TOOL_ROUNDS,
    )


__all__ = ["AgentResult", "run_agent", "get_agent"]
