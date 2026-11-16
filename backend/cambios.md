# Registro de cambios e incidencias — Clínica Benitez

Bitácora de cambios importantes, decisiones técnicas e inconvenientes que modifican o
interfieren con el plan inicial. Se actualiza a medida que avanza el proyecto.

- **Proyecto:** API REST + Agente de IA local para Clínica Benitez.
- **Plan base:** 5 fases (entorno/Docker, Modelfile, RAG, agente/tools, API REST).
- **Última actualización:** 2026-11-13.

---

## 2026-11-13 — Prevención de extrapolación en procedimientos no documentados

**Motivo:** ante “¿Cuál es el protocolo para trasplantes cardíacos?”, el agente recuperaba
fragmentos sobre traslados/derivaciones generales y los presentaba como si fueran el protocolo
del procedimiento. Eso viola la regla institucional de no inventar ni extrapolar protocolos.

**Cambios aplicados:**

1. **Regla explícita en el `SystemMessage` de `core.py` y en `Modelfile`:**
   si los fragmentos hablan de traslados/trámites generales pero no mencionan la especialidad
   o procedimiento consultado, primero debe aclarar que la Clínica Benitez no cuenta con un
   protocolo específico documentado para ese procedimiento. Solo después puede mencionar
   pautas generales de derivación si corresponden.
2. **Regla positiva complementaria:** si la práctica sí está documentada (por ejemplo,
   resonancias magnéticas en la autorización de obras sociales), debe usar esos pasos y no
   responder que falta información.
3. **Reparación de escapes Unicode inválidos en el fallback parser:** el modelo emitió
   `\u00i` en “cardíacos”, un JSON inválido que activaba el mensaje seguro y impedía ejecutar
   la tool. Se normalizan casos como `\u00i/o/u/n` antes de parsear.
4. **Filtro de relevancia en `buscar_protocolo`:** si ningún fragmento menciona términos
   específicos de la consulta, devuelve una instrucción de “sin protocolo específico”. Si sí
   los menciona, prioriza el fragmento más relevante para evitar mezclar secciones
   (autorización de prácticas vs. derivación/traslado). Para consultas administrativas
   generales de derivación se conservan varios fragmentos para no perder pasos.
5. **Guardrail determinista de respuesta:** si la tool devuelve la instrucción de “sin
   protocolo específico” y el modelo final no menciona esa ausencia, la respuesta se
   reemplaza por un mensaje explícito que aclara que no hay protocolo documentado para el
   procedimiento y ofrece una derivación administrativa.

**Recompilación:**

```powershell
ollama create agente-clinica -f backend/Modelfile
```

Resultado: `success`.

**Pruebas:**

| Consulta | Resultado |
|----------|-----------|
| “Protocolo para trasplantes cardíacos” | ✅ “No hay un protocolo específico para trasplantes cardíacos”; no extrapola pasos. |
| “Documentación para resonancia magnética” | ✅ Solo pasos de autorización de obras sociales/auditoría; sin mezclar traslado/cama/ambulancia. |
| “Cómo se gestiona una derivación administrativa” | ✅ Los 5 pasos completos del manual. |
| Horario de Diagnóstico por Imágenes | ✅ Sin regresión; horarios reales. |
| Extensión de Auditoría Médica | ✅ Sin regresión; Int. 220. |
| Emergencia por dolor de pecho | ✅ Sin regresión; derivación y ticket. |
| “Hola” | ✅ Sin regresión; sin tools. |

**Impacto:** sin cambios en el contrato de la API; mejora la fidelidad documental y evita
mezclar procedimientos.

---

## 2026-11-13 — Cambio de modelo base: `deepseek-r1:8b` → `llama3.1:8b`

**Motivo:** `deepseek-r1:8b` no emite tool calls nativos en este entorno, aunque Ollama lo
declare con capacidad `tools`.

**Evidencia:**

- `ChatOllama.bind_tools(...)` no generaba `tool_calls`.
- La API directa de Ollama (`/api/chat` con `tools`) devolvía `tool_calls=None` tanto para
  `agente-clinica` como para `deepseek-r1:8b` base.
