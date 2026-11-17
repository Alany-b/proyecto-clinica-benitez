# Desarrollo — Frontend Clínica Benitez

Bitácora técnica de la interfaz web. Se actualiza al finalizar cada fase.

## Visión general

- **Objetivo:** interfaz de chat para consultas administrativas, con estado del backend,
  escenarios de prueba y visualización de las herramientas usadas por el agente.
- **Stack:** React 19 + TypeScript + Vite 7 + Tailwind CSS v4.
- **Backend:** API en `http://localhost:8000` (ver `../backend/README.md`).

## Estado de fases

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | CORS en el backend | ✅ Completada (2026-11-13) |
| 2 | Inicialización y diseño del frontend | ✅ Completada (2026-11-13) |
| 3 | Dockerización (Node + Nginx) | ✅ Completada (2026-11-13) |
| 4 | Verificación end-to-end y cierre documental | ✅ Completada (2026-11-13) |

## Fase 1 — CORS en el backend

- `app/main.py` incorpora `CORSMiddleware` con orígenes `http://localhost:5173` y
  `http://localhost:3000`.
- `allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=False`.
- Validado con preflight `OPTIONS /api/chat` → `200` y `access-control-allow-origin`.
- Detalle completo en `../backend/desarollo.md` y `../backend/cambios.md`.

## Fase 2 — Inicialización y diseño del frontend

### Decisiones confirmadas

| Tema | Decisión |
|------|----------|
| Tailwind | v4 con `@tailwindcss/vite` (sin PostCSS manual). |
| Markdown | `react-markdown` + `remark-gfm`. |
| Escenarios | Envío automático en 1 clic; botones deshabilitados mientras `isLoading`. |
| React | React 19 + TypeScript estricto. |
| Estado | Hooks propios (`useState`, `useReducer` no necesario); sin Redux/Zustand. |
| UI | Tema oscuro, Tailwind puro, iconos SVG inline. |
| Routing | No se usa router: aplicación de una sola vista. |

### Estructura creada

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatWindow.tsx
│   │   ├── Header.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── Sidebar.tsx
│   │   ├── StatusIndicator.tsx
│   │   └── TypingIndicator.tsx
│   ├── hooks/
│   │   ├── useChat.ts
│   │   └── useHealth.ts
│   ├── lib/
│   │   └── api.ts
│   ├── types/
│   │   └── chat.ts
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   └── vite-env.d.ts
├── .dockerignore
├── .env.example
├── Dockerfile
├── index.html
├── nginx.conf
├── package.json
├── package-lock.json
├── tsconfig.json
└── vite.config.ts
```

### Diseño UI/UX

- **Header:** marca “CB”, título, estado de `/health` y botón “Nueva conversación”.
- **StatusIndicator:** online (verde), error 503 (rojo), verificando (ámbar); clic para
  revalidar.
- **Sidebar:** 5 escenarios con color por tipo; en móvil se abre como panel superpuesto.
- **ChatWindow:** estado vacío con bienvenida, lista de mensajes, indicador de escritura,
  alerta de error y caja de texto con autoajuste.
- **MessageBubble:** usuario a la derecha; asistente a la izquierda con Markdown.
- **Badges:** `RAG`, `Contacto`, `Derivación` (resaltado ámbar) y cantidad de pasos.
- **Responsive:** sidebar fijo en desktop; overlay en mobile.
- **Accesibilidad:** `aria-label`, `role="alert"`, `aria-live`, foco visible y navegación por
  teclado.

### Flujo de estado

- `useChat` mantiene `messages`, `isLoading` y `error`.
- Antes de enviar, construye `history` con los mensajes previos y agrega el mensaje del
  usuario de forma optimista.
- `postChat` envía `{ message, history }`.
- Al responder, agrega el mensaje del asistente con `herramientas` y `pasos`.
- `reset` aborta la petición en curso, limpia mensajes y errores.
- `loadingRef` evita envíos concurrentes aunque el usuario haga doble clic.

### Manejo de errores

- `422`: se muestra el detalle de validación devuelto por FastAPI.
- `503`: mensaje específico sobre Ollama/base documental no disponible.
- Error de red: aviso de conexión con `http://localhost:8000`.
- `AbortError` se ignora (reset o desmontaje).

