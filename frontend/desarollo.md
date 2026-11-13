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
| 3 | Dockerización (Node + Nginx) | ⏳ Pendiente |
| 4 | Verificación end-to-end y cierre documental | ⏳ Pendiente |

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
├── index.html
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
docker run --rm -v "C:/dev/proyecto-clinica-benitez/frontend:/app" -w /app node:20-alpine sh -c "npm install && npm run build"
```

Resultado:

- `npm install`: 179 paquetes, 0 vulnerabilidades.
- `tsc --noEmit`: OK.
- `vite build`: OK.
  - `dist/index.html` 0.64 kB.
  - CSS 35.00 kB (gzip 6.88 kB).
  - JS 410.08 kB (gzip 126.40 kB).
  - 289 módulos transformados.

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

### Comandos ejecutados

| Fecha | Comando | Resultado |
|-------|---------|-----------|
| 2026-11-13 | `docker compose down` y movimiento a `backend/` | ✅ Monorepo reorganizado. |
| 2026-11-13 | `docker compose up -d --build` | ✅ API healthy; `DOCS: 7`; chat OK. |
| 2026-11-13 | Creación de `frontend/` (React/Vite/TS/Tailwind) | ✅ Estructura y componentes. |
| 2026-11-13 | `npm install && npm run build` en Node 20 | ✅ 179 paquetes; typecheck y build OK. |
| 2026-11-13 | `npm run dev` en Node 20 (puerto 5173) | ✅ HTML servido correctamente. |
| 2026-11-13 | Chrome headless `--dump-dom` | ✅ Render detectado; estado **Online** con CORS. |

## Fase 3 — Dockerización (pendiente)

Plan:

- `frontend/Dockerfile` multi-etapa con `node:20-alpine` y `nginx:alpine`.
- `nginx.conf` con fallback SPA y cache de assets.
- Servicio `frontend` en `docker-compose.yml` (`5173:80`, `depends_on: api`).
- `VITE_API_URL` como build arg.

## Fase 4 — Verificación end-to-end (pendiente)

- Levantar el stack completo.
- Verificar `http://localhost:5173`, estado `/health` y los 5 escenarios.
- Actualizar `README.md` raíz y cerrar documentación.
