# Clínica Benitez — API REST + Agente de IA local

Asistente virtual para consultas administrativas de la Clínica Benitez. Combina un agente
local con **function calling**, un motor **RAG** sobre PDFs institucionales y una **API REST**
dockerizada. Todo corre en tu equipo: no se envían datos a servicios en la nube.

---

## ¿En qué consta el proyecto?

El proyecto es un **monolito modular** con tres dominios:

| Dominio | Responsabilidad |
|---------|-----------------|
| `app/api` | Capa HTTP: esquemas y endpoint `POST /api/chat`. |
| `app/agent` | Core del agente, tools y reglas de operación. |
| `app/rag` | Indexación de PDFs, embeddings y búsqueda en ChromaDB. |

Tecnologías principales:

- **FastAPI + Uvicorn** para la API.
- **LangChain 1.x** para mensajes, tools y el bucle de tool-calling.
- **Ollama** como runtime local de modelos.
- **llama3.1:8b** para generación y tool calling nativo.
- **nomic-embed-text** para embeddings (768 dimensiones).
- **ChromaDB** como base vectorial persistente.
- **Docker / Docker Compose** para empaquetar y ejecutar el servicio.

Flujo de una consulta:

```
Cliente → POST /api/chat → Agente (llama3.1:8b)
                              ├─ buscar_protocolo → Chroma (RAG)
                              ├─ consultar_contacto_area → directorio
                              └─ derivar_solicitud → ticket
                         → respuesta final en español
```

---

## Requisitos

- **Docker Desktop** instalado y con el motor Linux iniciado.
- **Ollama** instalado y ejecutándose en el host (`http://localhost:11434`).
- Espacio en disco: ~10 GB para los modelos.
- Opcional: `curl` o PowerShell para probar la API.

> La API corre dentro de Docker y se comunica con Ollama en el host mediante
> `host.docker.internal:11434`.

---

## Puesta en marcha

### 1. Ubicarse en el proyecto

```powershell
cd C:\dev\proyecto-clinica-benitez
```

### 2. Descargar los modelos en Ollama

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Verificar:

```powershell
ollama list
```

### 3. Compilar el modelo del agente

El archivo `backend/Modelfile` parte de `llama3.1:8b`, fija `temperature 0.2` y contiene el
SYSTEM prompt con las reglas de la clínica:

```powershell
ollama create agente-clinica -f backend/Modelfile
```

Debe finalizar con `success`. Verificar:

```powershell
ollama list
```

Debe aparecer `agente-clinica:latest`.

### 4. Agregar los PDFs institucionales

Copiar los documentos a:

```
backend/data/
```

Actualmente el proyecto incluye:

- `Manual de Procedimientos Administrativos.pdf`
- `Protocolo de Servicios y Contactos Internos.pdf`

Sin PDFs no se puede construir el índice RAG.

### 5. Construir y levantar la API

```powershell
docker compose up -d --build
```

Verificar que el contenedor esté saludable:

```powershell
docker compose ps
curl.exe -s http://localhost:8000/health
```

Respuesta esperada:

```json
{"status":"ok","service":"clinica-benitez-api"}
```

Documentación interactiva: <http://localhost:8000/docs>

### 6. Indexar los PDFs en Chroma

La primera vez, o cada vez que agregues/cambies PDFs:

```powershell
docker compose run --rm api python -m app.rag.indexer
```

Salida esperada (con los 2 PDFs actuales):

```
archivos: 2
paginas: 4
fragmentos: 7
coleccion: protocolos_clinica
persistencia: /code/vector_store
```

El índice se guarda en `backend/vector_store` y sobrevive a los reinicios del contenedor.

---

## Probar la API

### Consulta básica

```powershell
$body = @{
  message = "¿Cuál es el horario de Diagnóstico por Imágenes?"
  history = @()
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/chat `
  -Body $body `
  -ContentType "application/json; charset=utf-8"
```

Respuesta esperada:

```json
{
  "respuesta": "El horario de Diagnóstico por Imágenes es: Lunes a Viernes 07:00 a 20:00 hs, Sábados 08:00 a 13:00 hs. Ubicación: Subsuelo - Ala Sur.",
  "herramientas_usadas": ["buscar_protocolo"],
  "pasos": 2
}
```

### Con historial de conversación

```powershell
$body = @{
  message = "¿Y los sábados?"
  history = @(
    @{ role = "user"; content = "¿Cuál es el horario de Diagnóstico por Imágenes?" }
    @{ role = "assistant"; content = "Lunes a viernes de 07:00 a 20:00 hs." }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/chat `
  -Body $body `
  -ContentType "application/json; charset=utf-8"
```

### Consulta de contacto

```powershell
$body = @{
  message = "¿A qué extensión debo llamar para una derivación administrativa?"
  history = @()
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/chat `
  -Body $body `
  -ContentType "application/json"
```

Debe usar `consultar_contacto_area` y devolver el **Int. 104**.

### Consulta clínica / emergencia

```powershell
$body = @{
  message = "Me duele el pecho, ¿qué medicamento tomo?"
  history = @()
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/chat `
  -Body $body `
  -ContentType "application/json"
```

Debe:

- No diagnosticar ni recomendar medicamentos.
- Indicar guardia/servicio de emergencias.
- Usar `derivar_solicitud` y devolver un ticket.

### Errores esperados

| Caso | HTTP |
|------|------|
| `message` vacío | `422` |
| `role` distinto de `user`/`assistant` | `422` |
| Ollama o Chroma no disponibles | `503` |

---

## Probar el agente directamente

### Desde el contenedor (con tools reales)

