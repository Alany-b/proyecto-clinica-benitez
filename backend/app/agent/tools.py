"""Herramientas del agente de Clínica Benitez.

Incluye recuperación híbrida (vectorial + léxica) sobre la documentación
institucional, consulta de contactos y registro simulado de derivaciones.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from datetime import datetime
from typing import Annotated

from langchain_core.documents import Document
from langchain_core.tools import tool

from app.rag.indexer import get_vector_store, search_protocols

_LEXICAL_LIMIT = 3
_VECTOR_LIMIT = 6
_LEXICAL_MIN_SCORE = 2.0

_STOPWORDS = {
    "a", "al", "algo", "algun", "alguna", "algunas", "alguno", "algunos",
    "ante", "antes", "aqui", "asi", "aun", "cada", "como", "con", "contra",
    "cual", "cuales", "cuando", "de", "del", "desde", "donde", "dos", "el",
    "ella", "ellas", "ellos", "en", "entre", "era", "es", "esa", "ese",
    "eso", "esta", "estan", "este", "esto", "estos", "fue", "gracias",
    "ha", "hasta", "hay", "hola", "la", "las", "le", "les", "lo", "los",
    "mas", "me", "mi", "mis", "mucho", "muy", "necesito", "no", "nos",
    "o", "otra", "otro", "para", "pero", "poco", "por", "porque", "que",
    "quien", "quienes", "se", "segun", "ser", "si", "sin", "sobre", "son",
    "su", "sus", "te", "tengo", "tiene", "todo", "todos", "tu", "tus",
    "un", "una", "unas", "uno", "unos", "usted", "ustedes", "y", "ya",
}

_GENERIC_QUERY_TERMS = {
    "protocolo", "protocolos", "procedimiento", "procedimientos",
    "consulta", "consultas", "informacion", "documentacion", "necesito",
    "quiero", "saber", "servicio", "servicios", "area", "areas", "clinica",
    "benitez", "realiza", "realizan", "atienden", "tienen", "tiene", "hay",
    "puedo", "puede", "debo", "debe", "cual", "cuales", "como", "sobre",
    "tema", "general", "generales", "pasa", "extensions", "extension",
}

_NO_SPECIFIC_PROTOCOL = (
    "No encontré un protocolo específico documentado para la especialidad o "
    "procedimiento consultado. La Clínica Benitez no cuenta con un protocolo "
    "específico para ese procedimiento en la documentación disponible. No "
    "presentes pautas generales como si fueran su protocolo. Si corresponde, "
    "podés ofrecer una derivación administrativa general."
)

_ADMIN_PROCEDURE_TERMS = {
    "derivacion",
    "derivaciones",
    "traslado",
    "traslados",
    "administrativa",
    "administrativo",
    "internacion",
    "alta",
    "obras",
    "sociales",
    "autorizacion",
    "auditoria",
    "facturacion",
    "egresos",
    "cama",
    "ambulancia",
}

_CONTACTOS: dict[str, dict[str, str]] = {
    "gestion de pacientes": {
        "area": "Gestión de Pacientes",
        "responsable": "Lic. Mariana Torres",
        "telefono": "Int. 104",
        "correo": "derivaciones@clinicabenitez.com",
    },
    "auditoria medica": {
        "area": "Auditoría Médica",
        "responsable": "Dr. Carlos Villalba",
        "telefono": "Int. 220",
        "correo": "auditoria@clinicabenitez.com",
    },
    "facturacion y egresos": {
        "area": "Facturación y Egresos",
        "responsable": "Cra. Lucía Fernandez",
        "telefono": "Int. 115",
        "correo": "facturacion@clinicabenitez.com",
    },
    "direccion medica": {
        "area": "Dirección Médica",
        "responsable": "Dra. Elena Gomez",
        "telefono": "Int. 500",
        "correo": "direccion@clinicabenitez.com",
    },
    "mantenimiento y sistemas": {
        "area": "Mantenimiento y Sistemas",
        "responsable": "Ing. Roberto Ruiz",
        "telefono": "Int. 333",
        "correo": "soporte@clinicabenitez.com",
    },
}

_ALIASES = {
    "derivaciones": "gestion de pacientes",
    "derivacion": "gestion de pacientes",
    "gestion pacientes": "gestion de pacientes",
    "auditoria": "auditoria medica",
    "facturacion": "facturacion y egresos",
    "egresos": "facturacion y egresos",
    "cobros": "facturacion y egresos",
    "direccion": "direccion medica",
    "director medico": "direccion medica",
    "mantenimiento": "mantenimiento y sistemas",
    "sistemas": "mantenimiento y sistemas",
    "soporte": "mantenimiento y sistemas",
}

_TICKETS: dict[str, dict[str, str]] = {}


def _normalize(text: str) -> str:
    """Minúsculas, sin acentos y con espacios colapsados."""
    decomposed = unicodedata.normalize("NFD", text or "")
    without_accents = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def _tokenize(query: str) -> list[str]:
    """Tokens útiles para la búsqueda léxica, sin stopwords ni duplicados."""
    tokens = re.findall(r"[a-z0-9@._-]+", _normalize(query))
    cleaned: list[str] = []
    for token in tokens:
        token = token.strip("._-")
        if len(token) < 3 or token in _STOPWORDS:
            continue
        if token not in cleaned:
            cleaned.append(token)
    return cleaned


def _token_weight(token: str) -> float:
    """Da más peso a correos, números de extensión y términos específicos."""
    if "@" in token or any(ch.isdigit() for ch in token):
        return 2.5
    if len(token) >= 9:
        return 1.5
    return 1.0


def _specific_query_terms(query: str) -> list[str]:
    """Términos que identifican una especialidad o procedimiento concreto."""
    return [
        token
        for token in _tokenize(query)
        if token not in _GENERIC_QUERY_TERMS
    ]


def _lexical_search(query: str, limit: int = _LEXICAL_LIMIT) -> list[Document]:
    """Busca coincidencias literales de términos en los fragmentos indexados.

    Es un complemento de la búsqueda vectorial para nombres, correos y
    extensiones, donde `nomic-embed-text` pierde precisión al diluir el texto.
    """
    tokens = _tokenize(query)
    if not tokens:
        return []

    data = get_vector_store().get(include=["documents", "metadatas"])
    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []

    scored: list[tuple[float, Document]] = []
    for text, metadata in zip(documents, metadatas):
        normalized = _normalize(text)
        matched = [token for token in tokens if token in normalized]
        if not matched:
            continue
        score = sum(_token_weight(token) for token in matched)
        score += len(matched) / len(tokens)
        if score < _LEXICAL_MIN_SCORE:
            continue
        doc = Document(page_content=text, metadata=dict(metadata or {}))
        doc.metadata["recuperacion"] = "lexica"
        scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:limit]]


def _deduplicate(documents: list[Document], limit: int) -> list[Document]:
    seen: set[str] = set()
    result: list[Document] = []
    for doc in documents:
        key = hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        result.append(doc)
        if len(result) >= limit:
            break
    return result


def _format_documents(documents: list[Document]) -> str:
    blocks: list[str] = []
    for index, doc in enumerate(documents, start=1):
        metadata = doc.metadata or {}
        source = metadata.get("archivo") or metadata.get("source") or "documento"
        page = metadata.get("pagina")
        origin = f"{source}, página {page}" if page else str(source)
        blocks.append(f"[Fragmento {index} | {origin}]\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(blocks)


def hybrid_search(query: str) -> list[Document]:
    """Combina búsqueda léxica (exacta) con búsqueda vectorial (semántica)."""
    lexical = _lexical_search(query)
    vector = search_protocols(query, k=_VECTOR_LIMIT)
    return _deduplicate(lexical + vector, limit=_VECTOR_LIMIT)


@tool
def buscar_protocolo(
    query: Annotated[
        str,
        "Consulta en lenguaje natural sobre protocolos, servicios, horarios, "
        "requisitos, coberturas, trámites o contactos de la clínica.",
    ],
) -> str:
    """Busca información institucional en la documentación de la Clínica Benitez.

    Devuelve los fragmentos más relevantes de los PDFs indexados, indicando
    documento y página. Úsala antes de responder consultas institucionales.
    """
    if not query or not query.strip():
        return "Error: la consulta de búsqueda no puede estar vacía."

    documents = hybrid_search(query.strip())
    specific_terms = _specific_query_terms(query)

    if specific_terms:
        scored: list[tuple[int, Document]] = []
        for document in documents:
            normalized = _normalize(document.page_content)
            matches = sum(1 for term in specific_terms if term in normalized)
            if matches:
                scored.append((matches, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        if any(term in _ADMIN_PROCEDURE_TERMS for term in specific_terms):
            documents = [document for _, document in scored][:4]
        else:
            documents = [document for _, document in scored][:1]

        if not documents:
            return _NO_SPECIFIC_PROTOCOL
    else:
        documents = documents[:4]

    if not documents:
        return (
            "No encontré información en la documentación institucional para esa "
            "consulta. No inventes una respuesta: derivá al área correspondiente."
        )
    return _format_documents(documents)


def _resolve_area(area: str) -> str | None:
    normalized = _normalize(area)
    if normalized in _CONTACTOS:
        return normalized
    if normalized in _ALIASES:
        return _ALIASES[normalized]
    for key in _CONTACTOS:
        if key in normalized or normalized in key:
            return key
    for alias, key in _ALIASES.items():
        if alias in normalized:
            return key
    return None


@tool
def consultar_contacto_area(
    area: Annotated[
        str,
        "Área o departamento de la clínica (por ejemplo: Gestión de Pacientes, "
        "Auditoría Médica, Facturación y Egresos, Dirección Médica).",
    ],
) -> str:
    """Devuelve el contacto institucional de un área hospitalaria.

    Incluye responsable, teléfono interno y correo oficial. Si el área no está
    registrada, informa las áreas disponibles.
    """
    if not area or not area.strip():
        return "Error: debés indicar el área cuya información de contacto necesitás."

    normalized = _normalize(area)
    if "guardia" in normalized or "urgencia" in normalized or "emergencia" in normalized:
        return (
            "Guardia de emergencias: funciona las 24 horas. La documentación "
            "institucional no registra un teléfono directo de guardia; el paciente "
            "debe acudir presencialmente o llamar al servicio de emergencias local."
        )

    key = _resolve_area(area)
    if key is None:
        disponibles = ", ".join(
            f"{contact['area']} ({contact['telefono']})"
            for contact in _CONTACTOS.values()
        )
        return (
            f"No encontré un contacto registrado para '{area}'. "
            f"Áreas disponibles: {disponibles}."
        )

    contact = _CONTACTOS[key]
    return (
        f"Área: {contact['area']}\n"
        f"Responsable: {contact['responsable']}\n"
        f"Teléfono interno: {contact['telefono']}\n"
        f"Correo: {contact['correo']}\n"
        "Fuente: Protocolo de Servicios y Contactos Internos (CB-SRV-002)."
    )


@tool
def derivar_solicitud(
    motivo: Annotated[
        str,
        "Motivo breve y concreto de la derivación (consulta administrativa, "
        "consulta clínica, reclamo, caso que requiere atención humana).",
    ],
    area: Annotated[
        str,
        "Área o profesional de destino de la derivación.",
    ],
) -> str:
    """Registra una derivación simulada y devuelve el número de ticket.

    Usala cuando la consulta exceda tus capacidades, sea clínica, requiera
    atención humana o no pueda resolverse con la documentación institucional.
    """
    if not motivo or not motivo.strip():
        return "Error: la derivación necesita un motivo."
    if not area or not area.strip():
        return "Error: la derivación necesita un área de destino."

    ticket = f"T-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    _TICKETS[ticket] = {
        "motivo": motivo.strip(),
        "area": area.strip(),
        "estado": "pendiente",
        "creado": datetime.now().isoformat(timespec="seconds"),
    }
    return (
        f"Derivación registrada correctamente.\n"
        f"Ticket: {ticket}\n"
        f"Área: {area.strip()}\n"
        f"Motivo: {motivo.strip()}\n"
        f"Estado: pendiente de contacto.\n"
        "Informá al usuario el número de ticket y, si corresponde, el contacto "
        "del área usando consultar_contacto_area."
    )


TOOLS = [buscar_protocolo, consultar_contacto_area, derivar_solicitud]
TOOL_MAP = {tool.name: tool for tool in TOOLS}
