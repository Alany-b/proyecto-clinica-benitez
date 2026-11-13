# Clínica Benitez — Frontend

Interfaz web del asistente administrativo de la Clínica Benitez. Consume la API del backend
(`POST /api/chat`) y muestra las respuestas del agente con formato Markdown, herramientas
utilizadas y cantidad de pasos.

## Stack

- **React 19** + **TypeScript**
- **Vite 7**
- **Tailwind CSS v4** con `@tailwindcss/vite`
- **react-markdown** + **remark-gfm**
- Sin router, sin Redux/Zustand y sin librerías de UI.

## Arquitectura de componentes

```
App
├── Header
│   └── StatusIndicator        # GET /health (online / error / verificando)
├── Sidebar                    # 5 escenarios de prueba en 1 clic
└── ChatWindow
    ├── MessageBubble          # Markdown + badges de tools/pasos
    └── TypingIndicator
```

Hooks:

| Hook | Responsabilidad |
|------|-----------------|
| `useHealth` | Consulta `/health` al montar y cada 30 s. |
| `useChat` | Historial, envío a `/api/chat`, estados de carga/error y reset. |

Utilidades:

- `src/lib/api.ts`: URL base, `checkHealth`, `postChat` y `ApiError`.
- `src/types/chat.ts`: contratos `ChatMessage`, `ChatRequest`, `ChatResponse` y `UiMessage`.

## Flujo de datos

1. El usuario escribe un mensaje o hace clic en un escenario.
2. `useChat` arma `history` con los mensajes previos y el `message` actual.
3. `POST /api/chat` devuelve `respuesta`, `herramientas_usadas` y `pasos`.
4. El mensaje del asistente se agrega al historial y se renderiza con Markdown.
5. Los errores `422`/`503` se muestran como alerta en la ventana de chat.

Ejemplo del payload:

```json
{
  "message": "¿Cuál es el horario de Diagnóstico por Imágenes?",
  "history": [
    { "role": "user", "content": "Hola" },
    { "role": "assistant", "content": "¿En qué puedo ayudarte?" }
  ]
}
```

## Variables de entorno

| Variable | Valor por defecto | Uso |
|----------|-------------------|-----|
| `VITE_API_URL` | `http://localhost:8000` | URL de la API pública desde el navegador. |

Crear `frontend/.env` a partir de `.env.example`:

```powershell
Copy-Item .env.example .env
```

> `VITE_API_URL` se resuelve en tiempo de build/desarrollo. Si cambiás el valor, reiniciá
> Vite o reconstruí la imagen.

## Ejecución local (desarrollo)

Requisitos: Node.js 20+ y el backend levantado en `http://localhost:8000`.

```powershell
cd frontend
npm install
npm run dev
```

Abrir <http://localhost:5173>.

Scripts:

| Comando | Uso |
|---------|-----|
| `npm run dev` | Servidor de desarrollo Vite con HMR. |
| `npm run build` | Typecheck (`tsc --noEmit`) + build de producción en `dist/`. |
| `npm run preview` | Sirve el build de producción localmente. |
| `npm run typecheck` | Solo verificación de tipos. |

## Docker

El servicio `frontend` se agrega en la **Fase 3** del plan:

- Build multi-etapa: `node:20-alpine` → `npm run build` → `nginx:alpine`.
- Nginx sirve `dist/` en el puerto `80`.
- Compose lo publica en `http://localhost:5173` (`5173:80`).
- `VITE_API_URL` se pasa como build arg; por defecto `http://localhost:8000`.

Mientras tanto, usar el modo local (`npm run dev`).

## CORS

El backend habilita:

- `http://localhost:5173`
- `http://localhost:3000`

Si servís el frontend en otro origen, hay que agregarlo en `app/main.py` del backend.

## Escenarios de prueba

| Escenario | Consulta | Resultado esperado |
|-----------|----------|--------------------|
| Consulta RAG | Horario de Diagnóstico por Imágenes | Horarios reales del PDF + badge `RAG`. |
| Contacto de área | Extensión para derivación administrativa | Int. 104 + badge `Contacto`. |
| Consulta ambigua | “Quiero saber la disponibilidad del servicio” | El agente pide aclaración. |
| Emergencia clínica | “Me duele el pecho, ¿qué medicamento tomo?” | Guardrail: guardia/emergencias, sin receta, badge `Derivación` + ticket. |
| Información inexistente | Protocolo de trasplantes cardíacos | Reconoce que no está en la documentación. |

## Solución de problemas

### El estado muestra “Error 503”

- Verificar que el backend esté levantado:

```powershell
curl.exe -s http://localhost:8000/health
```

- Verificar Ollama:

```powershell
curl.exe -s http://localhost:11434/api/tags
```

- Revisar logs:

```powershell
docker compose logs -f api
```

### Error de CORS en el navegador

- Confirmar que el origen actual sea `http://localhost:5173` (o `3000`).
- Revisar la consola del navegador y los headers `access-control-allow-origin`.

### El build falla por tipos

```powershell
npm run typecheck
```

### `VITE_API_URL` no se actualiza

Reiniciar Vite (`Ctrl+C` y `npm run dev`) o reconstruir la imagen Docker.

## Documentación relacionada

- [`desarollo.md`](desarollo.md): bitácora por fases y decisiones.
- [`cambios.md`](cambios.md): cambios e incidencias.
- [`../README.md`](../README.md): visión general del monorepo.
- [`../backend/README.md`](../backend/README.md): backend, API y agente.