- El modelo escribía llamadas como texto: `get_weather(city="Paris")`.
- Un protocolo JSON manual eligió mal la herramienta (`derivar_solicitud` para una consulta
  de horarios) y sufrió timeouts >10 minutos.
- Con `llama3.1:8b` la misma prueba devolvió
  `ToolCall(function=Function(name='get_weather', arguments={'city': 'Paris'}))`.

**Cambio aplicado:**

- `Modelfile`: `FROM deepseek-r1:8b` → `FROM llama3.1:8b`.
- Se mantuvieron `temperature 0.2` y todo el SYSTEM prompt.
- Recompilación: `ollama create agente-clinica -f Modelfile` → `success`.

**Impacto:**

- `bind_tools` vuelve a ser viable y se cumple el objetivo de function calling nativo.
- `deepseek-r1:8b` queda instalado pero ya no se usa para generar respuestas.
- El modelo `agente-clinica` ahora pesa 4.9 GB (capas de `llama3.1:8b`).

**Validación:**

| Consulta | Tool usada | Resultado |
|----------|------------|-----------|
| Horario de Diagnóstico por Imágenes | `buscar_protocolo` | L-V 07:00-20:00, Sáb 08:00-13:00, Subsuelo-Ala Sur. |
| Extensión para derivación administrativa | `consultar_contacto_area` | Int. 104, `derivaciones@clinicabenitez.com`. |
| Dolor de pecho + medicación | `derivar_solicitud` | Sin diagnóstico; guardia/emergencias; ticket real. |
| “¿Y los sábados?” con historial | `buscar_protocolo` | Mantiene contexto y responde 08:00-13:00. |
| “Necesito un turno” | `buscar_protocolo` | Pide aclaración de servicio/especialidad. |

---

## 2026-11-13 — Reglas de operación y guardrails de seguridad

**Motivo:** con `llama3.1:8b`, la primera prueba clínica no derivó ni indicó emergencia; en
otra iteración registró la derivación pero omitió el ticket y no puso la emergencia primero.

**Cambios:**

1. `app/agent/core.py` agrega un `SystemMessage` con reglas obligatorias de operación:
   - institucional → `buscar_protocolo`;
   - contacto → `consultar_contacto_area`;
   - clínico/emergencia → `derivar_solicitud`;
   - emergencia → indicación de guardia/emergencias como primera frase;
   - no inventar horarios, contactos ni tickets.
2. Guardrail determinista en `core.py`:
   - si se usó `derivar_solicitud`, agrega el ticket a la respuesta si el modelo lo omitió;
   - si detecta términos de emergencia, antepone la indicación de guardia/emergencias
     cuando la respuesta no empieza con ella.
3. Lista de términos de emergencia ampliada (`dolor de pecho`, `duele el pecho`,
   `dificultad para respirar`, `desmayo`, `convulsión`, `sangrado abundante`, etc.).

**Impacto:** la seguridad no depende exclusivamente del cumplimiento del prompt por parte del
modelo. El guardrail no reemplaza al agente: solo corrige omisiones críticas.

**Validación:**

- “Me duele el pecho, ¿qué medicamento tomo?” →
  `TOOLS: ['derivar_solicitud']`, primera frase de emergencia, sin medicación y ticket
  `T-20261113-...`.

---

## 2026-11-13 — Recuperación híbrida autorizada (RAG)

**Motivo:** `nomic-embed-text` diluye chunks largos y los contactos exactos no siempre
aparecían en el top-3.

**Evidencia:**

- Similitud email aislado ↔ fila: **0.80**; email ↔ chunk completo: **0.62**.
- Chunks no relacionados: 0.65-0.68.
- `k=7` incluía la información, pero no es escalable.

**Cambio:** `buscar_protocolo` combina `similarity_search` con búsqueda léxica de
nombres/correos/extensiones, sin dependencias nuevas. Se mantiene Chroma y la colección
`protocolos_clinica`.

**Impacto:** las consultas de contactos ahora encuentran `Int. 104` y
`facturacion@clinicabenitez.com` de forma consistente.

---

## 2026-11-12 — LangChain 1.x en lugar de 0.3.x

**Motivo:** `requirements.txt` usaba mínimos sin versión fija y pip resolvió LangChain 1.5.0.

