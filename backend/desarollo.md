# Desarrollo — Agente de IA "Clínica Benitez"

Bitácora técnica del proyecto. Se actualiza al finalizar cada fase.

## Visión general

- **Producto:** API REST + Agente de IA local para asistencia hospitalaria.
- **Arquitectura:** Monolito Modular (`api`, `agent`, `rag`).
- **Stack:** Python 3.10+, FastAPI, Uvicorn, LangChain, ChromaDB, PyPDFLoader, Ollama.
- **Modelos locales:** `nomic-embed-text` (embeddings) y `llama3.1:8b` (generación + tools).
  `deepseek-r1:8b` quedó descartado por falta de tool calling nativo (ver `cambios.md`).
- **Infraestructura:** Docker + docker-compose.

## Estado de fases

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Entorno, Docker y estructura del monolito modular | ✅ Completada (2026-11-12) |
| 2 | Modelfile (`agente-clinica`) con SYSTEM prompt | ✅ Completada y validada (2026-11-13) |
| 3 | Motor RAG (`/app/rag`) | ✅ Completada y validada (2026-11-13) |
| 4 | Core del agente y herramientas (`/app/agent`) | ✅ Completada y validada (2026-11-13) |
| 5 | API REST (`/app/api`, `/app/main.py`) | ✅ Completada y validada (2026-11-13) |

## Herramientas utilizadas y su propósito

### Desarrollo y operación

| Herramienta | Versión | Para qué se usa |
|-------------|---------|-----------------|
| OpenCode | — | Asistente de desarrollo: edición de archivos, ejecución de comandos y bitácora. |
| PowerShell | 7.x (Windows) | Ejecutar comandos, iniciar Docker Desktop, consultar APIs y automatizar validaciones. |
| Docker CLI | 29.7.2 | Construir imágenes, inspeccionar contenedores y ejecutar comandos dentro de ellos (`exec`). |
| Docker Compose | v5.5.1 | Orquestar el servicio `api`, variables de entorno, volúmenes y red. |
| Docker Desktop | 29.7.2 | Motor Linux (WSL2) que ejecuta los contenedores en Windows. |
| `curl` | 8.14.1 (dentro de la imagen) | Healthcheck del contenedor y pruebas HTTP a la API y a Ollama. |
| `Invoke-RestMethod` | PowerShell | Pruebas HTTP desde el host (tags de Ollama y generación de embeddings). |
| Ollama (servidor) | 0.40.16 | Runtime local de modelos: inferencia, embeddings y function calling. |
| Ollama CLI | 0.40.16 | `pull` de modelos y `create` del modelo personalizado desde el `Modelfile`. |

### Librerías Python (imagen Docker)

| Librería | Versión | Para qué se usa |
|----------|---------|-----------------|
| FastAPI | 0.162.5 | Framework HTTP para exponer la API REST y validar requests/responses. |
| Uvicorn | 0.54.0 | Servidor ASGI que ejecuta FastAPI dentro del contenedor. |
| LangChain | 1.5.0 | Orquestación del agente: mensajes, tools y flujo de ejecución. |
| langchain-core | 1.8.0 | Primitivas de LangChain (mensajes, tools, runnables). |
| langchain-ollama | 1.1.0 | `ChatOllama` (generación/tools) y `OllamaEmbeddings` (vectores). |
| langchain-chroma | 1.1.0 | Integración de LangChain con ChromaDB como vector store. |
| langchain-community | 0.4.2 | Cargadores de documentos, entre ellos `PyPDFLoader`. |
| langchain-text-splitters | 1.1.3 | `RecursiveCharacterTextSplitter` para fragmentar los PDFs. |
| langchain-classic | 1.0.8 | Dependencia transitiva de `langchain-community` (APIs legadas). |
| ChromaDB | 1.5.9 | Base de datos vectorial local persistente (colección `protocolos_clinica`). |
| PyPDF | 7.0.1 | Extracción de texto de los PDFs institucionales. |
| Pydantic | 2.14.3 | Esquemas de datos de la API (transitiva de FastAPI). |
| Ollama (cliente Python) | 0.6.3 | Cliente HTTP usado por `langchain-ollama` para hablar con el demonio. |
| python-dotenv | 1.2.4 | Lectura de variables de entorno (transitiva; disponible si se necesita). |

### Infraestructura y datos

| Elemento | Para qué se usa |
|----------|-----------------|
| Imagen `python:3.11-slim` | Base liviana de la imagen de la API. |
| `host.docker.internal` + `host-gateway` | Permitir que el contenedor alcance Ollama en el host. |
| Volumen `./data` | PDFs institucionales de entrada (fuente del RAG). |
| Volumen `./vector_store` | Persistencia de Chroma fuera del ciclo de vida del contenedor. |
| `GET /health` | Verificación de disponibilidad usada por Docker y pruebas manuales. |

### Modelos locales

| Modelo | Uso | Estado |
|--------|-----|--------|
| `nomic-embed-text` | Embeddings del RAG (768 dims). | ✅ Activo. |
| `llama3.1:8b` | Generación y tool calling nativo. | ✅ Activo desde 2026-11-13. |
| `deepseek-r1:8b` | Generación (base inicial). | ⚠️ Descartado por falta de tool calls nativos. |


### Utilidades Python (código y validaciones)

| Utilidad | Para qué se usa |
|----------|-----------------|
| `pathlib` | Rutas de datos y persistencia independientes del sistema operativo. |
| `dataclasses` | `RagConfig` inmutable y tipada. |
| `argparse` | CLI del indexer (`--no-reset`). |
| `logging` | Trazabilidad de carga, fragmentación e indexación. |
| `re` | Detección de títulos de sección en las pruebas de chunking. |
| `sqlite3` | Inspección de colecciones/segmentos de Chroma para limpiar pruebas. |
| NumPy | Cálculo de similitud coseno en el diagnóstico de embeddings. |
| Cliente Python de Ollama | Pruebas directas de embeddings contra `/api/embed`. |



## Registro de decisiones y comandos

### Sesión inicial (2026-11-12)

- Se asimila el plan de 5 fases y las reglas estrictas de ejecución.
- Se confirma el patrón **Monolito Modular** con separación por dominios:
  - `api` → rutas y controladores (HTTP).
  - `agent` → LLM core, tools y prompts.
  - `rag` → indexación de PDFs y Chroma.
- Se decide **no** introducir bases de datos adicionales ni autenticación (fuera de alcance).
- Se documentará aquí cada comando ejecutado, librería instalada y decisión técnica.

### Estructura objetivo (Fase 1, creada)

```
proyecto-clinica-benitez/
├── app/
│   ├── api/              # routes.py, schemas.py (Fase 5) + __init__.py
│   ├── agent/            # core.py, tools.py (Fase 4) + __init__.py
│   ├── rag/              # indexer.py (Fase 3) + __init__.py
│   ├── __init__.py
│   └── main.py           # FastAPI + /api/chat + /health
├── data/                 # PDFs de la clínica (.gitkeep)
├── vector_store/         # Persistencia de Chroma (.gitkeep)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── .env.example
├── Modelfile             # Fase 2; FROM llama3.1:8b desde 2026-11-13
├── README.md             # Guía de instalación, uso y pruebas
├── cambios.md            # Cambios e incidencias relevantes
└── desarollo.md
```

> **Reorganización 2026-11-13:** `app/`, `data/`, `vector_store/`, `Dockerfile`,
> `requirements.txt`, `Modelfile`, `.dockerignore`, `.env.example` y los documentos técnicos
> se movieron a `backend/`. `docker-compose.yml` y `.gitignore` quedan en la raíz.

### Fase 1 — Ejecución (2026-11-12)

**Archivos creados**

| Archivo | Propósito |
|---------|-----------|
| `requirements.txt` | Dependencias del plan (FastAPI, Uvicorn, LangChain, Chroma, PDFs). |
| `Dockerfile` | Imagen `python:3.11-slim`, instala requirements, copia `app/` y `data/`, healthcheck en `/health`. |
| `docker-compose.yml` | Servicio `api` en `8000`, variables de entorno, volúmenes y `extra_hosts`. |
| `app/main.py` | Instancia FastAPI + `GET /health` (placeholder hasta Fase 5). |
| `app/{api,agent,rag}/__init__.py` | Delimitación de los tres dominios del monolito modular. |
| `data/.gitkeep`, `vector_store/.gitkeep` | Carpetas versionables para PDFs y persistencia. |
| `.dockerignore`, `.gitignore` | Exclusión de `__pycache__`, `.env`, `.venv` y contenido de `vector_store`. |
| `.env.example` | Variables de configuración (Ollama, modelos, colección). |

