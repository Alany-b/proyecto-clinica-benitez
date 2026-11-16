# Clínica Benitez — Monorepo
##  Integrantes : Recalde  Alejandro , Ybars Alan , Ruiz Diaz Ruben


Sistema de asistencia administrativa para la Clínica Benitez:

- **Backend:** API REST + agente de IA local con RAG, function calling y ChromaDB.
- **Frontend:** interfaz web React + Vite + TypeScript + Tailwind CSS, servida por Nginx.
- **Infraestructura:** Docker Compose con los servicios `api` y `frontend`.

Todo corre de forma local: Ollama en el host y los servicios en contenedores.

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
│   ├── Dockerfile        # node:20-alpine -> nginx:alpine
│   ├── nginx.conf
│   └── README.md
├── docker-compose.yml    # Servicios api + frontend
├── .gitignore
└── README.md
```

## Requisitos

- Docker Desktop con el motor iniciado.
- Ollama ejecutándose en el host (`http://localhost:11434`).
- Modelos: `llama3.1:8b` y `nomic-embed-text`.
- PDFs institucionales en `backend/data/`.

## Despliegue completo

```powershell
# 1. Modelos locales
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 2. Modelo del agente
ollama create agente-clinica -f backend/Modelfile

# 3. Construir y levantar API + frontend
docker compose up -d --build

# 4. Indexar los PDFs (primera vez o cuando cambien)
docker compose run --rm api python -m app.rag.indexer
```

Verificar:

```powershell
docker compose ps
curl.exe -s http://localhost:8000/health
```

Ambos servicios deben quedar `Up (healthy)`.

> La indexación solo es necesaria la primera vez o cuando cambien los PDFs de
> `backend/data/`. El índice se guarda en `backend/vector_store/`.

## Servicios

| Servicio | URL |
|----------|-----|
| Frontend (Nginx) | <http://localhost:5173> |
| API | <http://localhost:8000> |
| Documentación API | <http://localhost:8000/docs> |
| Healthcheck | <http://localhost:8000/health> |

El frontend se compila con Vite y se sirve como estáticos desde Nginx. El valor
`VITE_API_URL` se embebe en **build-time** (por defecto `http://localhost:8000`). Si lo
cambiás, reconstruí:

```powershell
docker compose up -d --build frontend
```

## Desarrollo local del frontend

Con el backend levantado:

```powershell
cd frontend
npm install
npm run dev
```

Abrir <http://localhost:5173>. El detalle está en [frontend/README.md](frontend/README.md).

## Comandos útiles

```powershell
docker compose logs -f              # logs de ambos servicios
docker compose logs -f frontend
docker compose logs -f api
docker compose up -d --build api   # solo backend
docker compose up -d --build frontend
docker compose down                 # detener el stack
```

## Documentación

- [Informe completo del proyecto (PDF)](Documentacion_Clinica_Benitez.pdf)
- [Informe editable (DOCX)](Documentacion_Clinica_Benitez.docx)
- [Backend](backend/README.md)
- [Frontend](frontend/README.md)
- [Bitácora backend](backend/desarollo.md)
- [Cambios backend](backend/cambios.md)
- [Bitácora frontend](frontend/desarollo.md)
- [Cambios frontend](frontend/cambios.md)
