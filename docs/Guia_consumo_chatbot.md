# Guía para consumir el chatbot de GenLab

Para los grupos que quieren usar el chatbot en su aplicación (módulo adicional 8). El detalle de cada campo y error está en el [contrato de la API](Contrato_API_Chatbot.md).

## 1. Pedir una clave

Cada grupo usa su propia clave en el encabezado `X-API-Key`. Pedísela al grupo que mantiene el chatbot, indicando el nombre de tu grupo. Te dan una clave y la URL del servicio.

- La clave es secreta: no la subas al repositorio ni la pongas en código que corra en el navegador.
- Si la perdés o se filtra, pedí una nueva.
- En desarrollo local, el servicio puede estar sin claves configuradas. En ese caso no hace falta el encabezado.

## 2. Hacer una consulta

`POST {URL}/chat` con un JSON que tiene el `mensaje` y, si seguís una conversación, el `conversacion_id` que te devolvió el servicio.

### Con curl

En macOS, Linux o Git Bash:

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu-clave" \
  -d '{"mensaje": "¿Qué es un exoma clínico?", "conversacion_id": null}'
```

En PowerShell (usá `curl.exe`, porque `curl` es otro comando):

```powershell
curl.exe -X POST http://localhost:8001/chat -H "Content-Type: application/json" -H "X-API-Key: tu-clave" -d '{\"mensaje\": \"¿Qué es un exoma clínico?\", \"conversacion_id\": null}'
```

Respuesta:

```json
{
  "respuesta": "El exoma es la parte del ADN que tiene las instrucciones para fabricar proteínas...",
  "conversacion_id": "6ba1b3fd-9a65-48d7-8c8c-a805cd6e7239",
  "tipo": "respuesta"
}
```

### Con fetch (desde tu servidor)

```js
const CHATBOT_URL = process.env.CHATBOT_URL;
const CHATBOT_API_KEY = process.env.CHATBOT_API_KEY;

async function askChatbot(message, conversationId = null) {
  const response = await fetch(`${CHATBOT_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": CHATBOT_API_KEY },
    body: JSON.stringify({ mensaje: message, conversacion_id: conversationId }),
  });

  if (response.status === 429) {
    const seconds = Number(response.headers.get("Retry-After")) || 5;
    throw Object.assign(new Error("Demasiadas consultas"), { retryAfter: seconds });
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw Object.assign(new Error("Chatbot no disponible"), {
      status: response.status,
      detail: body.detail,
    });
  }
  return response.json(); // { respuesta, conversacion_id, tipo }
}
```

## 3. Mantener la conversación

Guardá el `conversacion_id` de la primera respuesta y mandalo en los mensajes siguientes. Así el servicio entiende preguntas como "¿y cómo se hereda?". La conversación se olvida a los 30 minutos sin mensajes, y es solo tuya: otro consumidor no puede verla aunque use el mismo identificador.

## 4. Qué hacer con cada resultado

| Resultado | Qué hacer |
|---|---|
| `200` y cualquier `tipo` | Mostrar `respuesta` tal cual. Los tipos `fuera_de_alcance`, `derivar_medico` y `sin_informacion` también son respuestas válidas para el paciente. |
| `429` | Esperar los segundos del encabezado `Retry-After` y reintentar una sola vez. Si sigue, mostrar un mensaje de "probá de nuevo en unos segundos". |
| `503` | El chatbot está apagado. Mostrar el mensaje de `detail` tal cual (por ejemplo, "El chatbot no está disponible por el momento") y no reintentar en bucle. |
| `401` | La clave es incorrecta o falta. Es un error de configuración tuya: avisá al equipo, no al paciente. |
| `422` | El mensaje es inválido (vacío, solo espacios o de más de 1000 caracteres). Validalo en tu pantalla antes de enviarlo. |

Un `tipo: "derivar_medico"` significa que la consulta pedía un diagnóstico, interpretar un resultado propio o un tratamiento. El chatbot sugiere hablar con el médico tratante. **No ofrezcas contacto con el laboratorio como alternativa**: por indicación del PO, el chatbot no deriva a una persona.

## 5. Recomendaciones

- **Llamá siempre desde un servidor**, no desde el navegador. Si lo llamás desde el navegador, la clave queda a la vista de cualquiera.
- **No mandes datos personales.** Ni nombre, ni DNI, ni mail, ni teléfono, ni resultados de un paciente. El servicio tapa mails y números largos, pero **no nombres**, y los proveedores de IA gratuitos pueden usar lo que reciben. Avisá en tu pantalla que no escriban datos personales.
- **Limitá el largo** del mensaje a 1000 caracteres en tu formulario.
- **Respetá el límite**: 20 consultas por minuto por consumidor. No hagas consultas automáticas en bucle ni de prueba de carga contra el servicio compartido.
- **Mostrá que es un asistente automático** y que no reemplaza a un médico.
- Podés llamar a `GET /health` para saber si está disponible. No consume cuota de los modelos.

## 6. Limitaciones conocidas

- El chatbot usa **modelos de IA gratuitos**, que pueden agotar su cuota o caerse. Cuando pasa, el servicio responde con reglas y con el texto de su base de conocimiento: las respuestas son más literales, pero siguen respetando el alcance.
- Responde **solo** sobre estudios genéticos y patologías lisosomales. Lo demás da `fuera_de_alcance`.
- La base de conocimiento es corta y está en estado `borrador`, pendiente de validación de la cátedra. Preguntas sobre plazos, precios o trámites van a dar `sin_informacion`.
- Las conversaciones y los límites viven en la memoria de **una sola instancia**: se pierden si el servicio se reinicia.
- Si el servicio se despliega sin claves configuradas, no pide `X-API-Key`. Eso es solo para desarrollo.

## 7. Dudas

Escribile al grupo que mantiene el chatbot. La documentación interactiva de la API está en `{URL}/docs`.
