// Tests de `POST /chat` y `GET /health`: contrato, autenticación, límites y cadena de respuesta.

import assert from "node:assert/strict";
import test from "node:test";

import { handleRequest } from "../handler.ts";
import { ProviderError } from "../providers.ts";
import { CONSUMER, FakeProvider, MemoryStore, chatRequest, makeDeps } from "./helpers.ts";

async function ask(deps: ReturnType<typeof makeDeps>["deps"], message: string, extra: object = {}) {
  const response = await handleRequest(chatRequest({ mensaje: message, ...extra }), deps);
  return { status: response.status, body: await response.json(), headers: response.headers };
}

// --- Health ---------------------------------------------------------------------------------

test("GET responde el estado sin pedir credenciales", async () => {
  const { deps } = makeDeps();
  const response = await handleRequest(chatRequest(null, { apikey: null, "x-chatbot-token": null }, "GET"), deps);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { estado: "ok" });
});

test("si el servicio está apagado, health y chat responden 503", async () => {
  const { deps } = makeDeps({ env: { CHATBOT_AVAILABLE: "false" } });
  const health = await handleRequest(chatRequest(null, {}, "GET"), deps);
  assert.equal(health.status, 503);
  assert.match((await health.json()).detail, /no está disponible/);
  const chat = await ask(deps, "Hola");
  assert.equal(chat.status, 503);
});

test("OPTIONS responde el preflight de CORS", async () => {
  const { deps } = makeDeps();
  const response = await handleRequest(chatRequest(null, {}, "OPTIONS"), deps);
  assert.equal(response.status, 204);
  assert.match(response.headers.get("access-control-allow-headers") ?? "", /apikey/);
  assert.match(response.headers.get("access-control-allow-headers") ?? "", /x-chatbot-token/);
});

test("otros métodos dan 405", async () => {
  const { deps } = makeDeps();
  const response = await handleRequest(chatRequest(null, {}, "DELETE"), deps);
  assert.equal(response.status, 405);
});

// --- Autenticación (401) --------------------------------------------------------------------

test("sin apikey, 401", async () => {
  const { deps } = makeDeps();
  const response = await handleRequest(chatRequest({ mensaje: "Hola" }, { apikey: null }), deps);
  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), { detail: "Clave de API inválida." });
});

test("con apikey incorrecta, 401", async () => {
  const { deps } = makeDeps();
  const response = await handleRequest(chatRequest({ mensaje: "Hola" }, { apikey: "otra" }), deps);
  assert.equal(response.status, 401);
});

test("sin token del consumidor, 401", async () => {
  const { deps } = makeDeps();
  const response = await handleRequest(chatRequest({ mensaje: "Hola" }, { "x-chatbot-token": null }), deps);
  assert.equal(response.status, 401);
});

test("con un token que no existe o está revocado, 401", async () => {
  const { deps } = makeDeps();
  const response = await handleRequest(chatRequest({ mensaje: "Hola" }, { "x-chatbot-token": "inventado" }), deps);
  assert.equal(response.status, 401);
});

test("si no hay PUBLISHABLE_KEY configurada se rechaza todo (no queda abierto)", async () => {
  const { deps } = makeDeps({ env: { PUBLISHABLE_KEY: "" } });
  const response = await handleRequest(chatRequest({ mensaje: "Hola" }), deps);
  assert.equal(response.status, 401);
});

test("CHATBOT_AUTH_DISABLED=true deja pasar sin credenciales (solo desarrollo)", async () => {
  const { deps } = makeDeps({ env: { CHATBOT_AUTH_DISABLED: "true" } });
  const response = await handleRequest(chatRequest({ mensaje: "Hola" }, { apikey: null, "x-chatbot-token": null }), deps);
  assert.equal(response.status, 200);
});

// --- Validación (422) -----------------------------------------------------------------------