**Impacto:**

- `AgentExecutor` y `create_tool_calling_agent` ya no están en el paquete principal.
- Se implementó un bucle manual de tool-calling con `bind_tools` + `ToolMessage`.
- `langchain-community` quedó en sunset (emite `DeprecationWarning` por `PyPDFLoader`).

**Decisión:** mantener LangChain 1.x y el bucle manual; no se fijaron versiones 0.3.x.

---

## 2026-11-12 — Endurecimiento del SYSTEM prompt

**Motivo:** la primera prueba de `deepseek-r1:8b` inventó un ticket (`T-2024-0087`) y un
teléfono (`(04) 222-3456`) al no tener tools conectadas.

**Cambios en `Modelfile`:**

- Prohibición explícita de simular herramientas.
- Tickets y contactos solo si provienen de una tool real.
- Emergencia como primera indicación, sin esperar derivación.
- Prohibido cerrar con “¿algo más sobre tu salud?”.

**Impacto:** el modelo dejó de inventar tickets/teléfonos en consola. El problema de fondo
(falta de tools reales) se resolvió en Fase 4.

---

## 2026-11-12 — Docker Desktop detenido durante el build

**Incidencia:** `docker compose build` falló con
`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`.

**Causa:** Docker Desktop estaba cerrado; no era un error del proyecto.

**Resolución:** iniciar Docker Desktop y esperar a que el motor responda
(`docker info` → OK). Volvió a ocurrir el 2026-11-13 y se resolvió igual.

**Impacto:** ninguno sobre el código; sólo demora operativa.

---

## 2026-11-13 — Ajustes pre-despliegue (Parte A)

### Fallback para tool calls embebidas en texto

**Motivo:** `llama3.1:8b` puede devolver la llamada a una tool como JSON dentro de
`response.content` en vez de `tool_calls`, exponiendo JSON crudo y sin ejecutar la tool.

**Cambio:** `app/agent/core.py` incorpora:

- extracción robusta de JSON embebido;
- parseo de `{"name", "parameters"|"arguments"}` solo para tools registradas;
- reemplazo del mensaje crudo por un `AIMessage` con `tool_calls`;
- mensaje seguro si el JSON es inválido o la tool es desconocida.

**Validación:** 4/4 casos simulados OK (parameters, arguments string, tool desconocida,
JSON malformado).

### Blindaje de contactos y saludos

**Motivo:** evitar teléfonos/internos/correos inventados y consultas vectoriales inútiles
ante saludos.

**Cambio:**

- `Modelfile`: prohibición explícita de inventar contactos y regla de saludos.
- `core.py`: regla de saludos en el SystemMessage, bypass determinista para saludos simples
  y guardrail de ambigüedad para “disponibilidad/horario del servicio” sin área específica.

**Validación:**

- “Hola” / “Buenos días” → `TOOLS: []`, `PASOS: 0`.
- Auditoría Médica → Int. 220 (tool real).
- “Teléfono general” → no inventa; informa que no está documentado.
- “Disponibilidad del servicio” → pide aclaración sin consultar Chroma.

**Impacto:** ninguna dependencia nueva; se mantiene el contrato de la API.

---

## 2026-11-13 — Fase 5: API REST `POST /api/chat`

**Cambio:** se agregó la capa HTTP del monolito modular.

**Archivos:**

- `app/api/schemas.py`: `ChatMessage`, `ChatRequest` (`message` + `history`),
  `ChatResponse` (`respuesta`, `herramientas_usadas`, `pasos`).
- `app/api/routes.py`: `POST /api/chat`; ejecuta `run_agent` y traduce errores.
- `app/main.py`: incluye el router y mantiene `GET /health`; versión `0.2.0`.

**Contrato:**

```json
{"message": "...", "history": [{"role": "user", "content": "..."}]}
```

**Validaciones:**

- `message` obligatorio, 1-4000 caracteres.
- `history` máximo 50 mensajes; solo roles `user`/`assistant`.
- `system`/`tool` desde el cliente → `422`.
- Fallo de Ollama/Chroma → `503` controlado; sin trazas internas al cliente.

**Pruebas:**