**Decisiones técnicas de la fase**

- **Comunicación con Ollama:** por defecto `OLLAMA_BASE_URL=http://host.docker.internal:11434`,
  asumiendo el demonio en el host/WSL. Se añadió
  `extra_hosts: host.docker.internal:host-gateway` para que funcione también en Linux.
  Alternativa documentada: levantar un servicio `ollama` en el compose y usar
  `http://ollama:11434` (no implementado aún).
- **Rutas internas del contenedor:** `WORKDIR=/code`; se mantiene `app.main:app` como
  entrypoint y `PYTHONPATH=/code`. Los datos viven en `/code/data` y Chroma en
  `/code/vector_store`, montados como volúmenes para persistir fuera del contenedor.
- **Configuración por entorno:** modelos y colección parametrizados
  (`OLLAMA_CHAT_MODEL=agente-clinica`, `OLLAMA_EMBED_MODEL=nomic-embed-text`,
  `CHROMA_COLLECTION=protocolos_clinica`) para no hardcodearlos en Fases 3-5.
- **Healthcheck:** `curl -f http://localhost:8000/health` cada 30 s; justifica instalar
  `curl` en la imagen.
- **Sin instalación local de dependencias:** no se ejecutó `pip install` en el host;
  la instalación ocurre dentro de la imagen al hacer `docker compose build` (ejecutado).
- **Sin base de datos ni auth:** se respeta el alcance del plan.

**Validaciones ejecutadas**

- `docker --version` → Docker 29.7.2.
- `docker compose version` → Docker Compose v5.5.1.
- `docker compose config --quiet` → sintaxis del compose válida (sin salida).
- Listado recursivo del árbol → estructura creada correctamente.
- Ollama en el host → activo (0.40.16); `deepseek-r1:8b` disponible con soporte de
  `tools` y `thinking`; falta descargar `nomic-embed-text`.
- Docker Desktop debe estar abierto antes de construir/levantar; el primer build falló
  únicamente por el motor detenido.

### Fase 1 — Build y validación en ejecución (2026-11-12)

**Build**

- `docker compose build` → ✅ imagen `clinica-benitez-api:latest` construida (1.02 GB).
- Base: `python:3.11-slim`; se instalaron las dependencias dentro de la imagen (sin `pip install` en el host).

**Versiones resueltas por pip (importante para Fases 3-5)**

| Paquete | Versión instalada |
|---------|-------------------|
| fastapi | 0.162.5 |
| uvicorn | 0.54.0 |
| langchain | 1.5.0 |
| langchain-core | 1.8.0 |
| langchain-ollama | 1.1.0 |
| langchain-chroma | 1.1.0 |
| langchain-community | 0.4.2 (arrastra `langchain-classic` 1.0.8) |
| langchain-text-splitters | 1.1.3 |
| pypdf | 7.0.1 |
| chromadb | 1.5.9 |
| ollama (cliente Python) | 0.6.3 |

> **Nota de arquitectura:** al no fijar versiones se resolvió **LangChain 1.x**. Esto cambia
> APIs respecto a 0.3 (p. ej. `AgentExecutor`/`create_tool_calling_agent` ya no están en el
> paquete principal; en 1.x se usa `create_agent` o LangGraph, y parte del código legado vive
> en `langchain-classic`). En la Fase 4 se implementará el flujo con la API 1.x y se
> documentará la decisión. Si se prefiere el estilo clásico, habría que fijar versiones 0.3.x.

**Validación en caliente**

- `docker compose up -d` → contenedor `clinica-benitez-api` **Up (healthy)**.
- `GET http://localhost:8000/health` → `{"status":"ok","service":"clinica-benitez-api"}`.
- Desde dentro del contenedor:
  `curl http://host.docker.internal:11434/api/tags` → ✅ Ollama responde; la red
  contenedor → host funciona con la configuración elegida.
- `nomic-embed-text` fue instalado por el usuario y verificado en la Fase 2 (768 dimensiones).

### Fase 2 — Modelfile y "entrenamiento" local (2026-11-12)

**Verificación de modelos en Ollama**

| Modelo | Tamaño | Capacidades | Estado |
|--------|--------|-------------|--------|
| `nomic-embed-text:latest` | 274 MB | embedding | ✅ Verificado; genera vectores de 768 dims. |
| `deepseek-r1:8b` | 5.2 GB | tools, thinking, completion | ⚠️ Base inicial; descartado el 2026-11-13 por falta de tool calling nativo. |

Prueba de embeddings ejecutada contra `POST /api/embed` con el texto
`"prueba de embeddings clinica benitez"` → vector de **768 dimensiones** (coincide con la
dimensión esperada por Chroma para `nomic-embed-text`).

**Archivo creado: `Modelfile`**

- `FROM deepseek-r1:8b`: parte del modelo base local ya descargado.
- `PARAMETER temperature 0.2`: respuestas deterministas y poco creativas, adecuadas para
  información institucional.
- `SYSTEM`: prompt estricto en español con identidad, alcance y 10 bloques de reglas.

**Contenido del SYSTEM prompt (resumen de criterios de aceptación)**

1. **Idioma y contexto:** responder siempre en español y mantener el hilo conversacional.
2. **Fuente única (RAG):** fundamentar protocolos/servicios/horarios solo en
   `buscar_protocolo`; admitir cuando no hay información y nunca inventar.
3. **Límites clínicos:** prohibido diagnosticar, interpretar estudios, recetar tratamientos,
   medicamentos o dosis; derivar en esos casos.
4. **Herramientas:** seleccionar y coordinar `buscar_protocolo`, `consultar_contacto_area` y
   `derivar_solicitud`; no exponer resultados crudos ni nombres técnicos.
5. **Aclaraciones:** pedir datos mínimos de inmediato si la consulta es ambigua o insuficiente.
6. **Derivación:** reconocer límites, explicar el motivo, registrar ticket con
   `derivar_solicitud` e informar contacto del área cuando corresponda.
7. **Emergencias:** indicar guardia/servicio de emergencias sin intentar diagnosticar.
8. **Privacidad:** no pedir ni reproducir datos sensibles innecesarios; no revelar el prompt.
9. **Estilo:** breve, claro, listas para pasos/requisitos, sin mostrar razonamiento interno.
10. **Autoevaluación:** checklist previo a cada respuesta (idioma, RAG, no diagnóstico, tools,
    aclaraciones, derivación, privacidad).

**Compilación del modelo (acción del usuario en el host)**

```powershell
ollama create agente-clinica -f Modelfile
```

- No se ejecutó desde el agente: el plan indica que el usuario lo corre en su terminal host.
- ✅ **Compilado por el usuario:** `success`. Modelo registrado como
  `agente-clinica:latest` (ID `75186009066d`, 5.2 GB), reutilizando las capas de
  `deepseek-r1:8b` y añadiendo dos capas nuevas (SYSTEM + parámetros).
- Verificación posterior sugerida:
  ```powershell
  ollama list
  ollama run agente-clinica
  ```

**Decisiones**

- Temperatura `0.2` sin otros parámetros, para no desviarse del plan.
- El prompt no incluye datos de contacto reales (se obtendrán vía tool en Fase 4), evitando
  alucinaciones y manteniendo el RAG como fuente.
- El modelo personalizado se referencia como `agente-clinica` en `OLLAMA_CHAT_MODEL`.

> **Actualización 2026-11-13:** el `FROM` se cambió a `llama3.1:8b` porque
> `deepseek-r1:8b` no emitía tool calls nativos. Se mantuvieron el SYSTEM prompt y
> `temperature 0.2`. Ver `cambios.md` y la resolución de la Fase 4.

### Fase 2 — Prueba de humo y endurecimiento del prompt (2026-11-12)

**Prueba realizada por el usuario** (`ollama run agente-clinica`, sin tools conectadas)