test("mensaje inválido: 422 con el formato de errores de siempre", async () => {
  const { deps } = makeDeps();
  const cases: [unknown, string][] = [
    [{}, "missing"],
    [{ mensaje: "" }, "string_too_short"],
    [{ mensaje: "   " }, "value_error"],
    [{ mensaje: "a".repeat(1001) }, "string_too_long"],
    [{ mensaje: 42 }, "string_type"],
    [{ mensaje: null }, "string_type"],
    [{ mensaje: "Hola", conversacion_id: 7 }, "string_type"],
  ];
  for (const [body, type] of cases) {
    const response = await handleRequest(chatRequest(body), deps);
    assert.equal(response.status, 422, JSON.stringify(body).slice(0, 40));
    const { detail } = await response.json();
    assert.equal(detail[0].type, type);
    assert.equal(detail[0].loc[0], "body");
  }
});

test("el mensaje en blanco explica el motivo", async () => {
  const { deps } = makeDeps();
  const { body } = await ask(deps, "   ");
  assert.equal(body.detail[0].msg, "Value error, La consulta no puede estar vacía.");
});

test("1 y 1000 caracteres son válidos; 1001 no", async () => {
  const { deps } = makeDeps();
  assert.equal((await ask(deps, "a")).status, 200);
  assert.equal((await ask(deps, "a".repeat(1000))).status, 200);
  assert.equal((await ask(deps, "a".repeat(1001))).status, 422);
});

test("un cuerpo que no es JSON da 422", async () => {
  const { deps } = makeDeps();
  const response = await handleRequest(chatRequest("esto no es json"), deps);
  assert.equal(response.status, 422);
  assert.equal((await response.json()).detail[0].type, "json_invalid");
});

test("el orden es 401, 422, 503, 429: un pedido inválido no cuenta para el límite", async () => {
  const { deps, store } = makeDeps({ env: { CHATBOT_RATE_LIMIT: "1" } });
  assert.equal((await handleRequest(chatRequest({ mensaje: "" }, { apikey: null }), deps)).status, 401);
  assert.equal((await ask(deps, "")).status, 422);
  assert.equal(store.hits.get(CONSUMER) ?? 0, 0);
  assert.equal((await ask(deps, "Hola")).status, 200);
  assert.equal((await ask(deps, "Hola")).status, 429);
});

// --- Límite de consultas (429) --------------------------------------------------------------

test("al pasar el límite, 429 con Retry-After", async () => {
  const { deps } = makeDeps({ env: { CHATBOT_RATE_LIMIT: "2" } });
  await ask(deps, "Hola");
  await ask(deps, "Hola");
  const { status, body, headers } = await ask(deps, "Hola");
  assert.equal(status, 429);
  assert.match(body.detail, /Demasiadas consultas/);
  assert.equal(headers.get("retry-after"), "17");
});

// --- Respuestas -----------------------------------------------------------------------------

test("modo reglas: responde con la base de conocimiento", async () => {
  const { deps } = makeDeps();
  const { status, body } = await ask(deps, "¿Qué es un exoma clínico?");
  assert.equal(status, 200);
  assert.equal(body.tipo, "respuesta");
  assert.match(body.respuesta.toLowerCase(), /exoma/);
  assert.ok(body.conversacion_id);
});

test("modo reglas: las etapas del estudio salen con su lista numerada", async () => {
  const { deps } = makeDeps();
  const { body } = await ask(deps, "¿Cómo son las etapas de un estudio?");
  assert.equal(body.tipo, "respuesta");
  assert.match(body.respuesta, /estas etapas:\n\n1\. Tu médico pide el estudio/);
  assert.match(body.respuesta, /6\. Cuando el resultado está disponible/);
});

test("saludo, cortesía, fuera de alcance, derivación y sin información", async () => {
  const { deps } = makeDeps();
  assert.match((await ask(deps, "Hola")).body.respuesta, /asistente/i);
  assert.match((await ask(deps, "gracias")).body.respuesta, /De nada/);
  assert.equal((await ask(deps, "¿Cómo va a estar el clima mañana?")).body.tipo, "fuera_de_alcance");
  const referral = (await ask(deps, "¿Qué medicamento me recomiendas?")).body;
  assert.equal(referral.tipo, "derivar_medico");
  assert.match(referral.respuesta, /médico tratante/);
  assert.doesNotMatch(referral.respuesta.toLowerCase(), /laboratorio/);
  assert.equal((await ask(deps, "¿Qué es la enfermedad de Danon?")).body.tipo, "sin_informacion");
});

