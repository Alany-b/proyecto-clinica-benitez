# Backend — Clínica Benitez

API REST y agente de inteligencia artificial local para consultas administrativas de la
Clínica Benitez. El backend combina **FastAPI**, **LangChain**, **Ollama** y **ChromaDB**,
y se ejecuta dentro de Docker.

El frontend es un servicio separado. Este README explica cómo levantar **solo el backend**
desde la terminal.

---

## Requisitos

- **Docker Desktop** instalado y abierto, con el motor Linux iniciado.
- **Ollama** instalado y abierto en el equipo.
- Espacio libre en disco: aproximadamente 10 GB para los modelos.
- Un navegador web para abrir la documentación de la API.
- Los PDFs institucionales dentro de `backend/data/`.

No hace falta instalar Python ni Node en el equipo: todo el backend corre en contenedores.

---

## Antes de empezar: ubicación correcta

Todos los comandos de este README se ejecutan desde la **raíz del proyecto**, no desde la
carpeta `backend/`, porque el archivo `docker-compose.yml` está en la raíz.

```powershell
cd C:\dev\proyecto-clinica-benitez
```

Para comprobar que estás en el lugar correcto:

```powershell
Get-ChildItem
```

Debe aparecer `docker-compose.yml` junto a las carpetas `backend` y `frontend`.

---

## Levantar el backend paso a paso

### 1. Abrir Docker Desktop y Ollama

Antes de ejecutar cualquier comando:

1. Abrí **Docker Desktop** y esperá a que el motor termine de iniciar.
2. Abrí **Ollama** y verificá que esté funcionando.

Podés comprobar Ollama con:

```powershell
ollama list
```

Si el comando muestra los modelos instalados, Ollama está disponible.

### 2. Descargar los modelos

Solo es necesario la primera vez:

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

- `llama3.1:8b` se usa para generar respuestas y ejecutar herramientas.
- `nomic-embed-text` se usa para generar los embeddings del RAG.

### 3. Compilar el modelo del agente

El archivo `backend/Modelfile` parte de `llama3.1:8b` y contiene el SYSTEM prompt con las
reglas de la clínica:

```powershell
ollama create agente-clinica -f backend/Modelfile
```

Debe finalizar con `success`. Verificar:

```powershell
ollama list
```

Tiene que aparecer `agente-clinica:latest`.

### 4. Verificar los PDFs

Los documentos institucionales deben estar en:

```
backend/data/
```

Con los documentos actuales, la carpeta contiene:

- `Manual de Procedimientos Administrativos.pdf`
- `Protocolo de Servicios y Contactos Internos.pdf`

Sin PDFs no se puede construir el índice de búsqueda.

### 5. Construir y levantar solo el backend

```powershell
docker compose up -d --build api
```

La primera vez puede tardar unos minutos porque descarga la imagen base e instala las
dependencias. Las siguientes ejecuciones son más rápidas.

Verificar que el contenedor esté activo y saludable:

```powershell
docker compose ps
```

Debe aparecer el servicio `api` con estado `Up (healthy)` y el puerto `8000` publicado.

### 6. Indexar los PDFs

La primera vez, o cada vez que agregues o cambies documentos:

```powershell
docker compose run --rm api python -m app.rag.indexer
```

Salida esperada con los dos PDFs actuales:

```
archivos: 2
paginas: 4
fragmentos: 7
coleccion: protocolos_clinica
persistencia: /code/vector_store
```

El índice queda guardado en `backend/vector_store/` y se conserva al reiniciar el
contenedor.

### 7. Abrir la API en el navegador

Con el backend levantado:

- Documentación interactiva: <http://localhost:8000/docs>
- Estado del servicio: <http://localhost:8000/health>

En `/health` deberías ver:

```json
{"status":"ok","service":"clinica-benitez-api"}
```

---

## Levantar también el frontend

Si además querés la interfaz web:

```powershell
docker compose up -d --build
```

Esto levanta `api` y `frontend`. La interfaz queda disponible en:

<http://localhost:5173>

Para levantar únicamente el frontend, con el backend ya iniciado:

```powershell
docker compose up -d frontend
```

---

## Probar la API desde el navegador

No hace falta usar herramientas de línea de comandos para probar la API. La API incluye
Swagger UI en:

<http://localhost:8000/docs>

Pasos:

1. Abrí `http://localhost:8000/docs`.
2. Desplegá `POST /api/chat`.
3. Presioná **Try it out**.
4. Pegá un cuerpo como el siguiente:

```json
{
  "message": "¿Cuál es el horario de Diagnóstico por Imágenes?",
  "history": []
}
```

5. Presioná **Execute**.

La respuesta debe incluir `respuesta`, `herramientas_usadas` y `pasos`.

### Ejemplo con historial

```json
{
  "message": "¿Y los sábados?",
  "history": [
    {
      "role": "user",
      "content": "¿Cuál es el horario de Diagnóstico por Imágenes?"
    },
    {
      "role": "assistant",
      "content": "Lunes a viernes de 07:00 a 20:00 hs."
    }
  ]
}
```

### Consulta de contacto

```json
{
  "message": "¿A qué extensión debo llamar para una derivación administrativa?",
  "history": []
}
```

Debe usar `consultar_contacto_area` y devolver el interno 104.

### Consulta clínica o emergencia

```json
{
  "message": "Me duele el pecho, ¿qué medicamento tomo?",
  "history": []
}
```

Debe:

- no diagnosticar ni recomendar medicamentos;
- indicar guardia o servicio de emergencias;
- usar `derivar_solicitud` y devolver un ticket.

---

## Comandos útiles de terminal

### Ver el estado de los servicios

```powershell
docker compose ps
```

### Ver los logs del backend

```powershell
docker compose logs -f api
```

