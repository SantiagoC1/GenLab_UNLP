# Contrato de la API del chatbot GenLab

**Versión 2.0 (vigente).** Servicio del módulo adicional 8 (M11 de la especificación), publicado como **Edge Function de Supabase**. Reemplaza a la v1.0 (servicio FastAPI con `X-API-Key`).

Este documento es lo que pueden asumir los grupos que consumen el chatbot. Los campos y valores de abajo no se renombran sin avisar. Para empezar a usarlo, leé la [guía de consumo](Guia_consumo_chatbot.md) y probá los casos de [`chatbot.http`](chatbot.http).

## Qué cambió respecto de la v1.0

| | v1.0 | v2.0 |
|---|---|---|
| Dónde corre | FastAPI propio, puerto 8001 | Edge Function de Supabase |
| URL | `http://<servidor>:8001/chat` | `https://<ref>.supabase.co/functions/v1/chat` |
| Credenciales | `X-API-Key: <clave del grupo>` | `apikey: <clave publishable>` **y** `x-chatbot-token: <token del grupo>` |
| Documentación interactiva | `/docs` (Swagger) | Este contrato y `chatbot.http` |
| Cuerpo y respuesta de `POST /chat` | — | **Sin cambios** (`mensaje`, `conversacion_id`, `respuesta`, `tipo`) |
| Estado (conversaciones, límite, caché) | Memoria de un proceso | Base de datos de Supabase |

Cambió la firma de acceso (URL y credenciales), por eso es una versión mayor. Quien ya consumía la v1.0 solo tiene que cambiar la URL y los headers.

## Resumen

- Una sola función: `https://<ref>.supabase.co/functions/v1/chat`. `POST` consulta; `GET` informa si está disponible.
- Responde **en español** sobre estudios genéticos: exoma clínico, proceso del estudio, patologías lisosomales (Fabry, Pompe, mucopolisacaridosis tipo 1, Gaucher y ASMD) y términos del informe (variante, patogénica, benigna, VUS).
- Responde solo con una **base de conocimiento curada**. Si no tiene información suficiente, lo dice.
- **No** da diagnósticos, no interpreta el resultado de una persona y no habla de tratamientos: sugiere hablar con el médico tratante. No deriva a una persona del laboratorio (indicación del PO).

## Autenticación

Cada pedido a `POST` lleva **dos** headers:

| Header | Qué es | Quién lo conoce |
|---|---|---|
| `apikey` | La clave *publishable* del proyecto de Supabase. | Todos los consumidores (es la clave compartible). |
| `x-chatbot-token` | Token propio del consumidor. Identifica a quién consulta. | Solo ese consumidor. Se guarda en la base como hash. |

| Situación | Resultado |
|---|---|
| Falta `apikey` o no coincide, falta `x-chatbot-token`, o es inválido o está revocado | `401` |
| Todo correcto | Sigue con el pedido |

El token identifica al consumidor: con él se aplican el límite de consultas y la separación de conversaciones. Se pide al grupo que mantiene el chatbot (ver la guía) y se puede revocar o renovar sin afectar a los demás. `GET` (health) no pide credenciales.

## `POST /functions/v1/chat`

Recibe la consulta de un paciente y devuelve la respuesta.

### Pedido

```http
POST https://<ref>.supabase.co/functions/v1/chat
apikey: <clave publishable>
x-chatbot-token: <token del consumidor>
Content-Type: application/json

{
  "mensaje": "¿Qué es un exoma clínico?",
  "conversacion_id": null
}
```

| Campo | Tipo | Obligatorio | Detalle |
|---|---|---|---|
| `mensaje` | texto | sí | De 1 a 1000 caracteres, y no puede ser solo espacios. No incluir datos personales. |
| `conversacion_id` | texto | no | Para seguir una conversación y que el servicio recuerde el contexto. Hasta 200 caracteres. Sin él se abre una conversación nueva. |

### Respuesta `200`

```json
{
  "respuesta": "El exoma es la parte del ADN que tiene las instrucciones para fabricar proteínas...",
  "conversacion_id": "6ba1b3fd-9a65-48d7-8c8c-a805cd6e7239",
  "tipo": "respuesta"
}
```

| Campo | Detalle |
|---|---|
| `respuesta` | Texto para mostrar al paciente tal cual. |
| `conversacion_id` | Identificador de la conversación. Mandalo en el próximo mensaje para mantener el contexto. |
| `tipo` | Cómo se trató la consulta (tabla de abajo). |

### Valores de `tipo`

| Valor | Cuándo | Qué hace la aplicación consumidora |
|---|---|---|
| `respuesta` | La consulta es del tema y hay información. También saludos y agradecimientos. | Mostrar la respuesta. |
| `fuera_de_alcance` | La consulta no es sobre estudios genéticos. El servicio no inventa una respuesta. | Mostrar la respuesta. |
| `derivar_medico` | Pide un diagnóstico, interpretar su resultado, o habla de síntomas propios o de tratamientos. | Mostrar la respuesta. No hay que ofrecer contacto con el laboratorio. |
| `sin_informacion` | Es del tema, pero la base no tiene lo necesario. | Mostrar la respuesta. |

### Errores