```powershell
docker compose run --rm -T api python -c "from app.agent.core import run_agent; r = run_agent('¿Cuál es el horario de Diagnóstico por Imágenes?'); print(r.respuesta); print('TOOLS:', r.herramientas_usadas)"
```

Salida esperada:

```
El horario de Diagnóstico por Imágenes es: ...
TOOLS: ['buscar_protocolo']
```

### Desde la consola de Ollama (sin tools)

```powershell
ollama run agente-clinica
```

> Importante: `ollama run` **no inyecta las tools**. El modelo solo aplica el rol y las
> políticas del SYSTEM prompt. Para function calling real usá la API o `run_agent`.

---

## Estructura del proyecto

```
proyecto-clinica-benitez/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py        # POST /api/chat
│   │   │   └── schemas.py       # Request/response Pydantic
│   │   ├── agent/
│   │   │   ├── core.py          # ChatOllama + bind_tools + bucle de tools
│   │   │   └── tools.py         # buscar_protocolo, contactos, derivación
│   │   ├── rag/
│   │   │   └── indexer.py       # PDFs → chunks → embeddings → Chroma
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI + /health
│   ├── data/                    # PDFs institucionales
│   ├── vector_store/            # Persistencia de Chroma
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .env.example
│   ├── Modelfile                # agente-clinica (FROM llama3.1:8b)
│   ├── desarollo.md             # Bitácora técnica por fases
│   ├── cambios.md               # Cambios e incidencias relevantes
│   └── README.md
├── frontend/                    # React + Vite (Fase 2)
├── docker-compose.yml           # Servicios api + frontend
├── .gitignore
└── README.md
```

---

## Configuración

Variables disponibles (ver `backend/.env.example`):

| Variable | Valor por defecto | Uso |
|----------|-------------------|-----|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | URL de Ollama desde el contenedor. |
| `OLLAMA_CHAT_MODEL` | `agente-clinica` | Modelo de generación/tools. |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Modelo de embeddings. |
| `CHROMA_COLLECTION` | `protocolos_clinica` | Colección vectorial. |
| `DATA_DIR` | `/code/data` | PDFs dentro del contenedor. |
| `CHROMA_PERSIST_DIR` | `/code/vector_store` | Persistencia de Chroma. |

Si cambiás valores, editá `backend/.env` o `docker-compose.yml` y reiniciá:

```powershell
docker compose up -d
```

---

## RAG y herramientas

- **Carga:** `PyPDFLoader` sobre todos los `*.pdf` de `backend/data/`.
- **Fragmentación:** `RecursiveCharacterTextSplitter` con `chunk_size=1000`,
  `chunk_overlap=200`.
- **Embeddings:** `nomic-embed-text` (768 dims).
- **Persistencia:** Chroma en `backend/vector_store/`, colección `protocolos_clinica`.
- **Recuperación híbrida:** similitud vectorial + coincidencia léxica para nombres, correos y
  extensiones (mejora los contactos exactos).
- **Tools:**
  - `buscar_protocolo(query)`: documentación institucional.
  - `consultar_contacto_area(area)`: directorio interno.
  - `derivar_solicitud(motivo, area)`: ticket de derivación simulado.
- **Guardrails:** emergencia primero, sin diagnósticos/medicamentos, ticket visible y
  prohibición de inventar datos.
- **Contactos:** teléfonos, internos y correos solo se informan si provienen de
  `consultar_contacto_area` o `buscar_protocolo`; el prompt prohíbe inventarlos.
- **Fallback de tool calls:** si el modelo emite un JSON con `name` + `parameters`/`arguments`
  en texto plano, se ejecuta la tool programáticamente. Si el JSON es inválido o la tool no
  existe, se devuelve un mensaje seguro sin exponer el JSON.
- **Saludos y ambigüedad:** los saludos simples no consultan Chroma; las consultas de
  disponibilidad sin área específica piden aclaración.
- **No extrapolación:** si ningún fragmento menciona la especialidad/procedimiento, el agente
  aclara que no hay protocolo específico documentado y no aplica pasos generales como si
  fueran el protocolo consultado.

---

## Solución de problemas

### “failed to connect to the docker API”

Docker Desktop está cerrado. Abrilo y esperá a que el motor inicie:

```powershell
docker info
```

### Ollama no responde

```powershell
curl.exe -s http://localhost:11434/api/tags
```

Si falla, abrí Ollama y verificá que esté escuchando en `11434`.

### “model not found: agente-clinica”

```powershell
ollama create agente-clinica -f backend/Modelfile
```

### No encuentra información / respuestas vacías

- Verificá que haya PDFs en `backend/data/`.
- Reindexá:

```powershell
docker compose run --rm api python -m app.rag.indexer
```

- Revisá los logs:

```powershell
docker compose logs -f api
```

### La API devuelve 503

Suele significar que Ollama no está disponible o que Chroma no está indexado. Verificá
`/health`, `ollama list` y el índice.

### Caracteres raros en PowerShell (`DiagnA3stico`)

La API devuelve UTF-8 correcto. El problema es la visualización del terminal. Probá con
Windows Terminal o revisá la respuesta en `/docs`.

### Puerto 8000 ocupado

Cambiá el mapeo en `docker-compose.yml`:

```yaml
ports:
  - "8080:8000"
```

---

## Alcance y límites

- El agente **no diagnostica, no receta y no interpreta estudios**.
- Las derivaciones y tickets son **simulados** (no hay integración con un sistema real).
- Los contactos provienen de la documentación institucional cargada.
- No incluye autenticación, CORS ni TLS; no está listo para producción sin esos controles.
- La calidad del RAG depende de los PDFs y del modelo de embeddings.

Para detalles técnicos por fase, ver [`desarollo.md`](desarollo.md).
Para cambios e incidencias, ver [`cambios.md`](cambios.md).
