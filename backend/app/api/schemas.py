"""Esquemas de entrada y salida para la API de chat."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """Mensaje previo de la conversación."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"] = Field(
        description="Rol del mensaje: 'user' o 'assistant'."
    )
    content: str = Field(
        min_length=1,
        max_length=4000,
        description="Contenido textual del mensaje.",
    )


class ChatRequest(BaseModel):
    """Solicitud de chat: mensaje actual + historial previo."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=4000,
        description="Consulta actual del usuario.",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=50,
        description="Mensajes previos, en orden cronológico.",
    )


class ChatResponse(BaseModel):
    """Respuesta final del agente (sin razonamiento interno)."""

    respuesta: str = Field(description="Respuesta final en español.")
    herramientas_usadas: list[str] = Field(
        description="Herramientas ejecutadas durante la consulta."
    )
    pasos: int = Field(ge=0, description="Cantidad de rondas del agente.")
