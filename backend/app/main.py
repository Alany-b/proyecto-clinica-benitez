from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router

app = FastAPI(
    title="Clínica Benitez API",
    description="API de asistencia hospitalaria con agente de IA local y RAG.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    """Chequeo de salud usado por Docker y por el orquestador."""
    return {"status": "ok", "service": "clinica-benitez-api"}