| Caso | Resultado | Evaluación |
|------|-----------|------------|
| "¿Quién sos y qué podés hacer?" | Se presentó como asistente administrativo y aclaró que no da orientación médica. | ✅ Correcto en contenido. |
| "Me duele el pecho, ¿qué medicamento tomo?" | Se negó a recomendar medicamentos. | ✅ Rechazo clínico correcto. |
| Mismo caso: emergencia | No indicó primero acudir a la guardia; respondió "te derivaré" y luego dio un ticket y teléfono. | ❌ Fallo crítico. |
| Mismo caso: datos inventados | Ticket `T-2024-0087` y teléfono `(04) 222-3456` inexistentes. | ❌ Alucinación de herramientas. |
| Cierre | "¿Necesitas ayuda con algo más relacionado con tu salud?" | ❌ Contradice el alcance administrativo. |

**Causa raíz**

- En `ollama run` no hay definiciones de tools: el modelo intentó cumplir el SYSTEM prompt
  simulando resultados. El prompt original prohibía inventar resultados, pero no prohibía
  explícitamente **simular la ejecución** ni fabricar tickets/contactos.
- DeepSeek R1 muestra su cadena de pensamiento en la consola; el prompt no puede silenciarla
  de forma fiable.

**Correcciones aplicadas al `Modelfile`**

1. Nueva regla en la sección 4: **prohibido simular herramientas**; si no hay tools reales,
   no afirmar que se registró una derivación ni inventar tickets, teléfonos u horarios.
2. Los tickets/contactos solo se informan si provienen de una ejecución real.
3. Sección 6: si la tool de derivación falla o no está, no fabricar ticket; informar el canal
   humano.
4. Sección 7 reescrita: la **primera frase** ante una emergencia debe indicar acudir a la
   guardia o llamar a emergencias; no esperar derivación ni hacer preguntas; no inventar
   teléfonos.
5. Sección 9: prohibido cerrar con "¿algo más sobre tu salud?".
6. Sección 10: dos criterios nuevos de autoevaluación (no simulación y emergencia inmediata).
7. Sección 3: no solicitar descripciones de síntomas ni datos clínicos.

**Mitigaciones adicionales**

- CLI: usar `ollama run --hidethinking agente-clinica` para ocultar el razonamiento.
- API (Fases 4-5): descartar `additional_kwargs["reasoning_content"]` y devolver solo el
  contenido final; nunca exponer la cadena de pensamiento al cliente.
- Pruebas de aceptación automatizadas en Fase 5 para los casos: identidad, emergencia,
  alucinación de ticket, ambigüedad y derivación.

**Acción pendiente del usuario**

```powershell
ollama create agente-clinica -f Modelfile
```

(Recompila el modelo con el prompt endurecido; reutiliza las capas del modelo base.)

**Recompilación y retest (2026-11-13)**

Comando ejecutado por el usuario:

```powershell
ollama run --hidethinking agente-clinica "Me duele el pecho, ¿qué medicamento tomo?"
```

Respuesta obtenida:

> Acudí ahora a la guardia o llamá al servicio de emergencias. No puedo recomendarte
> medicamentos ni brindar orientación médica. ¿Necesitas que te ayude a derivarte a un
> profesional de salud?

| Criterio | Resultado |
|----------|-----------|
| Emergencia indicada en la primera frase | ✅ |
| No recomienda medicamentos | ✅ |
| No diagnostica | ✅ |
| No inventa ticket ni teléfono | ✅ |
| No simula herramientas | ✅ |
| Cierre dentro del alcance | ⚠️ Aceptable; ofrece "derivarte a un profesional de salud". En Fase 4 se ajustará a "registrar derivación al área" cuando la tool exista. |
| Razonamiento oculto | ✅ `--hidethinking`. |

**Veredicto:** el prompt endurecido corrige los fallos críticos. Fase 2 aprobada.

### Fase 3 — Motor RAG (2026-11-13)

**Documentos de entrada**

| Archivo | Páginas | Contenido |
|---------|---------|-----------|
| `Manual de Procedimientos Administrativos.pdf` | 2 | CB-ADM-001: derivaciones, obras sociales, auditoría, alta administrativa. |
| `Protocolo de Servicios y Contactos Internos.pdf` | 2 | CB-SRV-002: horarios de servicios y directorio de contactos. |

Ambos se cargaron y se verificó la extracción de texto con `PyPDFLoader`.

**Archivo creado: `app/rag/indexer.py`**

| Componente | Función |
|------------|---------|
| `RagConfig` | Configuración por entorno: `DATA_DIR`, `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION`, `OLLAMA_EMBED_MODEL`, `OLLAMA_BASE_URL`. |
| `load_documents()` | Carga recursiva de `*.pdf` con `PyPDFLoader`; agrega metadata `archivo`, `documento`, `pagina` (1-based) y advierte páginas sin texto. |
| `split_documents()` | `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` + `chunk_id`. |
| `get_embeddings()` | `OllamaEmbeddings(model="nomic-embed-text")` contra Ollama. |
| `get_vector_store()` | `Chroma` persistente en `/vector_store`, colección `protocolos_clinica`, similitud coseno. |
| `index_pdfs()` | Reset opcional de la colección + `add_documents`; devuelve estadísticas. |
| `search_protocols()` / `search_protocols_with_score()` | Búsqueda por similitud (y con distancia para diagnóstico). |
| `__main__` | CLI: `python -m app.rag.indexer` (`--no-reset` para agregar sin borrar). |

**Ejecución**

```powershell
docker compose build
docker compose run --rm api python -m app.rag.indexer
```

Resultado:

| Métrica | Valor |
|---------|-------|
| Archivos | 2 |
| Páginas | 4 |
| Fragmentos | 7 |
| IDs indexados | 7 |
| Colección | `protocolos_clinica` |
| Persistencia | `/code/vector_store` |
| Embeddings | `nomic-embed-text` (768 dims) vía `host.docker.internal:11434` |
| Tiempo de embeddings | ~15 s |

**Persistencia verificada**

- Se ejecutó la búsqueda desde contenedores nuevos (`docker compose run --rm`) leyendo el
  volumen `./vector_store`.
- `collection.count()` → 7 documentos.
- Se limpiaron las colecciones temporales de las pruebas; solo queda
  `protocolos_clinica` (segmento activo `d09bbfc3-...`).

**Pruebas de recuperación (top-3)**

| Consulta | Resultado observado |
|----------|---------------------|
| Horario de Diagnóstico por Imágenes | Recupera el protocolo de servicios (incluye Lun-Vie 07:00-20:00, Sáb 08:00-13:00, Subsuelo-Ala Sur). ✅ |
| Cómo se gestiona una derivación administrativa | Recupera el procedimiento de 5 pasos del manual. ✅ |
| Documentación para resonancia magnética | Recupera la sección de autorización de obras sociales. ✅ |
| Historia clínica en papel | Recupera la nota de derogación (registro digital). ✅ |
| Extensión/correo de un área (ej. Gestión de Pacientes) | ⚠️ El top-3 no siempre incluye la fila exacta; con `k=7` sí aparece. |
| Correo de Facturación y Egresos | ⚠️ El chunk del directorio queda debajo de otros por dilución del embedding. |

**Diagnóstico de la limitación**

- `nomic-embed-text` (137M) diluye el contenido de chunks largos: la similitud entre el email
  exacto y la fila aislada es **0.80**, pero baja a **0.62** frente al chunk completo de 690
  caracteres que lo contiene. Chunks no relacionados alcanzan 0.65-0.68.
- Con `k=7` (todos los fragmentos del corpus actual) la información siempre está disponible
  para el LLM, pero no es una estrategia escalable.

**Experimentos realizados (documentados, no adoptados)**

| Experimento | Resultado | Decisión |
|-------------|-----------|----------|
| Prefijos Nomic (`search_document:` / `search_query:`) | Mejora leve de distancias; no corrige el ranking de contactos. | No adoptado (el plan indica `OllamaEmbeddings` estándar). |
| Chunks enriquecidos con documento/página/sección | Mejora el contexto, pero la tabla sigue dentro de un chunk dominado por horarios. | No adoptado. |
| Corte por secciones + splitter 1000/200 | Aísla el directorio en un chunk propio; ranking aún inestable para correos. | No adoptado para respetar el plan. |
| Chunks 500/100 y 300/60 | Mejora el top-3 de contactos, pero “correo de Facturación” sigue fallando; más fragmentos. | No adoptado: el plan fija 1000/200. |
| Similitud coseno directa contra Ollama | Confirma que el problema es el embedding, no Chroma. | Insumo para la mitigación de Fase 4. |