test("una derivación al médico no gasta cuota del modelo", async () => {
  const provider = new FakeProvider("gemini", { tipo: "respuesta", respuesta: "no debería usarse" });
  const { deps } = makeDeps({ providers: [provider] });
  await ask(deps, "Tengo Fabry, ¿qué hago?");
  await ask(deps, "Hola");
  assert.equal(provider.calls.length, 0);
});

test("con modelo: usa la respuesta y el tipo que devuelve", async () => {
  const provider = new FakeProvider("gemini", { tipo: "respuesta", respuesta: "  El exoma es la parte del ADN que codifica proteínas.  " });
  const { deps, store } = makeDeps({ providers: [provider] });
  const { body } = await ask(deps, "¿Qué es el exoma?");
  assert.equal(body.respuesta, "El exoma es la parte del ADN que codifica proteínas.");
  assert.equal(body.tipo, "respuesta");
  assert.equal(store.queries[0].provider, "gemini");
  // La base chica va completa al modelo
  assert.equal(provider.calls[0].documents, 10);
});

test("CHATBOT_USE_LLM=false no llama a ningún modelo", async () => {
  const provider = new FakeProvider("gemini", { tipo: "respuesta", respuesta: "x" });
  const { deps } = makeDeps({ providers: [provider], env: { CHATBOT_USE_LLM: "false" } });
  await ask(deps, "¿Qué es el exoma?");
  assert.equal(provider.calls.length, 0);
});

// --- Cadena de proveedores y cooldown -------------------------------------------------------

test("si el primero se queda sin cuota, responde el siguiente y el primero queda en cooldown", async () => {
  const gemini = new FakeProvider("gemini", new ProviderError("gemini", "quota", "HTTP 429", 120));
  const groq = new FakeProvider("groq", { tipo: "respuesta", respuesta: "Respuesta de Groq." });
  const { deps, store } = makeDeps({ providers: [gemini, groq] });

  assert.equal((await ask(deps, "¿Qué es el exoma?")).body.respuesta, "Respuesta de Groq.");
  assert.equal(store.down.get("gemini"), 120, "usa el Retry-After del proveedor");

  await ask(deps, "¿Qué es Pompe?");
  assert.equal(gemini.calls.length, 1, "en cooldown no se vuelve a intentar");
  assert.equal(groq.calls.length, 2);
});

test("un JSON inválido pasa al siguiente sin cooldown", async () => {
  const gemini = new FakeProvider("gemini", new ProviderError("gemini", "invalid", "x"));
  const groq = new FakeProvider("groq", { tipo: "respuesta", respuesta: "Groq." });
  const { deps, store } = makeDeps({ providers: [gemini, groq] });
  await ask(deps, "¿Qué es el exoma?");
  assert.equal(store.down.size, 0);
});

test("sin cuota ni respuesta de ninguno, cae al modo reglas y el paciente igual recibe respuesta", async () => {
  const gemini = new FakeProvider("gemini", new ProviderError("gemini", "unavailable", "HTTP 400"));
  const { deps, store } = makeDeps({ providers: [gemini] });
  const { status, body } = await ask(deps, "¿Qué es un exoma clínico?");
  assert.equal(status, 200);
  assert.match(body.respuesta.toLowerCase(), /exoma/);
  assert.equal(store.queries[0].provider, "rules");
  assert.equal(store.down.get("gemini"), 90, "cooldown por defecto");
});

// --- Caché ----------------------------------------------------------------------------------

test("una consulta repetida en el primer mensaje sale de la caché", async () => {
  const provider = new FakeProvider("gemini", { tipo: "respuesta", respuesta: "Sobre el exoma." });
  const { deps, store } = makeDeps({ providers: [provider] });
  await ask(deps, "¿Qué es el exoma?");
  const second = await ask(deps, "que es el EXOMA");
  assert.equal(second.body.respuesta, "Sobre el exoma.");
  assert.equal(provider.calls.length, 1);
  assert.equal(store.queries[1].provider, "cache");
});

test("no se cachea una derivación al médico del modelo ni una consulta con datos tapados", async () => {
  const provider = new FakeProvider("gemini", { tipo: "derivar_medico", respuesta: "Hablalo con tu médico tratante." });
  const { deps, store } = makeDeps({ providers: [provider] });
  await ask(deps, "algo raro sobre mi caso y el exoma");
  assert.equal(store.cache.size, 0);

  const ok = new FakeProvider("gemini", { tipo: "respuesta", respuesta: "Exoma." });
  const second = makeDeps({ providers: [ok] });
  await ask(second.deps, "Mi mail es ana@correo.com, ¿qué es un exoma?");
  assert.equal(second.store.cache.size, 0);
});