### Reiniciar el backend

```powershell
docker compose restart api
```

### Reconstruir después de cambiar código

```powershell
docker compose up -d --build api
```

### Detener el backend

```powershell
docker compose down
```

### Reindexar los PDFs

```powershell
docker compose run --rm api python -m app.rag.indexer
```

---

## CORS y desarrollo desde otros orígenes

El backend permite:

- `http://localhost:5173` y `http://localhost:3000`.
- Cualquier origen `http://localhost`, `http://127.0.0.1` o IP privada
  (`10.x.x.x`, `172.16–31.x.x`, `192.168.x.x`) en cualquier puerto, mediante
  `allow_origin_regex`.

Esto permite usar Vite en un puerto alternativo (por ejemplo `5174`) o abrir la interfaz
desde la IP de WSL/LAN sin recibir un error CORS. El backend no usa cookies ni credenciales,
por lo que `allow_credentials` queda en `False`.

> Para producción conviene restringir los orígenes a los dominios reales.

---

## Estructura del backend

```
backend/
├── app/
│   ├── api/
│   │   ├── routes.py        # Endpoint POST /api/chat
│   │   └── schemas.py       # Esquemas de entrada y salida
│   ├── agent/
│   │   ├── core.py          # Modelo, bucle de tools y guardrails
│   │   └── tools.py         # Búsqueda, contactos y derivaciones
│   ├── rag/
│   │   └── indexer.py       # PDFs → chunks → embeddings → Chroma
│   └── main.py              # FastAPI + /health
├── data/                    # PDFs institucionales
├── vector_store/            # Índice persistente de Chroma
├── requirements.txt
├── Dockerfile
├── Modelfile                # agente-clinica (FROM llama3.1:8b)
├── .env.example
├── desarollo.md
├── cambios.md
└── README.md
```

El `docker-compose.yml` y el `README.md` general están en la raíz del proyecto.

---

## Configuración

Para levantar el backend no hace falta tocar ninguna variable: los valores por defecto de
`docker-compose.yml` ya funcionan. Si necesitás cambiarlos, editá el bloque `environment` del
servicio `api` en `docker-compose.yml`.

| Variable | Valor por defecto | Uso |
|----------|-------------------|-----|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | URL de Ollama desde el contenedor. |
| `OLLAMA_CHAT_MODEL` | `agente-clinica` | Modelo de generación y herramientas. |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Modelo de embeddings. |
| `CHROMA_COLLECTION` | `protocolos_clinica` | Colección vectorial. |
| `DATA_DIR` | `/code/data` | PDFs dentro del contenedor. |
| `CHROMA_PERSIST_DIR` | `/code/vector_store` | Persistencia de Chroma. |

Después de cambiar configuración o código:

```powershell
docker compose up -d --build api
```

---

## Qué hace el backend

- **API REST:** `POST /api/chat` y `GET /health`.
- **Agente:** interpreta consultas en español y recibe el contexto documental antes de
  responder; solo invoca herramientas para contacto o derivación.
- **RAG proactivo:** la búsqueda en Chroma se ejecuta automáticamente antes del modelo, por lo
  que una consulta simple no depende de que el modelo genere un JSON perfecto.
- **Contexto multi-turno:** si el mensaje es muy corto (“Centro quirúrgico”, “¿Y los sábados?”)
  se combina con el turno anterior del usuario para recuperar la información correcta.
- **Búsqueda híbrida:** combina similitud vectorial y coincidencia léxica para recuperar
  horarios, contactos, internos y correos.
- **Herramientas expuestas al modelo:**
  - `consultar_contacto_area(area)`: responsable, interno y correo.
  - `derivar_solicitud(motivo, area)`: ticket de derivación simulado.
  - La búsqueda documental (`buscar_protocolo`) es interna y la ejecuta el backend.
- **Guardrails:** no diagnostica, no receta, no inventa contactos ni protocolos, prioriza
  emergencias, genera ticket determinista si corresponde y evita mencionar nombres internos.

---

## Solución de problemas

### Docker no responde

Abrí Docker Desktop y esperá a que el motor inicie. Después verificá:

```powershell
docker compose ps
```

### Ollama no responde

Abrí la aplicación de Ollama y verificá que los modelos estén disponibles:

```powershell
ollama list
```

### Falta el modelo `agente-clinica`

```powershell
ollama create agente-clinica -f backend/Modelfile
```

### La API no encuentra información

- Verificá que los PDFs estén en `backend/data/`.
- Reindexá:

```powershell
docker compose run --rm api python -m app.rag.indexer
```

- Revisá los logs:

```powershell
docker compose logs -f api
```

### La API devuelve error 503

Suele indicar que Ollama no está disponible o que el índice no está construido. Verificá:

```powershell
docker compose ps
ollama list
```

Y volvé a indexar si es necesario.

### El puerto 8000 está ocupado

Cambiá el mapeo en `docker-compose.yml`:

```yaml
ports:
  - "8080:8000"
```

Luego reconstruí:

```powershell
docker compose up -d --build api
```

### La interfaz muestra caracteres raros

La API devuelve UTF-8 correcto. Si PowerShell muestra caracteres extraños, revisá la
respuesta en `/docs` o usá Windows Terminal.

---

## Alcance y límites

- El agente **no diagnostica, no receta y no interpreta estudios**.
- Las derivaciones y los tickets son **simulados**.
- Los contactos provienen de la documentación institucional cargada.
- No incluye autenticación ni TLS; no está listo para producción sin esos controles.
- La calidad de las respuestas depende de los PDFs y del modelo de embeddings.

Para el detalle técnico por fases, ver [`desarollo.md`](desarollo.md).
Para cambios e incidencias, ver [`cambios.md`](cambios.md).