**Recomendación para la Fase 4**

- `buscar_protocolo` con `k=6` o `k=7` para el corpus actual.
- Evaluar una **recuperación híbrida**: `similarity_search` + coincidencia léxica de
  nombres/correos/extensiones (ej. “Facturación”, “Int. 104”). Requiere autorización por ser
  una mejora fuera del texto literal del plan.
- Si el corpus crece, migrar a un re-ranker o a un modelo de embeddings con mejor precisión.

**Observaciones técnicas**

- `langchain-community` emite un `DeprecationWarning` (paquete en sunset); se mantiene
  `PyPDFLoader` porque el plan lo exige.
- La colección usa distancia coseno (`hnsw:space=cosine`).
- Los rechazos/aclaraciones del agente siguen dependiendo del SYSTEM prompt y de las tools
  reales de la Fase 4.

### Fase 4 — Implementación, bloqueo y resolución (2026-11-13)

**Archivos creados**

| Archivo | Contenido |
|---------|-----------|
| `app/agent/tools.py` | `buscar_protocolo` (híbrida vectorial + léxica), `consultar_contacto_area` (directorio documentado), `derivar_solicitud` (ticket simulado). |
| `app/agent/core.py` | `ChatOllama` con `bind_tools`, bucle manual de tool-calling, filtrado de razonamiento, historial y fallback. |

**Pruebas aisladas de las tools (sin LLM)**

| Prueba | Resultado |
|--------|-----------|
| `hybrid_search("¿A qué extensión deriva Gestión de Pacientes?")` | ✅ Incluye el fragmento con `Int. 104`. |
| `hybrid_search("correo de Facturación y Egresos")` | ✅ Primer resultado contiene `facturacion@clinicabenitez.com`. |
| `consultar_contacto_area("auditoría médica")` | ✅ Dr. Carlos Villalba, Int. 220, correo oficial. |
| `derivar_solicitud("dolor de pecho", "urgencias")` | ✅ Ticket `T-20261113-...` generado. |

La recuperación híbrida autorizada funciona y corrige los contactos exactos.

**Prueba del agente (`run_agent`)**

```python
run_agent("¿Cuál es el horario de Diagnóstico por Imágenes?")
```

Resultado:

- `herramientas_usadas = []` (no llamó a `buscar_protocolo`).
- Respuesta inventada: “8:00 a 14:00 y 15:00 a 18:00 todos los días…”, datos que no están en los PDFs.

**Diagnóstico del bloqueo**

| Prueba | Resultado |
|--------|-----------|
| `ChatOllama.bind_tools(...)` + invoke | No genera `tool_calls`. |
| Ollama API directa (`/api/chat` con `tools`) sobre `agente-clinica` | `tool_calls=None`; responde texto inventado. |
| Ollama API directa sobre `deepseek-r1:8b` (modelo base) | `tool_calls=None`; mismo comportamiento. |
| Prompt explícito “usá la herramienta” + `think=False` | El modelo escribe `get_weather(city="Paris")` como **texto**, no como tool call estructurado. |
| Protocolo JSON manual | Eligió mal la tool (`derivar_solicitud` para una consulta de horarios) y la segunda consulta superó 10 minutos. |
| Salida JSON estructurada (`format` + enum + few-shot) | Volvió a elegir `derivar_solicitud` para horarios y se colgó en la consulta siguiente. |

**Conclusión**

- El problema **no es LangChain ni el código**: el modelo `deepseek-r1:8b` no emite el formato de
  tool calls que Ollama/LangChain esperan (aunque `ollama show` declare `tools`).
- El modelo parece entrenado con otra sintaxis de funciones; además mostró latencias muy altas
  en las pruebas de routing.
- `bind_tools()` no puede funcionar de forma nativa con este modelo en este entorno.

**Opciones (requiere decisión del usuario)**

| Opción | Ventaja | Costo |
|--------|---------|-------|
| A. Cambiar el modelo de generación por uno con tool calling nativo probado (ej. `qwen3:8b` o `llama3.1:8b`) | Mantiene `bind_tools` y el diseño del plan. | Descargar ~5 GB y recompilar el Modelfile. |
| B. Mantener `deepseek-r1:8b` y orquestar de forma determinista | RAG siempre fundamentado; sin alucinaciones de horarios. | No usa function calling nativo; el LLM solo redacta la respuesta. |
| C. Mantener el modelo y parsear llamadas en texto/JSON | No descarga modelos. | Routing poco confiable y latencia alta (evidencia de las pruebas). |

**Recomendación:** A para cumplir el objetivo de function calling nativo; B si se prioriza
confiabilidad sin descargar otro modelo. C no se recomienda.

**Decisión del usuario:** Opción A con `llama3.1:8b`.

**Resolución aplicada (2026-11-13)**

1. `Modelfile`: `FROM deepseek-r1:8b` → `FROM llama3.1:8b`, manteniendo `temperature 0.2`
   y el SYSTEM prompt completo.
2. `ollama create agente-clinica -f Modelfile` → `success` (modelo recompilado).
3. `app/agent/core.py` incorpora un `SystemMessage` con reglas obligatorias de operación
   (institucional → `buscar_protocolo`; contacto → `consultar_contacto_area`;
   clínico/emergencia → `derivar_solicitud`; no inventar datos).
4. Guardrail determinista: agrega el ticket si el modelo lo omite y antepone la indicación de
   guardia/emergencias cuando corresponde.
5. `app/agent/tools.py` mantiene la búsqueda híbrida autorizada (vectorial + léxica).

**Validación final de la Fase 4**

| Consulta | Tool invocada | Resultado |
|----------|---------------|-----------|
| “¿Cuál es el horario de Diagnóstico por Imágenes?” | `buscar_protocolo` | L-V 07:00-20:00, Sáb 08:00-13:00, Subsuelo-Ala Sur. Sin invenciones. |
| “¿A qué extensión debo llamar para una derivación administrativa?” | `consultar_contacto_area` | Int. 104, Lic. Mariana Torres, correo oficial. |
| “Me duele el pecho, ¿qué medicamento tomo?” | `derivar_solicitud` | Emergencia primero, sin medicación, ticket `T-20261113-...`. |
| “¿Y los sábados?” con historial | `buscar_protocolo` | Mantiene contexto y responde 08:00-13:00. |
| “Necesito un turno” | `buscar_protocolo` | Pide aclaración de servicio/especialidad. |

**Estado:** ✅ Fase 4 completada y validada. El detalle de los cambios de modelo y guardrails
está en `cambios.md`.

### Fase 5 — API REST (2026-11-13)

**Archivos creados**

| Archivo | Contenido |
|---------|-----------|
| `app/api/schemas.py` | `ChatMessage` (rol `user`/`assistant`), `ChatRequest` (`message` + `history`) y `ChatResponse` (`respuesta`, `herramientas_usadas`, `pasos`). |
| `app/api/routes.py` | `POST /api/chat`; ejecuta `run_agent`, valida errores y devuelve solo la respuesta final. |
| `app/main.py` | Incluye el router, versión `0.2.0` y mantiene `GET /health`. |

**Contrato de `POST /api/chat`**

```json
{
  "message": "¿Cuál es el horario de Diagnóstico por Imágenes?",
  "history": [
    {"role": "user", "content": "Hola"},
    {"role": "assistant", "content": "¿En qué puedo ayudarte?"}
  ]
}
```

```json
{
  "respuesta": "El horario de Diagnóstico por Imágenes es: ...",
  "herramientas_usadas": ["buscar_protocolo"],
  "pasos": 2
}
```

**Validaciones y errores**

- `message`: obligatorio, 1-4000 caracteres.
- `history`: máximo 50 mensajes; roles permitidos `user`/`assistant`.
- Roles `system`/`tool` enviados por el cliente → `422`.
- Mensaje vacío → `422`.
- Fallo de Ollama/Chroma → `503` con mensaje controlado y log del traceback.
- No se expone el razonamiento interno ni trazas al cliente.

**Pruebas ejecutadas**

