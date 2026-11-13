# Clínica Benitez — Monorepo
##  Integrantes : Recalde  Alejandro , Ybars Alan , Ruiz Diaz Ruben


Sistema de asistencia administrativa para la Clínica Benitez:

- **Backend:** API REST + agente de IA local con RAG y function calling.
- **Frontend:** interfaz web React + Vite + TypeScript + Tailwind CSS.

Todo corre de forma local con Docker y Ollama. El frontend puede ejecutarse con Vite en
desarrollo o con Nginx una vez completada la Fase 3.

## Estructura

```
proyecto-clinica-benitez/
├── backend/              # FastAPI, agente LangChain, RAG, Chroma
│   ├── app/
│   ├── data/             # PDFs institucionales
│   ├── vector_store/     # Persistencia de Chroma
│   ├── Dockerfile
│   ├── Modelfile
│   ├── requirements.txt
│   └── README.md
├── frontend/             # React + Vite + TypeScript + Tailwind
│   ├── src/
│   ├── README.md
│   └── (Dockerfile en Fase 3)
├── docker-compose.yml    # Servicio api (frontend en Fase 3)
└── README.md
```

## Requisitos

- Docker Desktop con el motor iniciado.
- Ollama ejecutándose en el host (`http://localhost:11434`).
- Modelos: `llama3.1:8b` y `nomic-embed-text`.

## Puesta en marcha rápida

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
ollama create agente-clinica -f backend/Modelfile

docker compose up -d --build
docker compose run --rm api python -m app.rag.indexer
```

> La indexación solo es necesaria la primera vez o cuando cambien los PDFs de `backend/data/`.

## Servicios

| Servicio | URL |
|----------|-----|
| Frontend (desarrollo) | <http://localhost:5173> |
| Frontend (Docker, Fase 3) | <http://localhost:5173> |
| API | <http://localhost:8000> |
| Documentación API | <http://localhost:8000/docs> |
| Healthcheck | <http://localhost:8000/health> |

## Desarrollo local del frontend

Con el backend levantado:

```powershell
cd frontend
npm install
npm run dev
```

Abrir <http://localhost:5173>. El detalle está en [frontend/README.md](frontend/README.md).

## Documentación

- [Backend](backend/README.md)
- [Frontend](frontend/README.md)
- [Bitácora backend](backend/desarollo.md)
- [Cambios backend](backend/cambios.md)
- [Bitácora frontend](frontend/desarollo.md)
- [Cambios frontend](frontend/cambios.md)

## Detener el stack

```powershell
docker compose down
```