- TestClient: `/health` 200; chat 200; mensaje vacío 422; rol inválido 422.
- Contenedor real: `Up (healthy)`; chat con horario, historial y contacto devuelve
  `200` con las tools correctas.
- `/openapi.json` incluye `/api/chat`.

**Nota operativa:** la API devuelve UTF-8 correcto; algunas consolas de PowerShell muestran
caracteres raros por encoding del terminal, no por la respuesta HTTP.

**Impacto:** no interfiere con el plan; completa la Fase 5.

---

## 2026-11-13 — Reorganización a monorepo (`backend/` + `frontend/`)

**Motivo:** separar el backend del próximo frontend React, manteniendo un único compose raíz.

**Movimientos:**

- `app/`, `data/`, `vector_store/`, `Dockerfile`, `requirements.txt`, `Modelfile`,
  `.dockerignore`, `.env.example`, `README.md`, `desarollo.md`, `cambios.md` → `backend/`.
- Raíz: `docker-compose.yml`, `.gitignore` actualizado y nuevo `README.md`.
- `.dockerignore` se movió a `backend/` porque el contexto de build es `./backend`.
- No se agregó `env_file` porque no existe un `.env` real; se mantienen los defaults en
  `environment`.

**Cambios en compose:**

```yaml
build: ./backend
volumes:
  - ./backend/data:/code/data
  - ./backend/vector_store:/code/vector_store
```

**Verificación:**

- `docker compose config --quiet` → OK.
- `docker compose up -d --build` → API `Up (healthy)`.
- `GET /health` → `200`.
- `DOCS: 7` → índice Chroma intacto.
- `POST /api/chat` → `200`, `buscar_protocolo`, datos reales.

**Impacto:** ninguno sobre el contrato de la API; habilita `frontend/` en la raíz.

---

## 2026-11-13 — CORS habilitado para el frontend

**Motivo:** el frontend React correrá en el navegador del host (`http://localhost:5173` /
`http://localhost:3000`) y necesita llamar a la API en `http://localhost:8000`.

**Cambio:** `app/main.py` incorpora `CORSMiddleware` con:

- `allow_origins=["http://localhost:5173", "http://localhost:3000"]`
- `allow_methods=["*"]`
- `allow_headers=["*"]`
- `allow_credentials=False` (no hay auth/cookies)

**Validación:**

- Preflight `OPTIONS /api/chat` con `Origin: http://localhost:5173` → `200` y
  `access-control-allow-origin: http://localhost:5173`.
- `GET /health` con el mismo Origin → `200` y header CORS.
- Sin dependencias nuevas; `CORSMiddleware` viene con FastAPI/Starlette.

**Impacto:** habilita la Fase 2 del frontend sin modificar el contrato de la API.

---

## 2026-11-13 — Documentación para puesta en marcha (`README.md`)

**Cambio:** se creó `README.md` con:

- Descripción del proyecto y arquitectura.
- Requisitos (Docker Desktop, Ollama, modelos).
- Pasos de instalación, compilación del `Modelfile`, build y levantado.
- Indexación de PDFs.
- Ejemplos de prueba de la API (horario, historial, contacto, emergencia).
- Prueba directa del agente y diferencia con `ollama run`.
- Variables de entorno, estructura, RAG/tools y solución de problemas.
- Alcance y límites.

**Impacto:** no modifica el código ni el plan; facilita la operación y las pruebas.

---

## Riesgos y pendientes conocidos

- `nomic-embed-text` sigue teniendo precisión limitada; la mitigación híbrida es actual.
  Si el corpus crece, evaluar un re-ranker o un modelo de embeddings mejor.
- `llama3.1:8b` puede omitir detalles del ticket o el orden de la emergencia; el guardrail
  determinista los corrige, pero conviene mantener pruebas de regresión.
- El proyecto no tiene autenticación ni base de datos adicional (fuera de alcance del plan).
- Las pruebas de tools se ejecutan dentro del contenedor con `docker compose run --rm`.
  Cada cambio de código requiere `docker compose build` antes de probar.
- Chroma persiste en `./vector_store`; para reindexar:
  `docker compose run --rm api python -m app.rag.indexer`.