| Prueba | Resultado |
|--------|-----------|
| `GET /health` con TestClient | `200` `{"status":"ok",...}`. |
| `POST /api/chat` (horario) con TestClient | `200`; `buscar_protocolo`; datos reales del PDF. |
| `POST /api/chat` con `message=""` | `422`. |
| `POST /api/chat` con rol `system` | `422`. |
| `docker compose up -d --build` | Contenedor `Up (healthy)` en `8000`. |
| `POST /api/chat` end-to-end (horario) | `200`; L-V 07:00-20:00, Sáb 08:00-13:00, Subsuelo-Ala Sur. |
| `POST /api/chat` con historial (“¿Y los sábados?”) | `200`; mantiene contexto y responde 08:00-13:00. |
| `POST /api/chat` (contacto) | `200`; `consultar_contacto_area`; Int. 104. |
| `GET /openapi.json` | Contiene `/api/chat`. |

**Nota de codificación**

- La API devuelve JSON UTF-8 correcto (`Diagn\xc3\xb3stico` en bytes).
- Algunas consolas de PowerShell muestran caracteres raros (`DiagnA3stico`); es un problema de
  visualización del terminal, no de la respuesta HTTP.

**Decisiones**

- Endpoint síncrono (`def`): FastAPI lo ejecuta en threadpool, adecuado para LangChain/Ollama.
- Se acepta `message` + `history`; el prompt actual va separado del historial.
- Sin autenticación ni CORS (fuera del alcance del plan).
- El cliente nunca puede inyectar mensajes `system`/`tool`.

### Frontend — Fase 1: CORS en el backend (2026-11-13)

**Cambio aplicado en `app/main.py`**

- Import de `CORSMiddleware` desde `fastapi.middleware.cors`.
- Orígenes permitidos: `http://localhost:5173` y `http://localhost:3000`.
- `allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=False`.
- Sin dependencias nuevas: `CORSMiddleware` viene con FastAPI/Starlette.

**Validación**

```powershell
docker compose up -d --build api
curl.exe -i -s -X OPTIONS "http://localhost:8000/api/chat" `
  -H "Origin: http://localhost:5173" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: content-type"
```

Resultado:

- `HTTP/1.1 200 OK`.
- `access-control-allow-origin: http://localhost:5173`.
- `access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT, QUERY`.
- `access-control-allow-headers: content-type`.

También se verificó `GET /health` con `Origin: http://localhost:5173` → 200 con el header CORS.

**Estado:** ✅ Fase 1 completada. El backend sigue funcionando en `http://localhost:8000`.

### Reorganización a monorepo (2026-11-13)

**Motivo:** separar backend y frontend en carpetas independientes, manteniendo un único
`docker-compose.yml` en la raíz.

**Movimientos:**

- `app/`, `data/`, `vector_store/`, `Dockerfile`, `requirements.txt`, `Modelfile`,
  `.dockerignore`, `.env.example`, `README.md`, `desarollo.md`, `cambios.md` → `backend/`.
- Permanecen en la raíz: `docker-compose.yml`, `.gitignore` (actualizado) y nuevo `README.md`.

**Cambios en `docker-compose.yml`:**

- `build: .` → `build: ./backend`.
- Volúmenes `./data` y `./vector_store` → `./backend/data` y `./backend/vector_store`.
- Sin `env_file` (no existe `.env` real); se mantienen los valores por defecto en
  `environment`.

**Verificación:**

- `docker compose config --quiet` → OK.
- `docker compose up -d --build` → API `Up (healthy)`.
- `GET /health` → `200`.
- `DOCS: 7` → índice Chroma intacto tras el movimiento.
- `POST /api/chat` (“horario de Diagnóstico por Imágenes”) → `200`, `buscar_protocolo`,
  datos reales.

**Estado:** ✅ reorganización completada sin pérdida del índice ni cambios de contrato.

### Ajustes pre-despliegue — Parte A (2026-11-13)

#### A.2 — Fallback de tool calls embebidas en texto

**Problema:** `llama3.1:8b` ocasionalmente emite la intención de llamar una tool como JSON
dentro de `content` (`{"name": "...", "parameters": {...}}`) en lugar de poblar
`response.tool_calls`. El ciclo de herramientas no se ejecutaba y el usuario veía JSON crudo.

**Solución aplicada en `app/agent/core.py`:**

- `_extract_json_object()`: extrae el primer objeto JSON válido, incluso dentro de bloques
  Markdown o texto adicional, respetando strings y llaves anidadas.
- `_parse_text_tool_call()`: valida que `name` exista en `TOOL_MAP` y acepta
  `parameters` o `arguments` (objeto o string JSON).
- Si el JSON es válido y la tool existe:
  - se reemplaza el `AIMessage` crudo por uno con `tool_calls` estructurado;
  - se ejecuta la tool y se agrega el `ToolMessage` con el resultado;
  - el modelo vuelve a invocarse para redactar la respuesta final.
- Si el texto **parece** un intento de tool call (`{` + `"name"`/`"parameters"`/
  `"arguments"`) pero no se puede interpretar, se devuelve un mensaje seguro:
  “No encontré información institucional sobre esa consulta o no pude procesarla
  correctamente. ¿Podrías reformularla?”.
- No se agregaron dependencias: solo `json` y `uuid` de la librería estándar.

**Porqué:** mantiene el diseño de `bind_tools` sin depender de que el modelo respete siempre
el formato estructurado. El reemplazo del mensaje crudo evita que el modelo repita el JSON y
garantiza que la interfaz nunca lo muestre.

**Pruebas (agente simulado, sin depender del modelo):**

| Caso | Resultado |
|------|-----------|
| JSON válido con `parameters` | ✅ Ejecuta `buscar_protocolo`; 2 invocaciones; `ToolMessage` con documentación. |
| JSON válido con `arguments` string | ✅ Ejecuta `consultar_contacto_area`; respuesta final. |
| Tool desconocida | ✅ Mensaje seguro; no ejecuta tools; sin JSON. |
| JSON malformado | ✅ Mensaje seguro; no ejecuta tools; sin JSON. |

#### A.3 — Blindaje de contactos y saludos en el `Modelfile`

**Cambios:**

- Prohibición explícita de inventar teléfonos, internos, correos, horarios o contactos fuera
  de `consultar_contacto_area` / `buscar_protocolo`.
- Regla para responder saludos simples, despedidas y preguntas de identidad sin invocar
  herramientas.
- Criterios 10 y 11 de autoevaluación para contactos y saludos.

**Recompilación:**

```powershell
ollama create agente-clinica -f backend/Modelfile
```

Resultado: `success` (reutiliza las capas de `llama3.1:8b`).

**Hallazgo durante la validación:** el prompt por sí solo no impidió que “Hola” disparara
`buscar_protocolo`. Por eso se agregó:

- regla de saludos al `SystemMessage` de operación en `core.py`;
- bypass determinista para saludos simples (`_GREETING_RE`), con respuesta directa y
  `pasos=0`;
- guardrail de ambigüedad (`_is_vague_service_request`) para consultas como “disponibilidad
  del servicio” u “horario de atención” sin área específica: pide aclaración sin consultar
  Chroma.

**Porqué:** el requisito institucional prohíbe alucinar contactos y el prompt no era
suficiente frente a un modelo cuantizado. Los guardrails garantizan el comportamiento y
reducen latencia/consultas vectoriales innecesarias.

**Pruebas:**

| Consulta | Resultado |
|----------|-----------|
| “Hola” / “Buenos días” | ✅ `TOOLS: []`, `PASOS: 0`, respuesta directa. |
| “¿A qué extensión debo llamar para Auditoría Médica?” | ✅ `consultar_contacto_area`, Int. 220. |
| “¿Cuál es el teléfono general de la clínica?” | ✅ No inventa teléfono; informa que no está en la documentación. |
| “Quiero saber la disponibilidad del servicio” | ✅ Pide aclaración, `TOOLS: []`, `PASOS: 0`. |
| “¿Cuál es el horario de Diagnóstico por Imágenes?” | ✅ `buscar_protocolo`, horarios reales. |

#### Validaciones de la Parte A (backend)

- `docker compose up -d --build api` → API healthy.
- Fallback simulado: 4/4 casos OK.
- Recompilación del modelo: `success`.
- Saludos, contactos, ambigüedad y RAG: OK.

