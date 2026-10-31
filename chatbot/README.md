# Chatbot GenLab

Servicio independiente (FastAPI) que responde a pacientes, en español, sobre estudios genéticos y patologías lisosomales (módulo adicional 8, M11). Otros grupos lo consumen por API.

- Contrato de la API: [`docs/Contrato_API_Chatbot.md`](../docs/Contrato_API_Chatbot.md)
- Guía para los grupos consumidores: [`docs/Guia_consumo_chatbot.md`](../docs/Guia_consumo_chatbot.md)

## Cómo funciona

Cada consulta pasa por estos pasos, en orden:

1. **Reglas** (`app/scope.py`): saludos, agradecimientos y derivaciones obvias al médico (síntomas propios, tratamientos, casos personales) se contestan sin modelo.
2. **Caché** (`app/cache.py`): una pregunta repetida, en el primer mensaje de una conversación, sale de la memoria. Nunca se guardan las consultas con datos tapados ni las derivaciones al médico.
3. **Cadena de proveedores de IA** (`app/providers.py`): se prueban en el orden de `CHATBOT_LLM_PROVIDERS` (por defecto `gemini,groq,nvidia`). Todos tienen plan gratuito.
   - Un proveedor sin clave se saltea solo.
   - Si uno devuelve `429` (o se agota la cuota, o se cae), pasa al siguiente y queda **en cooldown** `CHATBOT_PROVIDER_COOLDOWN_SECONDS` (o lo que diga `Retry-After`). Mientras tanto no se lo vuelve a intentar, así no se espera el timeout en cada consulta.
   - Si un proveedor devuelve un JSON inválido, se pasa al siguiente sin cooldown.
4. **Modo reglas** (`app/main.py`): si ningún proveedor responde, se contesta con la base de conocimiento (`knowledge/`), eligiendo el párrafo que responde la pregunta. El paciente nunca se queda sin respuesta.

Los logs indican quién respondió (`provider`: `gemini`, `groq`, `nvidia`, `cache` o `rules`).

Gemini usa su propio cliente (salida estructurada). Groq, NVIDIA NIM y OpenRouter usan un único cliente genérico compatible con OpenAI, con `httpx`.

## Requisitos

Python 3.12 y Git. Para correrlo con el resto del sistema, Docker Desktop. En Windows no hay `make`: todos los comandos de abajo son de PowerShell.

## Levantar solo el chatbot

Desde la raíz del repo:

```powershell
cd chatbot
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Si PowerShell bloquea el script de activación: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. El venv queda en `chatbot/.venv` (ignorado por git); las próximas veces alcanza con activarlo.

Configuración: copiá `.env.example` a `.env` en la raíz del repo (el servicio lee ese archivo y también `chatbot/.env`) y completá las claves que tengas:

```powershell
cp ..\.env.example ..\.env
```

Sin ninguna clave el chatbot funciona igual, en modo reglas. Levantarlo:

```powershell
uvicorn app.main:app --reload --port 8001
```

- Documentación y pruebas: http://localhost:8001/docs
- Health: http://localhost:8001/health

Probar el chat (PowerShell):

```powershell
curl.exe -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d '{\"mensaje\": \"¿Qué es un exoma clínico?\", \"conversacion_id\": null}'
```

Para apagarlo: `Ctrl+C`.

## Claves gratuitas

| Proveedor | Dónde sacarla | Qué pide | Variable |
|---|---|---|---|
| Gemini | Google AI Studio | Cuenta de Google | `GEMINI_API_KEY` y `GEMINI_MODEL` |
| Groq | console.groq.com | Email | `GROQ_API_KEY` |
| NVIDIA NIM | build.nvidia.com | Email y teléfono | `NVIDIA_API_KEY` |
| OpenRouter (opcional) | openrouter.ai | Email | `OPENROUTER_API_KEY` y `OPENROUTER_MODEL` |

Groq y NVIDIA traen por defecto el modelo `openai/gpt-oss-120b`. Gemini y OpenRouter necesitan que elijas el modelo (para OpenRouter, uno gratuito vigente). Los planes gratuitos cambian sin aviso: revisá los límites en la página de cada proveedor.

## Configuración

Todas son variables de entorno (`.env`). Las que no están en `.env.example` tienen el valor por defecto de la tabla.

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `CHATBOT_LLM_PROVIDERS` | `gemini,groq,nvidia` | Orden de la cadena. Agregar `openrouter` si se usa. |
| `CHATBOT_USE_LLM` | `true` | `false` = nunca usa modelos, solo reglas. |
| `CHATBOT_LLM_TIMEOUT_SECONDS` | `12` | Espera máxima por proveedor. |
| `CHATBOT_PROVIDER_COOLDOWN_SECONDS` | `90` | Cuánto se saltea un proveedor sin cuota o caído. |
| `GROQ_BASE_URL`, `NVIDIA_BASE_URL`, `OPENROUTER_BASE_URL` | URLs oficiales | Cambiar solo si el proveedor las cambia. |
| `CHATBOT_AVAILABLE` | `true` | `false` = `/health` y `/chat` responden `503`. |
| `CHATBOT_API_KEYS` | vacío | Claves de los consumidores, `nombre:clave,nombre:clave`. Vacío = no pide clave. |
| `CHATBOT_RATE_LIMIT` | `20` | Consultas por minuto de cada consumidor. |
| `CONVERSATION_TTL_MINUTES` | `30` | Minutos sin mensajes tras los que se olvida una conversación. |
| `CONVERSATION_MAX_TURNS` | `6` | Intercambios anteriores que se le pasan al modelo. |
| `CHATBOT_CACHE_TTL_MINUTES` | `60` | Vida de una respuesta en la caché. |
| `CHATBOT_CACHE_MAX_ENTRIES` | `500` | Tamaño máximo de la caché. `0` la desactiva. |
| `CHATBOT_PROMPT_MAX_DOCUMENTS` | `12` | Umbral del prompt: ver abajo. |
| `CHATBOT_PROMPT_TOP_DOCUMENTS` | `3` | Cuántos textos se mandan al modelo cuando se pasa el umbral. |
| `CORS_ORIGINS` | `*` | Orígenes permitidos. |

**Umbral del prompt.** Hoy la base tiene 10 textos y se mandan todos al modelo en cada consulta (así resuelve sinónimos y continuaciones). Cuando la base tenga más de `CHATBOT_PROMPT_MAX_DOCUMENTS` textos, se mandan solo los `CHATBOT_PROMPT_TOP_DOCUMENTS` más parecidos a la consulta. Si el buscador no encuentra ninguno, se mandan todos.

## Tests y lint

Con el venv activo, dentro de `chatbot/`:

```powershell
pytest
ruff check . ; ruff format --check .
```

Los tests no usan red: simulan los proveedores.

## Evaluar los modelos

`scripts/evaluate.py` corre una batería fija de preguntas (dentro y fuera de alcance, derivación al médico, sin información, continuación, prompt injection, datos personales) contra cada proveedor y arma una tabla con el tipo esperado, el obtenido, si pasa y la latencia.

```powershell
python -m scripts.evaluate                      # reglas + cada proveedor con clave
python -m scripts.evaluate --provider rules     # solo reglas: no necesita claves
python -m scripts.evaluate --provider groq      # fuerza un proveedor
python -m scripts.evaluate --raw                # le pregunta todo al modelo, sin atajos de reglas ni caché
python -m scripts.evaluate --output informe     # además guarda informe.md e informe.csv
```

Por defecto pasa por el mismo camino que `/chat`. Con `--raw` se ve si el modelo respeta las reglas por sí solo, que es lo que importa para decidir si un proveedor merece estar en la cadena. Entre llamadas a un modelo espera `--delay` segundos (1,5 por defecto) para no pasarse del límite por minuto. El resumen marca "sacar de la cadena" a los proveedores que fallan reglas críticas, y el comando termina con código 1 si falla alguna.

## Con Docker, junto con el resto del sistema

Desde la raíz del repo:

```powershell
cp .env.example .env     # completar SUPABASE_*, SECRET_KEY y las claves del chatbot
docker compose up --build
```

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend (API) | http://localhost:8000/docs |
| Chatbot (API) | http://localhost:8001/docs |

La base de datos es la de Supabase: las tablas se crean ejecutando `supabase/schema.sql` a mano en el SQL Editor. `SECRET_KEY` se genera con `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