### Validaciones realizadas

```powershell
docker build -f "%TEMP%\opencode\frontend-build.Dockerfile" -t clinica-frontend-build-test frontend
```

Ese build limpio equivale al escenario real de Fase 3: `npm ci` + `npm run build` dentro de
Node 20, sin reutilizar `node_modules` del host.

Resultado:

- `npm ci`: 182 paquetes, 0 vulnerabilidades.
- `tsc --noEmit`: OK.
- `vite build`: OK.
  - `dist/index.html` 0.64 kB.
  - CSS 35.03 kB (gzip 6.89 kB).
  - JS 410.21 kB (gzip 126.47 kB).
  - 289 módulos transformados.

**Incidencia de build incremental:** al reutilizar `node_modules` montado desde Windows, el
build falló con `EIO` al intentar eliminar binarios nativos de `lightningcss` y con
`node.exe: not found` en `.bin/tsc`. No es un problema del código: el `node_modules` nativo
no es portable entre Windows y el contenedor Linux. Se resolvió validando con un build limpio
en Docker, que es además el flujo definitivo de Fase 3.

**Prueba de servidor de desarrollo:**

```powershell
docker run -d --rm --name clinica-frontend-dev -p 5173:5173 `
  -v "C:/dev/proyecto-clinica-benitez/frontend:/app" `
  -w /app node:20-alpine npm run dev -- --host 0.0.0.0 --port 5173
```

- `GET http://localhost:5173` → HTML de Vite con el título correcto.
- Se validó el render con Chrome headless (`--dump-dom`) y se detectaron:
  “Clínica Benitez”, “Escenarios de prueba”, “Online”, “Nueva conversación”,
  “Consulta RAG”, “Emergencia clínica” y “¿En qué puedo ayudarte?”.
- El estado **Online** confirma que el navegador pudo consultar `GET /health` en
  `http://localhost:8000` con CORS habilitado.
- Contenedor de desarrollo detenido con `docker stop clinica-frontend-dev`.

> El build se validó dentro de `node:20-alpine`; el `Dockerfile` multi-etapa se implementa en
> la Fase 3.

### Ajuste A.1 — Aislamiento de escenarios

**Motivo:** los 5 escenarios son pruebas independientes. Si un escenario hereda el historial
del anterior, el resultado deja de ser válido: por ejemplo, el Escenario 3 (“Quiero saber la
disponibilidad del servicio”) podría responder usando el contexto de un horario previo en
lugar de pedir aclaración.

**Implementación:**

- `useChat.send(text, { fresh: true })`:
  - fuerza `history: []`;
  - reemplaza los mensajes visibles por el nuevo mensaje del usuario;
  - actualiza `messagesRef` de forma sincrónica.
- `App.handleScenario()` llama `send(prompt, { fresh: true })`.
- `Sidebar` no necesitó cambios: sigue emitiendo el prompt y `App` define el modo limpio.

**Porqué:** la interfaz y el contexto enviado al agente deben coincidir. Limpiar solo el
historial pero mantener los mensajes visibles mostraría un contexto que el agente ya no tiene.

**Validación E2E (Playwright + Chrome del sistema):**

1. Clic en “Consulta RAG” → request con `historyLength: 0`, respuesta con horarios reales.
2. Clic en “Consulta ambigua” → request con `historyLength: 0`, respuesta pidiendo
   aclaración, `secondTools: []`.
3. `rawJsonVisible: false`.
4. Único error de consola: `404` de favicon (no funcional).

Resultado: `UI_E2E_OK`.

### Comandos ejecutados

| Fecha | Comando | Resultado |
|-------|---------|-----------|
| 2026-11-13 | `docker compose down` y movimiento a `backend/` | ✅ Monorepo reorganizado. |
| 2026-11-13 | `docker compose up -d --build` | ✅ API healthy; `DOCS: 7`; chat OK. |
| 2026-11-13 | Creación de `frontend/` (React/Vite/TS/Tailwind) | ✅ Estructura y componentes. |
| 2026-11-13 | `npm install && npm run build` en Node 20 | ✅ 179 paquetes; typecheck y build OK. |
| 2026-11-13 | `npm run dev` en Node 20 (puerto 5173) | ✅ HTML servido correctamente. |
| 2026-11-13 | Chrome headless `--dump-dom` | ✅ Render detectado; estado **Online** con CORS. |
| 2026-11-13 | Build limpio `npm ci && npm run build` en Docker | ✅ 182 paquetes; build OK. |
| 2026-11-13 | Playwright E2E: escenarios 1 y 3 | ✅ Ambos `history: []`; el segundo pide aclaración; sin JSON crudo. |