#### A.4 — Prevención de extrapolación en procedimientos no documentados

**Problema observado:** el Escenario 5 (“protocolo para trasplantes cardíacos”) recuperaba
fragmentos de derivación/traslado generales y el modelo los presentaba como el protocolo del
trasplante. Además, en “documentación para resonancia magnética” mezclaba pasos de
autorización de obras sociales con pasos de derivación (cama, ambulancia).

**Porqué importa:** el requisito institucional prohíbe inventar o extrapolar protocolos
clínicos. Un trasplante cardíaco no está documentado en los PDFs; la respuesta correcta es
admitirlo y no fabricar un procedimiento. La resonancia sí está documentada, pero solo en la
sección de autorización de obras sociales.

**Cambios:**

1. `core.py` (`SystemMessage`) y `Modelfile`: regla explícita de no extrapolación y regla
   positiva para prácticas sí documentadas.
2. `core.py` fallback: reparación de escapes Unicode inválidos (`\u00i` → `í`, etc.) que el
   modelo generaba al escribir “cardíacos” y que invalidaban el JSON.
3. `tools.py` `buscar_protocolo`: filtro por términos específicos.
   - Si ningún fragmento menciona la especialidad/procedimiento, devuelve una instrucción de
     “sin protocolo específico”.
   - Si la consulta es de un procedimiento puntual, prioriza un solo fragmento para evitar
     mezclar secciones.
   - Si es una consulta administrativa general (derivación, traslado, obras sociales,
     auditoría), conserva hasta 4 fragmentos para no perder pasos.
4. Recompilación del modelo:

```powershell
ollama create agente-clinica -f backend/Modelfile
```

5. Guardrail determinista: si `buscar_protocolo` devuelve la instrucción de “sin protocolo
   específico” y la respuesta final no lo menciona, se reemplaza por un mensaje explícito
   que aclara la ausencia de protocolo documentado y ofrece una derivación.

**Validaciones:**

| Consulta | Resultado |
|----------|-----------|
| Trasplantes cardíacos | ✅ No hay protocolo específico; no extrapola. |
| Resonancia magnética | ✅ Solo autorización de obras sociales/auditoría. |
| Derivación administrativa | ✅ 5 pasos completos. |
| Horario de imágenes | ✅ Sin regresión. |
| Extensión de Auditoría Médica | ✅ Sin regresión. |
| Emergencia de pecho | ✅ Sin regresión. |
| “Hola” | ✅ Sin regresión. |

**Decisión de diseño:** la regla en el prompt se complementa con el filtro de recuperación.
El prompt por sí solo no impedía que el modelo mezclara fragmentos solapados; el filtro
garantiza que, si no hay evidencia específica, el agente no reciba pasos generales como si
fueran el protocolo consultado.

### RAG proactivo y fluidez conversacional (2026-11-16)

**Problema:** `llama3.1:8b` podía bloquearse formateando JSON con tildes al intentar invocar
`buscar_protocolo`, y los seguimientos cortos (“Centro quirúrgico”, “¿Y los sábados?”) no
siempre recuperaban el contexto anterior. Además, dejar tres tools disponibles aumentaba las
llamadas innecesarias y el riesgo de exponer nombres internos.

**Decisión arquitectónica:** mover la recuperación documental a Python y dejar al modelo solo
las acciones que requieren una decisión conversacional (contacto y derivación).

#### 1. Resolución de contexto multi-turno

- Si el mensaje actual tiene **4 palabras o menos** y existe un turno previo del usuario, se
  arma una consulta de búsqueda combinando ambos:
  `"Horario de atención" + "Centro quirúrgico"`.
- Solo se usa para la recuperación; el mensaje que recibe el LLM sigue siendo el actual.
- Si el turno anterior era un saludo, no se combina.
- **Porqué:** el usuario no debería repetir el tema completo en un seguimiento natural. La
  expansión mejora la recuperación sin alterar el hilo de la conversación.

#### 2. RAG proactivo antes del LLM

- Antes de invocar a `ChatOllama`, el backend ejecuta `buscar_protocolo` con la consulta
  expandida.
- Los fragmentos se inyectan como un `SystemMessage` de **CONTEXTO INSTITUCIONAL**.
- Si se usaron fragmentos, se registra `buscar_protocolo` en `herramientas_usadas` para que el
  frontend muestre el badge RAG.
- Si no hay protocolo específico, se inyecta la instrucción de no extrapolación y se activa el
  guardrail determinista.
- **Porqué:** elimina la dependencia de que el modelo de 8B genere un JSON perfecto para una
  búsqueda que el backend puede ejecutar directamente. Reduce latencia, errores de formato y
  llamadas innecesarias.

#### 3. Tool calling reducido

- `bind_tools()` recibe solo `consultar_contacto_area` y `derivar_solicitud`.
- `buscar_protocolo` sigue existiendo en `TOOL_MAP` para el RAG proactivo y el fallback parser,
  pero no se ofrece al modelo como herramienta.
- **Porqué:** menos tools = menos oportunidades de JSON inválido, menos ruido en la selección
  y un flujo más predecible. El fallback parser queda como red de seguridad.

#### 4. Prompt y cero nombres internos

- El SYSTEM prompt ahora indica que la documentación se recupera automáticamente y se entrega
  como contexto; el modelo no debe invocar una tool de búsqueda.
- Se prohíbe mencionar nombres de herramientas, funciones, modelos, bases vectoriales o
  detalles técnicos en la respuesta.
- Se agregó una sanitización determinista (`_sanitize_internal_terms`) que reemplaza nombres
  internos si el modelo los menciona igual.
- **Porqué:** el usuario final debe recibir una respuesta institucional, no detalles de
  implementación. El prompt solo no garantiza el cumplimiento; la sanitización actúa como red.

#### 5. Guardrails conservados y ampliados

- El guardrail de ambigüedad se mantiene **antes** del RAG proactivo: evita búsquedas
  vectoriales inútiles y preserva la respuesta determinista del Escenario 3.
- El RAG proactivo se omite en emergencias clínicas.
- Si el modelo no genera ticket en una emergencia, el backend ejecuta
  `derivar_solicitud` de forma determinista.
- Si el modelo omite el interno recuperado por contacto, se devuelve el contacto real.
- La no extrapolación se mantiene con el filtro de relevancia y el guardrail de “sin protocolo
  específico”.
- **Porqué:** la seguridad y la fidelidad documental no pueden depender de la variabilidad del
  modelo.

#### 6. RAG frente a fine-tuning o context stuffing

Se eligió RAG proactivo frente a las otras dos alternativas:

- **Fine-tuning:** exigiría reentrenar cada vez que cambian horarios, contactos o protocolos,
  no garantiza trazabilidad de la fuente y consume más recursos.
- **Context stuffing:** enviar todos los documentos en cada prompt aumenta tokens, latencia y
  costo, y puede diluir la información relevante. Además, el corpus puede crecer.
- **RAG:** permite actualizar PDFs y reindexar sin reentrenar, recupera solo lo relevante,
  permite citar documento/página y mantiene los datos en local.
- **Privacidad:** los PDFs, embeddings y modelos quedan en el equipo; no se envía información
  hospitalaria a la nube.

#### 7. Flujo resultante

```text
Mensaje
  ├─ saludo → respuesta directa
  ├─ ambigüedad → aclaración determinista
  ├─ emergencia → sin RAG; LLM + derivación/ticket garantizado
  └─ consulta institucional/contacto
       ├─ expansión de contexto si es corta
       ├─ RAG proactivo en Python
       ├─ CONTEXTO INSTITUCIONAL al LLM
       ├─ tools: contacto / derivación
       └─ sanitización + guardrails + respuesta final
```

#### 8. Validaciones

| Prueba | Resultado |
|--------|-----------|
| Horario de Diagnóstico por Imágenes | ✅ RAG proactivo, badge `buscar_protocolo`, horarios reales. |
| “Horario de atención” | ✅ Pide aclaración; no consulta Chroma. |
| Seguimiento “Centro quirúrgico” | ✅ Expande contexto y responde 09:00–15:00. |
| Seguimiento “¿Y los sábados?” | ✅ Responde 08:00–13:00 con el contexto anterior. |
| Contacto de Auditoría Médica | ✅ Interno 220 y correo real. |
| Emergencia por dolor de pecho | ✅ Guardia/emergencias, sin medicación, ticket. |
| Trasplantes cardíacos | ✅ Sin protocolo específico; no extrapola. |
| “Hola” | ✅ Sin tools, `pasos=0`. |
| Nombres internos en respuestas | ✅ Ninguno; sanitización activa. |

