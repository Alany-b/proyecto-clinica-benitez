# Cambios e incidencias — Frontend Clínica Benitez

Registro cronológico de modificaciones importantes, decisiones e incidencias del frontend.

- **Proyecto:** interfaz web del Agente Clínica Benitez.
- **Última actualización:** 2026-11-17.

---

## 2026-11-17 — Modo “Conversar con el agente” separado de los escenarios

**Motivo:** el chat solo era accesible dentro de uno de los 5 escenarios de prueba. No había
forma de mantener una conversación libre de varios turnos sin que un escenario reiniciara el
historial.

**Cambio:**

- Se agregó `ModeTabs` con dos modos: **Conversar con el agente** (inicial) y **Escenarios de
  prueba**.
- `App` instancia dos `useChat` independientes: uno para el chat libre y otro para escenarios.
  Cambiar de pestaña no pierde el historial de la otra.
- En el modo de escenarios la barra lateral vuelve a mostrarse; en el chat libre se oculta y el
  chat ocupa todo el ancho. El botón de menú del header solo aparece en escenarios.
- `ChatWindow` recibió `emptyState` y `placeholder` para adaptar el estado vacío de cada modo.
- “Nueva conversación” reinicia solo el modo visible.
- El formulario de chat libre mantiene el historial; los escenarios siguen enviando
  `fresh: true`.

**Porqué:** separar la conversación real del banco de pruebas permite demostrar el asistente
como producto y, a la vez, conservar los 5 casos guiados para la defensa sin mezclar contextos.

**Validación:** `npm run typecheck` y `npm run build` OK; imagen Docker reconstruida y
`clinica-benitez-frontend` healthy.

---

## 2026-11-17 — CORS para desarrollo en `5174` e IP de WSL

**Motivo:** al abrir la interfaz en `http://172.23.48.1:5174`, el navegador bloqueaba
`/health` y `/api/chat` porque el backend solo permitía `localhost:5173` y `3000`.

**Cambio:** el backend acepta ahora `localhost`, `127.0.0.1` e IP privadas en cualquier puerto
mediante `allow_origin_regex`. No se modificó el frontend.

**Validación:** E2E en `http://172.23.48.1:5174` → Online, `POST /api/chat` 200, sin errores
CORS. El origen externo de prueba es rechazado.

---

## 2026-11-16 — Integración con RAG proactivo

**Cambio de backend:** la recuperación documental se ejecuta antes del modelo y los
seguimientos cortos se expanden con el turno anterior. El contrato `POST /api/chat` no cambió.

**Impacto en frontend:** ninguno a nivel de código. Los escenarios siguen enviando
`history: []`; el seguimiento “Horario de atención” → “Centro quirúrgico” envía historial y el
backend lo resuelve. Los badges `RAG`, `Contacto` y `Derivación` siguen funcionando.

**Validación E2E:**

- 5 escenarios correctos, con `history: []`.
- Seguimiento con `historyLength: 2` y respuesta 09:00–15:00.
- Sin nombres de herramientas internas en la interfaz.
- Sin errores de consola ni CORS.
- Resultado: `UI_PROACTIVE_E2E_OK`.

**Porqué no se modificó React:** el backend absorbió la complejidad del RAG proactivo y la
expansión de contexto; el frontend ya consumía `respuesta`, `herramientas_usadas` y `pasos`.

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