## Fase 3 — Dockerización con Nginx (completada)

### Archivos creados/actualizados

| Archivo | Propósito |
|---------|-----------|
| `frontend/Dockerfile` | Build multi-etapa: `node:20-alpine` → `nginx:alpine`. |
| `frontend/nginx.conf` | Sirve estáticos, fallback SPA, cache de assets y gzip. |
| `frontend/.dockerignore` | Excluye `node_modules`, `dist`, `.env`, documentación y logs del contexto. |
| `docker-compose.yml` | Servicio `frontend` (`5173:80`, `depends_on` con healthcheck). |

### Por qué multi-stage con Nginx y no `npm run dev`

`npm run dev` mantiene el servidor de desarrollo de Vite y un proceso Node.js con
`node_modules` dentro del contenedor. Eso implica:

- imagen y consumo de RAM/CPU innecesarios para servir archivos estáticos;
- proceso de desarrollo con HMR y websockets que no se necesita en producción;
- más superficie de ataque y más recursos compitiendo con Ollama y ChromaDB.

El build multi-etapa compila en `node:20-alpine` y descarta esa etapa. La imagen final solo
contiene `nginx:alpine` y `dist/`, sin Node ni dependencias. En este entorno la imagen final
pesa **94.3 MB** (base `nginx:alpine` 1.31.8); sigue siendo mucho menor que una imagen Node
con `node_modules` y no ejecuta JavaScript en el servidor. Si se prioriza aún más el tamaño,
existe la variante `nginx:alpine-slim`, pero no se aplicó para respetar la indicación de usar
`nginx:alpine`.

### `VITE_API_URL` en build-time

Vite reemplaza `import.meta.env.VITE_*` durante `npm run build`, no en runtime. Por eso el
Dockerfile declara en la etapa de build, antes de compilar:

```dockerfile
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
```

Y Compose pasa el valor como build arg:

```yaml
args:
  VITE_API_URL: ${VITE_API_URL:-http://localhost:8000}
```

Consecuencia: cambiar la URL de la API requiere reconstruir la imagen
(`docker compose up -d --build frontend`); reiniciar el contenedor no alcanza.

### Nginx

- `try_files $uri $uri/ /index.html` permite rutas SPA.
- `/assets/` con cache inmutable de 1 año.
- `gzip` para texto, CSS, JS, JSON, XML y SVG.
- No se configura proxy `/api`: el navegador llama directamente a
  `http://localhost:8000`, que ya tiene CORS para `http://localhost:5173`. Un proxy evitaría
  CORS, pero duplicaría la capa de red y no es el diseño acordado.
- `HEALTHCHECK` con `wget` contra `http://127.0.0.1/` para que Compose muestre `healthy`.

### Un único `docker-compose.yml` en la raíz

Se mantiene un solo archivo en la raíz en lugar de composes separados por carpeta porque:

- permite un ciclo de vida unificado: `docker compose up -d --build`;
- centraliza logs (`docker compose logs -f`), red y variables;
- expresa el orden de arranque con `depends_on`;
- no impide operar un servicio individual (`docker compose up -d api`).

Se usa `depends_on: api: condition: service_healthy` (no la forma corta) para que el
frontend no quede disponible antes de que el healthcheck de la API esté OK.

### Validación end-to-end

| Prueba | Resultado |
|--------|-----------|
| `docker compose config --quiet` | ✅ Sin errores. |
| `docker compose up -d --build` | ✅ Imágenes construidas y servicios iniciados. |
| `docker compose ps` | ✅ API y frontend `Up (healthy)`. |
| `curl -I http://localhost:5173` | ✅ `200`, `Server: nginx/1.31.8`. |
| Navegador (Playwright + Chrome) | ✅ Interfaz cargada desde Nginx. |
| Estado `/health` | ✅ **Online** visible. |
| Consulta RAG | ✅ `POST http://localhost:8000/api/chat`; `buscar_protocolo`; horarios reales. |
| Historial del escenario | ✅ `history: []`. |
| Errores CORS | ✅ Ninguno. |
| Consola del navegador | ✅ Sin errores. |
| Logs Nginx/API | ✅ `OPTIONS /api/chat` 200, `POST /api/chat` 200, healthchecks 200. |
| Tamaño imagen frontend | ✅ 94.3 MB. |

