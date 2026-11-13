# Cambios e incidencias — Frontend Clínica Benitez

Registro cronológico de modificaciones importantes, decisiones e incidencias del frontend.

- **Proyecto:** interfaz web del Agente Clínica Benitez.
- **Última actualización:** 2026-11-13.

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

**Incidencia:** ninguna. El aviso de nueva versión de npm no afecta el build.

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

- **Docker del frontend:** `Dockerfile` y servicio `frontend` se agregan en la Fase 3.
- **`VITE_API_URL`:** se resuelve en build; si cambia, hay que reconstruir la imagen.
- **CORS:** cualquier origen nuevo debe agregarse en `backend/app/main.py`.
- **Sin tests automatizados:** la validación actual es typecheck + build + pruebas manuales.
- **Sin autenticación:** fuera del alcance del plan.
- **El estado online depende de Ollama:** `/health` puede responder OK aunque el agente falle
  si Ollama se cae después del chequeo; el error se muestra al enviar una consulta.
