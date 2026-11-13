"""Rutas HTTP del dominio de chat."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.agent.core import run_agent
from app.api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Consulta al agente de Clínica Benitez",
    description=(
        "Procesa la consulta actual junto con el historial, ejecuta las herramientas "
        "necesarias (RAG, contactos o derivación) y devuelve la respuesta final."
    ),
)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        result = run_agent(
            message=payload.message,
            history=[message.model_dump() for message in payload.history],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - depende de Ollama/Chroma
        logger.exception("Error procesando la consulta de chat")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No se pudo procesar la consulta porque el agente o la base "
                "documental no están disponibles. Intentá nuevamente en unos segundos."
            ),
        ) from exc

    return ChatResponse(
        respuesta=result.respuesta,
        herramientas_usadas=result.herramientas_usadas,
        pasos=result.pasos,
    )