**E2E de interfaz:** 5 escenarios del sidebar + seguimiento
“Horario de atención” → “Centro quirúrgico”. Los escenarios enviaron `history: []`; el
seguimiento envió `history` con los dos mensajes previos. Resultado: `UI_PROACTIVE_E2E_OK`, sin
errores de consola y con ambos contenedores healthy.

**Recompilación del modelo:**

```powershell
ollama create agente-clinica -f backend/Modelfile
```

### CORS para desarrollo en puertos alternativos e IP local (2026-11-17)

**Problema:** al abrir el frontend de desarrollo en `http://172.23.48.1:5174`, el navegador
bloqueaba `/health` y `/api/chat` porque el backend solo permitía `localhost:5173` y
`localhost:3000`. Vite puede elegir `5174` si `5173` está ocupado, y WSL/LAN puede servir la
interfaz desde una IP privada.

**Solución:** además de `allow_origins`, se agregó `allow_origin_regex` para aceptar:

- `http://localhost` y `http://127.0.0.1` en cualquier puerto.
- IP privadas `10.x.x.x`, `172.16–31.x.x` y `192.168.x.x` en cualquier puerto.

`allow_credentials` sigue en `False` porque no hay autenticación ni cookies.

**Porqué:** el entorno de desarrollo cambia de puerto y de IP con facilidad; una lista fija de
orígenes genera errores CORS intermitentes. La regex cubre el desarrollo local sin abrir CORS a
dominios públicos. En producción debe restringirse a los dominios reales.

**Validación:**

- Preflight con `Origin: http://172.23.48.1:5174` → `200` y
  `access-control-allow-origin` correcto.
- Preflight con `http://localhost:5174` → `200`.
- Preflight con `http://localhost:5173` → `200`.
- Origen externo `http://evil.example` → `400` sin header CORS.
- E2E en `http://172.23.48.1:5174`: estado **Online**, `POST /api/chat` `200` y respuesta con
  horarios reales, sin errores CORS.

## Comandos ejecutados

| Fecha | Comando | Resultado |
|-------|---------|-----------|
| 2026-11-12 | `Get-ChildItem -Force` | Directorio del proyecto vacío; se inicia la bitácora. |
| 2026-11-12 | `docker --version` | Docker 29.7.2. |
| 2026-11-12 | `docker compose version` | Docker Compose v5.5.1. |
| 2026-11-12 | `docker compose config --quiet` | Compose válido, sin errores de sintaxis. |
| 2026-11-12 | `Get-ChildItem -Recurse -Force` | Árbol del proyecto verificado tras Fase 1. |
| 2026-11-12 | `docker compose build` (1er intento) | ❌ Falló: Docker Desktop estaba cerrado (`npipe:////./pipe/dockerDesktopLinuxEngine` no encontrado). No fue un error del proyecto. |
| 2026-11-12 | `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"` | Docker Desktop iniciado. |
| 2026-11-12 | `docker info` (espera hasta 3 min) | Motor OK: 29.7.2, linux/x86_64. |
| 2026-11-12 | `docker compose build` (2do intento) | ✅ Imagen `clinica-benitez-api:latest` construida (1.02 GB). |
| 2026-11-12 | `docker compose up -d` | Contenedor `Up (healthy)`. |
| 2026-11-12 | `curl http://localhost:8000/health` | `{"status":"ok","service":"clinica-benitez-api"}`. |
| 2026-11-12 | `docker compose exec api curl http://host.docker.internal:11434/api/tags` | ✅ El contenedor alcanza Ollama en el host. |
| 2026-11-12 | `curl http://localhost:11434/api/tags` | Ollama 0.40.16 activo; `deepseek-r1:8b` con `tools`/`thinking`; `nomic-embed-text` ausente. |
| 2026-11-12 | `Invoke-RestMethod http://localhost:11434/api/tags` | ✅ `nomic-embed-text:latest` (274 MB, embedding) y `deepseek-r1:8b` (tools/thinking) presentes. |
| 2026-11-12 | `POST http://localhost:11434/api/embed` (nomic-embed-text) | ✅ Vector de 768 dimensiones generado correctamente. |
| 2026-11-12 | Creación manual de `Modelfile` | ✅ SYSTEM prompt con criterios de aceptación y `temperature 0.2`. |
| 2026-11-12 | `ollama create agente-clinica -f Modelfile` | ✅ `success`; modelo `agente-clinica:latest` (5.2 GB, ID `75186009066d`). |
| 2026-11-12 | `ollama list` | ✅ `agente-clinica`, `nomic-embed-text`, `deepseek-r1:8b` disponibles. |
| 2026-11-12 | `ollama run --help` | ✅ Soporta `--hidethinking` y `--think`; se usará para ocultar el razonamiento en consola. |
| 2026-11-12 | `ollama run agente-clinica` (prueba de usuario) | ⚠️ Identidad y rechazo clínico correctos; falló en emergencia y alucinó ticket/teléfono. |
| 2026-11-12 | Endurecimiento del `Modelfile` | ✅ Reglas anti-simulación, emergencia inmediata y cierre administrativo. |
| 2026-11-12 | `ollama create agente-clinica -f Modelfile` (recompilar) | ✅ Recompilado con el prompt endurecido (confirmado por el retest). |
| 2026-11-13 | `ollama run --hidethinking agente-clinica "Me duele el pecho..."` | ✅ Emergencia primero, sin medicación, sin ticket/teléfono inventados. Fase 2 validada. |
| 2026-11-13 | `Get-ChildItem data` | ✅ 2 PDFs cargados por el usuario (Manual administrativo y Protocolo de servicios). |
| 2026-11-13 | `PyPDFLoader(...).load()` (dentro del contenedor) | ✅ 2 páginas por PDF; texto extraído correctamente. |
| 2026-11-13 | `docker compose build` (incremental) | ✅ Imagen actualizada con `app/rag/indexer.py` (capas de pip en caché). |
| 2026-11-13 | `docker compose run --rm api python -m app.rag.indexer` | ✅ 2 archivos, 4 páginas, 7 fragmentos, 7 IDs; embeddings en ~15 s. |
| 2026-11-13 | Consulta de `collection.count()` desde contenedor nuevo | ✅ 7 documentos persistidos en `./vector_store`. |
| 2026-11-13 | `similarity_search_with_score` (5 consultas) | ✅ Horarios/derivaciones/resonancia/historia; ⚠️ contactos exactos dependen de `k`. |
| 2026-11-13 | Pruebas con prefijos Nomic, chunks enriquecidos, corte por secciones y tamaños 500/100 y 300/60 | ⚠️ Mejoras parciales; no adoptadas para respetar 1000/200. |
| 2026-11-13 | Similitud coseno directa (`ollama.Client.embed` + NumPy) | ✅ Confirmado: dilución del embedding en chunks largos (0.80 → 0.62). |
| 2026-11-13 | Limpieza de colecciones/segmentos temporales de prueba | ✅ Solo queda `protocolos_clinica` (7 docs). |
| 2026-11-13 | Creación de `app/agent/tools.py` y `app/agent/core.py` | ✅ Código creado; tools validadas de forma aislada. |
| 2026-11-13 | `docker compose run --rm api python -c "from app.agent.tools import ..."` | ✅ Híbrida encuentra `Int. 104`, correo de Facturación, contactos y ticket. |
| 2026-11-13 | `run_agent("¿Cuál es el horario de Diagnóstico por Imágenes?")` | ❌ No llamó tools (`tools_usadas=[]`) y alucinó horarios. |
| 2026-11-13 | Ollama `/api/chat` con `tools` (modelo `agente-clinica` y base) | ❌ `tool_calls=None`; el modelo responde texto. |
| 2026-11-13 | Prueba `get_weather(city="Paris")` | ❌ El modelo escribe la llamada como texto, no como tool call estructurado. |
| 2026-11-13 | Protocolo JSON manual y salida estructurada (`format` + enum + few-shot) | ❌ Eligió mal la tool y sufrió timeouts >10 min. |
| 2026-11-13 | `ollama list` | ✅ `llama3.1:8b` ya descargado por el usuario (4.9 GB). |
| 2026-11-13 | Prueba nativa con `llama3.1:8b` + tool `get_weather` | ✅ Devuelve `ToolCall(name='get_weather', arguments={'city': 'Paris'})`. |
| 2026-11-13 | `Modelfile`: `FROM` cambiado a `llama3.1:8b` | ✅ SYSTEM prompt y `temperature 0.2` intactos. |
| 2026-11-13 | `ollama create agente-clinica -f Modelfile` | ✅ `success`; modelo recompilado sobre `llama3.1:8b`. |
| 2026-11-13 | `run_agent("¿Cuál es el horario de Diagnóstico por Imágenes?")` | ✅ `buscar_protocolo`; L-V 07:00-20:00, Sáb 08:00-13:00, Subsuelo-Ala Sur. |
| 2026-11-13 | `run_agent("¿A qué extensión debo llamar para una derivación administrativa?")` | ✅ `consultar_contacto_area`; Int. 104 y correo oficial. |
| 2026-11-13 | `run_agent("Me duele el pecho, ¿qué medicamento tomo?")` | ✅ `derivar_solicitud`; emergencia primero, sin medicación, ticket visible. |
| 2026-11-13 | `run_agent("¿Y los sábados?", history=...)` | ✅ Mantiene contexto y responde 08:00-13:00. |
| 2026-11-13 | `run_agent("Necesito un turno")` | ✅ Pide aclaración de servicio/especialidad. |
| 2026-11-13 | Creación de `app/api/schemas.py`, `app/api/routes.py` y actualización de `app/main.py` | ✅ Endpoint `POST /api/chat` y `/health`. |
| 2026-11-13 | `docker compose build` | ✅ Imagen con la API REST (capas en caché). |
| 2026-11-13 | TestClient (`GET /health`, `POST /api/chat`, validaciones) | ✅ 200/200, vacío 422, rol inválido 422. |
| 2026-11-13 | `docker compose up -d --build` | ✅ Contenedor `Up (healthy)`; `/health` OK. |
| 2026-11-13 | `POST /api/chat` end-to-end (horario, historial, contacto) | ✅ 200; tools correctas y datos reales. |
| 2026-11-13 | `GET /openapi.json` | ✅ `/api/chat` documentado. |
| 2026-11-13 | CORS en `app/main.py` (5173 y 3000) | ✅ `CORSMiddleware` configurado; sin dependencias nuevas. |
| 2026-11-13 | `docker compose up -d --build api` | ✅ API recreada con CORS. |
| 2026-11-13 | Preflight `OPTIONS /api/chat` con Origin 5173 | ✅ 200 + `access-control-allow-origin`. |
| 2026-11-13 | `GET /health` con Origin 5173 | ✅ 200 + header CORS. |
| 2026-11-13 | `docker compose down` | ✅ Contenedor y red detenidos para mover `vector_store`. |
| 2026-11-13 | `Move-Item ... -Destination backend` | ✅ Backend movido a `backend/`; raíz con compose, `.gitignore` y README. |
| 2026-11-13 | `docker-compose.yml`: build y volúmenes a `./backend` | ✅ `docker compose config --quiet` OK. |
| 2026-11-13 | `docker compose up -d --build` (monorepo) | ✅ API `Up (healthy)`; `/health` OK. |
| 2026-11-13 | `DOCS: 7` tras mover `vector_store` | ✅ Índice Chroma intacto. |
| 2026-11-13 | `POST /api/chat` tras reorganización | ✅ 200; `buscar_protocolo`; horarios reales. |
| 2026-11-13 | `ollama create agente-clinica -f backend/Modelfile` | ✅ Prompt endurecido recompilado (`success`). |
| 2026-11-13 | Test simulado de fallback (4 casos) | ✅ Tool calls embebidas, tool desconocida y JSON inválido. |
| 2026-11-13 | `run_agent` saludos/contactos/ambigüedad | ✅ Sin tools en saludos, Int. 220 real, aclaración en consulta vaga. |
| 2026-11-13 | `docker compose up -d --build api` | ✅ API healthy con fallback y guardrails. |
| 2026-11-13 | Regla de no extrapolación en `Modelfile` + `SystemMessage` | ✅ Recompilado con `ollama create` (`success`). |
| 2026-11-13 | Reparación de escapes Unicode inválidos en fallback | ✅ `\u00i` → `í`; el JSON de trasplantes se parsea. |
| 2026-11-13 | Filtro de relevancia en `buscar_protocolo` | ✅ Sin protocolo específico para trasplantes; resonancia sin mezclar derivación. |
| 2026-11-13 | Regresión: horario, contacto, emergencia y saludo | ✅ Todos sin cambios. |
| 2026-11-16 | RAG proactivo + expansión multi-turno + tools reducidas | ✅ `buscar_protocolo` se ejecuta en Python; bind de contacto/derivación. |
| 2026-11-16 | Sanitización de nombres internos | ✅ Respuestas sin `buscar_protocolo`, `consultar_contacto_area` ni `derivar_solicitud`. |
| 2026-11-16 | Validación backend de 5 escenarios + seguimiento | ✅ RAG, contacto, ambigüedad, emergencia, no protocolo y “Centro quirúrgico”. |
| 2026-11-16 | E2E frontend con 5 escenarios + seguimiento | ✅ `UI_PROACTIVE_E2E_OK`; historial correcto y sin errores de consola. |
| 2026-11-17 | CORS con `allow_origin_regex` para localhost/IP privada | ✅ Vite 5174 e IP WSL habilitados; origen externo rechazado. |
| 2026-11-17 | E2E en `http://172.23.48.1:5174` | ✅ Online, `POST /api/chat` 200, sin errores CORS. |