Resultado final: `NGINX_E2E_OK`.

## Fase 4 — Verificación end-to-end y cierre (completada)

- Stack completo levantado desde la raíz.
- Ambos contenedores healthy y verificados por HTTP.
- Interfaz servida por Nginx, estado Online y consulta real contra el agente.
- `README.md` raíz y documentos de `frontend/` actualizados.
- `backend/` mantiene su contrato sin cambios funcionales en esta fase.

## Integración con RAG proactivo (2026-11-16)

El backend pasó a recuperar documentación antes de invocar al modelo y a resolver
seguimientos cortos combinando el turno anterior. El frontend **no necesitó cambios de
código**: el contrato `POST /api/chat` se mantiene igual.

**Qué cambia para la interfaz:**

- Los escenarios del sidebar siguen enviando `history: []`.
- Una consulta corta como “Centro quirúrgico” envía el historial previo y el backend la
  expande para recuperar el contexto.
- El badge `RAG` sigue apareciendo cuando el backend usa fragmentos documentales.
- Los badges `Contacto` y `Derivación` se mantienen para las tools expuestas.
- Las respuestas ya no deben contener nombres de herramientas internas.

**Validación E2E (Playwright + Chrome):**

| Prueba | Resultado |
|--------|-----------|
| 5 escenarios del sidebar | ✅ Respuestas correctas, `history: []` en cada uno. |
| “Horario de atención” | ✅ Pide aclaración. |
| “Centro quirúrgico” después de la aclaración | ✅ `historyLength: 2`; responde 09:00–15:00. |
| Badge RAG en consulta de horario | ✅ `buscar_protocolo` registrado. |
| Badge Derivación en emergencia | ✅ Ticket visible. |
| Nombres internos en la interfaz | ✅ Ninguno. |
| Errores de consola/CORS | ✅ Ninguno. |

Resultado: `UI_PROACTIVE_E2E_OK`.

**Porqué no se tocó el frontend:** el backend resolvió la recuperación y el contexto; la
interfaz ya mostraba `herramientas_usadas` y `pasos`. Mantener el contrato evita romper los
componentes y permite que el beneficio llegue sin migraciones.

## Fase 5 — Chat libre y escenarios separados (2026-11-17)

**Problema:** toda conversación nacía de uno de los 5 escenarios, que reinician el historial.
No existía un lugar para hablar con el agente de forma continua.

**Diseño:**

- `ModeTabs` divide la interfaz en **Conversar con el agente** (modo inicial) y **Escenarios de
  prueba**.
- `App` crea dos instancias de `useChat` (`chat` y `scenarios`) para que cada modo conserve su
  propio historial. Cambiar de pestaña no borra mensajes ni dispara peticiones.
- En el modo de escenarios reaparece el `Sidebar` de 5 casos; en el chat libre se oculta y el
  chat ocupa el ancho completo. El botón de menú del `Header` solo se muestra en escenarios.
- `Sidebar` exporta `SCENARIOS` para que `ModeTabs` muestre la cantidad sin duplicar datos.
- `ChatWindow` acepta `emptyState` (título, descripción, chips y acción opcional) y
  `placeholder`, de modo que cada modo explica qué hacer.
- El chat libre envía historial completo entre turnos; los escenarios mantienen
  `{ fresh: true }` para no mezclar contexto.
- “Nueva conversación” reinicia solo el modo visible.

**Porqué dos instancias y no una:** mantener los historiales aislados evita que una consulta de
prueba contamine la conversación real y permite cambiar de pestaña sin perder trabajo. Como el
contrato `POST /api/chat` no cambia, el backend no se modifica.

**Validación:**

```powershell
cd frontend
npm run typecheck
npm run build
```

Ambos comandos finalizaron sin errores; la imagen Docker se reconstruyó y
`clinica-benitez-frontend` quedó healthy.