test("con historial no se usa la caché", async () => {
  const provider = new FakeProvider("gemini", { tipo: "respuesta", respuesta: "R." });
  const { deps } = makeDeps({ providers: [provider] });
  const first = await ask(deps, "¿Qué es Fabry?");
  await ask(deps, "¿Qué es Fabry?", { conversacion_id: first.body.conversacion_id });
  assert.equal(provider.calls.length, 2);
});

// --- Conversaciones -------------------------------------------------------------------------

test("recuerda la conversación: la continuación se entiende con la consulta anterior", async () => {
  const { deps } = makeDeps();
  const first = await ask(deps, "¿Qué es la enfermedad de Fabry?");
  const second = await ask(deps, "¿y cómo se hereda?", { conversacion_id: first.body.conversacion_id });
  assert.equal(second.body.conversacion_id, first.body.conversacion_id);
  assert.equal(second.body.tipo, "respuesta");
  assert.match(second.body.respuesta, /cromosoma X/i);
});

test("al modelo se le pasa el historial, y solo los últimos mensajes", async () => {
  const provider = new FakeProvider("gemini", { tipo: "respuesta", respuesta: "R." });
  const { deps } = makeDeps({ providers: [provider], env: { CONVERSATION_MAX_TURNS: "1" } });
  const id = (await ask(deps, "primera")).body.conversacion_id;
  await ask(deps, "segunda", { conversacion_id: id });
  await ask(deps, "tercera", { conversacion_id: id });
  assert.deepEqual(provider.calls[2].history.map((t) => t.content), ["segunda", "R."]);
});

test("las conversaciones están separadas por consumidor", async () => {
  const store = new MemoryStore();
  store.tokens.set("token-otro", "grupo-5");
  const { deps } = makeDeps({ store });
  const first = await ask(deps, "¿Qué es la enfermedad de Fabry?");
  const response = await handleRequest(
    chatRequest(
      { mensaje: "¿y cómo se hereda?", conversacion_id: first.body.conversacion_id },
      { "x-chatbot-token": "token-otro" },
    ),
    deps,
  );
  // Sin historial propio, la continuación sola no tiene de qué hablar
  assert.notEqual((await response.json()).tipo, "respuesta");
});

// --- Datos personales -----------------------------------------------------------------------

test("tapa mails y números largos antes de guardar y de mandar al modelo", async () => {
  const provider = new FakeProvider("gemini", { tipo: "respuesta", respuesta: "Tu DNI 12345678 y ana@correo.com" });
  const { deps, store } = makeDeps({ providers: [provider] });
  await ask(deps, "Mi mail es ana@correo.com y mi DNI 12345678, ¿qué es un exoma?");
  assert.match(provider.calls[0].question, /\[mail\]/);
  assert.match(provider.calls[0].question, /\[número\]/);
  assert.doesNotMatch(provider.calls[0].question, /ana@|12345678/);
  assert.doesNotMatch(store.queries[0].question + store.queries[0].answer, /ana@|12345678/);
});

// --- Robustez -------------------------------------------------------------------------------

test("si fallan la caché, el historial o el registro, el paciente igual recibe su respuesta", async () => {
  const store = new MemoryStore();
  store.failing = new Set(["cacheGet", "cachePut", "history", "addTurn", "logQuery"]);
  const provider = new FakeProvider("gemini", { tipo: "respuesta", respuesta: "Igual respondo." });
  const { deps } = makeDeps({ store, providers: [provider] });
  const { status, body } = await ask(deps, "¿Qué es el exoma?");
  assert.equal(status, 200);
  assert.equal(body.respuesta, "Igual respondo.");
});

test("si falla la autenticación contra la base, 500 y no se deja pasar", async () => {
  const store = new MemoryStore();
  store.failing = new Set(["authenticate"]);
  const { deps } = makeDeps({ store });
  const { status, body } = await ask(deps, "Hola");
  assert.equal(status, 500);
  assert.match(body.detail, /Error interno/);
});