## Librerías instaladas (requirements.txt)

`fastapi`, `uvicorn`, `langchain`, `langchain-ollama`, `langchain-chroma`,
`langchain-community`, `langchain-text-splitters`, `pypdf`.
Versiones exactas resueltas en la imagen: ver tabla de la Fase 1.

## Notas

- El `Modelfile` se compila en el **host** con:
  `ollama create agente-clinica -f Modelfile`
- Base actual del modelo: `llama3.1:8b` (cambio del 2026-11-13, ver `cambios.md`).
- El SYSTEM prompt de Fase 2 fija los criterios de aceptación: español siempre,
  contexto conversacional, RAG como única fuente, prohibición de diagnósticos/tratamientos,
  uso de tools, pedir aclaraciones y derivar cuando corresponda.
- `nomic-embed-text` está instalado y validado (768 dims).
- `agente-clinica:latest` compilado y con tool calling nativo verificado.
- `ollama run` no inyecta tools: el function calling real ocurre en `app/agent/core.py` con
  `bind_tools`; en consola el modelo solo cumple el rol/políticas del SYSTEM prompt.
- Chroma persiste en `./vector_store` (volumen) con la colección `protocolos_clinica`
  (7 fragmentos de los 2 PDFs actuales). Para reindexar:
  `docker compose run --rm api python -m app.rag.indexer`.
- Los cambios importantes y las incidencias que afectan el plan se registran en `cambios.md`.
- La API expone `POST /api/chat` y `GET /health`; documentación interactiva en `/docs`.

## Estado final

Las 5 fases del plan están completadas y validadas:

1. Entorno, Docker y monolito modular.
2. Modelfile con SYSTEM prompt (base final `llama3.1:8b`).
3. Motor RAG con Chroma + `nomic-embed-text`.
4. Agente con tools nativas, recuperación híbrida y guardrails.
5. API REST `POST /api/chat`.

**Cómo levantar el servicio**

```powershell
docker compose up -d --build
```

**Probar**

```powershell
curl.exe -s http://localhost:8000/health
```

```powershell
$body = @{ message = "¿Cuál es el horario de Diagnóstico por Imágenes?"; history = @() } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/chat -Body $body -ContentType "application/json"
```

**Siguientes pasos opcionales (fuera del plan, requieren autorización):**

- Tests automatizados con `pytest` para el agente y la API.
- Autenticación/CORS si se conecta un frontend.
- Re-ranker o modelo de embeddings mejor si crece el corpus.
- Métricas/observabilidad y límites de tasa.






