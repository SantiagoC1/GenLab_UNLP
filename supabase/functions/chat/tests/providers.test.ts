// Tests de los proveedores de IA: forma del pedido, errores y lectura de la respuesta.

import assert from "node:assert/strict";
import test from "node:test";

import { loadConfig } from "../config.ts";
import { buildDocuments } from "../knowledge.ts";
import { KNOWLEDGE } from "../knowledge.generated.ts";
import {
  GeminiProvider,
  NoProviderAvailable,
  OpenAICompatibleProvider,
  ProviderError,
  generateWithFallback,
  parseReply,
  providerChain,
  thinkingConfig,
} from "../providers.ts";
import type { FetchFn } from "../providers.ts";
import { FakeProvider, MemoryStore } from "./helpers.ts";

const documents = buildDocuments(KNOWLEDGE).slice(0, 2);

function fakeFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  const calls: { url: string; init: RequestInit }[] = [];
  const fn: FetchFn = async (url, init) => {
    calls.push({ url, init: init ?? {} });
    return new Response(typeof body === "string" ? body : JSON.stringify(body), { status, headers });
  };
  return { fn, calls };
}

const geminiBody = (text: string) => ({ candidates: [{ content: { parts: [{ text }] } }] });

// --- parseReply -----------------------------------------------------------------------------

test("parseReply lee JSON, bloques de código y texto alrededor", () => {
  const json = '{"tipo":"respuesta","respuesta":"Hola"}';
  assert.deepEqual(parseReply("x", json), { tipo: "respuesta", respuesta: "Hola" });
  assert.equal(parseReply("x", "```json\n" + json + "\n```").respuesta, "Hola");
  assert.equal(parseReply("x", `Acá va: ${json} listo`).respuesta, "Hola");
});

test("parseReply rechaza lo que no tiene el formato", () => {
  for (const bad of ["", "no es json", '{"tipo":"otro","respuesta":"x"}', '{"tipo":"respuesta"}', '{"tipo":"respuesta","respuesta":""}']) {
    assert.throws(() => parseReply("x", bad), (e: unknown) => e instanceof ProviderError && e.kind === "invalid", bad);
  }
});

// --- Gemini ---------------------------------------------------------------------------------

test("Gemini 3 usa thinkingLevel; Gemini 2.x usa thinkingBudget (con el 3 da HTTP 400)", () => {
  assert.deepEqual(thinkingConfig("gemini-3.5-flash-lite"), { thinkingLevel: "LOW" });
  assert.deepEqual(thinkingConfig("gemini-2.5-flash"), { thinkingBudget: 0 });
});

test("Gemini: arma el pedido con la clave en el header, el esquema y el historial", async () => {
  const { fn, calls } = fakeFetch(200, geminiBody('{"tipo":"respuesta","respuesta":"Listo."}'));
  const provider = new GeminiProvider("la-clave", "gemini-3.5-flash-lite", 5, fn);
  const reply = await provider.generate("¿Y cómo se hereda?", [
    { role: "user", content: "¿Qué es Fabry?" },
    { role: "assistant", content: "Es una enfermedad." },
  ], documents);

  assert.equal(reply.respuesta, "Listo.");
  assert.match(calls[0].url, /models\/gemini-3\.5-flash-lite:generateContent$/);
  const headers = calls[0].init.headers as Record<string, string>;
  assert.equal(headers["x-goog-api-key"], "la-clave");
  assert.doesNotMatch(calls[0].url, /la-clave/, "la clave no va en la URL");

  const body = JSON.parse(calls[0].init.body as string);
  assert.deepEqual(body.contents.map((c: { role: string }) => c.role), ["user", "model", "user"]);
  assert.equal(body.generationConfig.responseMimeType, "application/json");
  assert.deepEqual(body.generationConfig.thinkingConfig, { thinkingLevel: "LOW" });
  assert.deepEqual(body.generationConfig.responseSchema.required, ["tipo", "respuesta"]);
  assert.match(body.systemInstruction.parts[0].text, /DOCUMENTOS:/);
});