```powershell
docker compose up --build -d       # en segundo plano
docker compose up --build chatbot  # solo el chatbot
docker compose logs -f chatbot     # ver logs
docker compose down                # apagar todo
```

Sin Docker, el sistema completo se levanta en tres terminales: el backend con `uvicorn app.main:app --reload --port 8000` desde `backend/` (con `CHATBOT_URL=http://localhost:8001` en el `.env`), el chatbot como arriba, y el frontend con `npm ci` y `npm run dev` desde `frontend/`.

## Base de conocimiento

Los textos están en `knowledge/` (ver `knowledge/README.md` para el formato). Todos están en estado `borrador` hasta que alguien del equipo los revise contra la fuente y la cátedra valide el alcance. Si agregás o sacás un texto, actualizá la cantidad en `tests/test_knowledge.py`.

## Limitaciones conocidas

- Usa **planes gratuitos** de proveedores de IA, sin garantía de disponibilidad ni de cuota. Cuando se agotan todos, responde con reglas y con la base de conocimiento.
- Los proveedores gratuitos **pueden usar los prompts** para mejorar sus productos. `_scrub` tapa mails y números de 6 o más dígitos, pero **no nombres**, y el prompt indica no incluir datos personales.
- Las conversaciones, el límite de consultas, la caché y el cooldown viven en la **memoria de un solo proceso**: se pierden al reiniciar y no escalan a varias instancias ni a varios workers.
- La base de conocimiento está en `borrador`, pendiente de validación de la cátedra.
- Si `CHATBOT_API_KEYS` está vacío no se pide clave: solo para desarrollo, hay que configurarla al desplegar.
- El buscador de las reglas es por palabras: algunas preguntas que la base sí responde pueden dar `sin_informacion` en modo reglas (por ejemplo "¿quién retira la muestra?"). Con modelo se resuelven mejor.
- Pendientes de la cátedra: decisión 8 (qué responder ante síntomas o resultados personales) y P10 (canal).

## Problemas comunes

- **Puerto ocupado:** `Get-NetTCPConnection -LocalPort 8001 -State Listen` muestra el proceso.
- **Responde siempre con el texto de la base:** no hay ninguna clave configurada, `CHATBOT_USE_LLM=false`, o todos los proveedores fallaron. Mirá el log: cada respuesta dice qué proveedor la dio.
- **Un proveedor "no responde" tras un `429`:** es el cooldown. Pasa solo a los `CHATBOT_PROVIDER_COOLDOWN_SECONDS`, o se reinicia el servicio.
- **`503` en `/health` o `/chat`:** `CHATBOT_AVAILABLE=false`.
