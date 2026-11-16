# Cambios e incidencias — Frontend Clínica Benitez

Registro cronológico de modificaciones importantes, decisiones e incidencias del frontend.

- **Proyecto:** interfaz web del Agente Clínica Benitez.
- **Última actualización:** 2026-11-13.

---

## 2026-11-13 — Fase 3: Docker + Nginx y orquestación raíz

**Cambio:** se agregó la imagen de producción del frontend y el servicio en Compose.

- `frontend/Dockerfile` multi-etapa: `node:20-alpine` (build) → `nginx:alpine` (runtime).
- `frontend/nginx.conf`: estáticos, fallback SPA, cache de `/assets/` y gzip.
- `frontend/.dockerignore` ampliado.
- `docker-compose.yml`: servicio `frontend`, `5173:80`, `VITE_API_URL` como build arg y
  `depends_on` con `condition: service_healthy`.

**Porqué:**

- No se ejecuta `npm run dev` en el contenedor: Node + Vite + `node_modules` consumen
  recursos y no son necesarios para servir estáticos. Nginx entrega `dist/` con bajo consumo.
- `VITE_API_URL` se embebe en build-time; por eso `ARG`/`ENV` están antes de
  `npm run build`. Cambiarla exige reconstruir.
- Un compose raíz unifica ciclo de vida, red, logs y orden de arranque; el healthcheck de la
  API evita publicar el frontend antes de que el backend esté listo.

**Validación:**

- Ambos contenedores `Up (healthy)`.
- `http://localhost:5173` servido por `nginx/1.31.8`, `200`.
- Estado **Online**, `POST http://localhost:8000/api/chat` con `history: []`, respuesta real
  y sin errores CORS.
- Imagen final: 94.3 MB.
- Resultado: `NGINX_E2E_OK`.

**Nota:** el tamaño real es 94.3 MB (base `nginx:alpine` 1.31.8). Si se busca reducirlo, se
puede evaluar `nginx:alpine-slim`; no se aplicó para respetar la indicación de `nginx:alpine`.

---

## 2026-11-13 — Aislamiento de escenarios y build limpio

**Cambio:** cada clic en un escenario del sidebar inicia una conversación limpia.

- `useChat.send(text, { fresh: true })` fuerza `history: []`.
- Se reemplazan los mensajes visibles por el nuevo mensaje del usuario.
- `App.handleScenario()` usa `fresh: true`; `Sidebar` no cambió.

**Porqué:** las pruebas del sidebar deben ser independientes. Sin esto, el Escenario 3
(“disponibilidad del servicio”) podía heredar el tema de una consulta anterior y responder
en vez de pedir aclaración. Limpiar también la vista evita mostrar un contexto que el agente
ya no recibe.

**Validación E2E (Playwright + Chrome):**

- Escenario 1 → `historyLength: 0`, respuesta con horarios reales.
- Escenario 3 → `historyLength: 0`, `secondTools: []`, respuesta pidiendo aclaración.
- `rawJsonVisible: false`.
- Resultado: `UI_E2E_OK`.

**Incidencia de build:** el build incremental con `node_modules` montado desde Windows falló
con `EIO` en binarios nativos de `lightningcss` y `node.exe: not found` en `.bin/tsc`. No es
un error del código: los binarios nativos no son portables entre Windows y Linux. Se validó
con un build limpio `npm ci && npm run build` dentro de Node 20, que es el flujo real de la
Fase 3.

---

## 2026-11-13 — Creación del frontend React + Vite + Tailwind

**Cambio:** se creó la aplicación `frontend/` con:

- React 19 + TypeScript estricto.
- Vite 7 y `@vitejs/plugin-react`.
- Tailwind CSS v4 mediante `@tailwindcss/vite`.
- `react-markdown` + `remark-gfm` para respuestas del agente.
- Componentes: `Header`, `Sidebar`, `ChatWindow`, `MessageBubble`, `TypingIndicator`,
  `StatusIndicator`.
- Hooks: `useHealth` (polling de `/health`) y `useChat` (historial, envío, errores, reset).
- Variables de entorno con `VITE_API_URL`.

**Decisiones:**

- Sin router, sin Redux/Zustand y sin librería de UI.
- Escenarios del sidebar con envío automático y bloqueo mientras `isLoading`.
- Tema oscuro con acentos teal/cyan; badge de derivación resaltado en ámbar.
- Manejo explícito de `422`, `503` y errores de red.

**Validación:**

```powershell
docker run --rm -v "C:/dev/proyecto-clinica-benitez/frontend:/app" -w /app node:20-alpine sh -c "npm install && npm run build"
```

- 179 paquetes instalados, 0 vulnerabilidades.
- `tsc --noEmit` OK.
- `vite build` OK (289 módulos; JS 410 kB / gzip 126 kB).
- Servidor de desarrollo en `5173` OK.
- Render validado con Chrome headless: estado **Online**, escenarios y chat visibles.

**Incidencia:** ninguna en el build inicial. La incidencia de `node_modules` montado desde
Windows se documenta en la sección de aislamiento de escenarios.

---

## 2026-11-13 — Dependencia de CORS en el backend

**Motivo:** el frontend corre en el navegador en `http://localhost:5173` y llama a la API en
`http://localhost:8000`.

**Cambio previo (backend):** `CORSMiddleware` con orígenes `5173` y `3000`, métodos y headers
`*`, sin credenciales.

**Validación:** preflight `OPTIONS /api/chat` con `Origin: http://localhost:5173` → `200` y
`access-control-allow-origin` correcto.

**Impacto:** sin este cambio, el navegador bloquearía `POST /api/chat`.

---

## 2026-11-13 — Reorganización a monorepo

**Cambio:** backend movido a `backend/`; `frontend/` en la raíz; compose raíz actualizado.

**Impacto en frontend:** `VITE_API_URL` sigue apuntando a `http://localhost:8000`; no cambia
el contrato de la API.

---

## Riesgos y pendientes

- **Docker del frontend:** completado con build multi-etapa y Nginx; servicio `frontend` en
  el compose raíz.
- **`VITE_API_URL`:** se resuelve en build; si cambia, hay que reconstruir la imagen.
- **CORS:** cualquier origen nuevo debe agregarse en `backend/app/main.py`.
- **Sin tests automatizados:** la validación actual es typecheck + build + pruebas manuales.
- **Sin autenticación:** fuera del alcance del plan.
- **El estado online depende de Ollama:** `/health` puede responder OK aunque el agente falle
  si Ollama se cae después del chequeo; el error se muestra al enviar una consulta.