| Código | Cuándo | Cuerpo |
|---|---|---|
| `401` | Credenciales faltantes o inválidas | `{"detail": "Clave de API inválida."}` |
| `422` | Pedido inválido: cuerpo que no es JSON, mensaje vacío, solo espacios, de más de 1000 caracteres, falta el campo o tipo incorrecto | `{"detail": [ ... ]}` (abajo). Es el mismo para todos los casos. |
| `429` | Se pasó el límite de consultas del consumidor | `{"detail": "Demasiadas consultas. ..."}` y el header `Retry-After` con los segundos de espera |
| `503` | El servicio está apagado (`CHATBOT_AVAILABLE=false`) | `{"detail": "El chatbot no está disponible por el momento. Intentá de nuevo más tarde."}` |
| `405` | Un método distinto de `GET`, `POST` u `OPTIONS` | `{"detail": "Método no permitido."}` |
| `500` | Falla inesperada del servicio (por ejemplo, la base no responde) | `{"detail": "Error interno del servicio. Intentá de nuevo más tarde."}` |

Formato del `422`:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "mensaje"],
      "msg": "Value error, La consulta no puede estar vacía.",
      "input": "   "
    }
  ]
}
```

Los errores `401`, `405`, `429`, `500` y `503` llevan `detail` como texto. Si falla el modelo de lenguaje, el servicio **no** devuelve error: responde con reglas y con el texto de la base (ver más abajo).

El orden de las verificaciones es: credenciales (`401`), validación del pedido (`422`), servicio disponible (`503`) y límite de consultas (`429`). Un pedido inválido no cuenta para el límite.

## `GET /functions/v1/chat` (health)

Indica si el servicio está disponible. No pide credenciales y no consume cuota de los proveedores de IA.

| Código | Cuerpo |
|---|---|
| `200` | `{"estado": "ok"}` |
| `503` | `{"detail": "El chatbot no está disponible por el momento. Intentá de nuevo más tarde."}` |

## Límites y comportamiento

- **Largo:** 1000 caracteres por mensaje.
- **Consultas:** 20 por minuto por consumidor (configurable con `CHATBOT_RATE_LIMIT`). Se cuenta por minuto calendario: `Retry-After` indica cuánto falta para el siguiente.
- **Conversaciones:** el servicio recuerda los últimos 6 intercambios, durante 30 minutos sin mensajes. Las conversaciones están **separadas por consumidor**: el mismo `conversacion_id` usado por dos consumidores no se mezcla.
- **Datos personales:** el servicio no pide ni guarda datos identificables. Antes de registrar o enviar una consulta a un modelo, tapa mails (`[mail]`) y números de 6 o más dígitos (`[número]`). No tapa nombres.
- **Registro:** se registran consulta y respuesta (sin datos personales), el consumidor, el tipo y quién respondió, para evaluar la calidad.

## Cómo se genera la respuesta

1. Las reglas resuelven solas los saludos, los agradecimientos y las derivaciones obvias al médico (síntomas propios, tratamientos, casos personales).
2. Si no, una consulta ya hecha antes (primer mensaje de una conversación) sale de una caché.
3. Si no, se consulta a modelos de lenguaje gratuitos, en este orden: **Gemini → Groq → NVIDIA NIM → (OpenRouter, opcional)**. El que no tiene clave o agotó su cuota se saltea un tiempo.
4. Si ninguno responde, el servicio responde con **reglas y el texto de la base de conocimiento**, para no dejar al paciente sin respuesta.

El consumidor no necesita saber cuál de estos caminos se usó: el formato de la respuesta es el mismo.

## Compatibilidad

Los campos `mensaje`, `conversacion_id`, `respuesta` y `tipo`, y los valores de `tipo` de la tabla, son parte del contrato y no cambian. Se pueden agregar campos nuevos en las respuestas: ignorá los que no conozcas. Un cambio en la URL, los headers o los campos existentes es una versión nueva de este contrato.

## Pendiente

Estas decisiones dependen de la cátedra y siguen abiertas:

- **Decisión 8:** qué responde el chatbot ante síntomas o resultados personales. Hoy: deriva al médico tratante, sin dar información general sobre la patología.
- **P10:** canal de acceso (plataforma o WhatsApp). Hoy: solo API, consumida desde la plataforma.
- La validación de la cátedra sobre el alcance y los textos de la base de conocimiento, que hoy están como `borrador`.

## Limitaciones conocidas

- Usa **planes gratuitos** de proveedores de IA, sin garantía de disponibilidad. Cuando se agotan, el servicio degrada a reglas y a la base.
- Los proveedores gratuitos **pueden usar lo que se les envía** para mejorar sus productos. Por eso se tapan mails y números largos, pero **no nombres**, y el prompt indica no incluir datos personales. Las aplicaciones consumidoras deberían avisar a los pacientes que no escriban datos personales.
- Está sujeto a los límites del plan gratuito de Supabase (invocaciones, tiempo de ejecución y tamaño de la base). El historial y el registro de consultas se limpian solos, pero conviene revisarlos si el uso crece.
- La base de conocimiento está en estado `borrador`, pendiente de validación.
- El token viaja en un header: tiene que usarse desde un servidor, nunca desde el navegador.