test("Gemini: 429 es cuota (con su Retry-After) y 400 es no disponible", async () => {
  const quota = new GeminiProvider("k", "m", 5, fakeFetch(429, "{}", { "retry-after": "30" }).fn);
  await assert.rejects(quota.generate("q", [], documents), (e: unknown) => e instanceof ProviderError && e.kind === "quota" && e.retryAfter === 30);

  const bad = new GeminiProvider("k", "m", 5, fakeFetch(400, "{}").fn);
  await assert.rejects(bad.generate("q", [], documents), (e: unknown) => e instanceof ProviderError && e.kind === "unavailable" && /400/.test(e.message));
});

test("Gemini: una red caída o un timeout es no disponible", async () => {
  const fn: FetchFn = async () => {
    throw new TypeError("fetch failed");
  };
  await assert.rejects(new GeminiProvider("k", "m", 5, fn).generate("q", [], documents), (e: unknown) => e instanceof ProviderError && e.kind === "unavailable");
});

test("Gemini: una respuesta con otra forma es inválida", async () => {
  const provider = new GeminiProvider("k", "m", 5, fakeFetch(200, { algo: "distinto" }).fn);
  await assert.rejects(provider.generate("q", [], documents), (e: unknown) => e instanceof ProviderError && e.kind === "invalid");
});

test("Gemini sin clave o sin modelo no está configurado", () => {
  assert.equal(new GeminiProvider("", "m", 5).isConfigured(), false);
  assert.equal(new GeminiProvider("k", "", 5).isConfigured(), false);
  assert.equal(new GeminiProvider("k", "m", 5).isConfigured(), true);
});

// --- Compatibles con OpenAI -----------------------------------------------------------------

test("Groq pide JSON con response_format; NVIDIA lo pide en el prompt", async () => {
  const reply = { choices: [{ message: { content: '{"tipo":"respuesta","respuesta":"ok"}' } }] };
  const groq = fakeFetch(200, reply);
  await new OpenAICompatibleProvider("groq", "https://api.groq.com/openai/v1/", "k", "m", 5, true, groq.fn).generate("q", [], documents);
  assert.equal(groq.calls[0].url, "https://api.groq.com/openai/v1/chat/completions");
  const groqBody = JSON.parse(groq.calls[0].init.body as string);
  assert.deepEqual(groqBody.response_format, { type: "json_object" });
  assert.equal((groq.calls[0].init.headers as Record<string, string>).Authorization, "Bearer k");

  const nvidia = fakeFetch(200, reply);
  await new OpenAICompatibleProvider("nvidia", "https://x/v1", "k", "m", 5, false, nvidia.fn).generate("q", [], documents);
  const nvidiaBody = JSON.parse(nvidia.calls[0].init.body as string);
  assert.equal(nvidiaBody.response_format, undefined);
  assert.match(nvidiaBody.messages[0].content, /objeto JSON/);
});

test("compatibles con OpenAI: 429 es cuota y 500 no disponible", async () => {
  const quota = new OpenAICompatibleProvider("groq", "https://x", "k", "m", 5, true, fakeFetch(429, "{}").fn);
  await assert.rejects(quota.generate("q", [], documents), (e: unknown) => e instanceof ProviderError && e.kind === "quota");
  const down = new OpenAICompatibleProvider("groq", "https://x", "k", "m", 5, true, fakeFetch(500, "{}").fn);
  await assert.rejects(down.generate("q", [], documents), (e: unknown) => e instanceof ProviderError && e.kind === "unavailable");
});

// --- Cadena ---------------------------------------------------------------------------------

test("providerChain respeta el orden, saltea los que no tienen clave y los repetidos", () => {
  const config = loadConfig({
    CHATBOT_LLM_PROVIDERS: "gemini,groq,groq,nvidia,desconocido",
    GEMINI_API_KEY: "k",
    GEMINI_MODEL: "m",
    GROQ_API_KEY: "k",
  });
  assert.deepEqual(providerChain(config).map((p) => p.name), ["gemini", "groq"]);
});

test("generateWithFallback sin ningún proveedor disponible levanta NoProviderAvailable", async () => {
  const store = new MemoryStore();
  const down = new FakeProvider("gemini", new ProviderError("gemini", "quota", "HTTP 429"));
  await assert.rejects(generateWithFallback([down], store, 90, "q", [], documents), NoProviderAvailable);
  await assert.rejects(generateWithFallback([], store, 90, "q", [], documents), NoProviderAvailable);
});
