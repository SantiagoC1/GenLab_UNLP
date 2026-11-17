// Proveedores de modelos de lenguaje con plan gratuito. Port de chatbot/app/providers.py.
//
// El cooldown (a qué proveedor saltear un rato) ya no vive en memoria: lo guarda la base, así lo
// comparten todas las instancias de la función. Acá solo se decide a quién llamar y qué hacer si falla.

import type { Config } from "./config.ts";
import type { Document, Turn } from "./knowledge.ts";
import { JSON_REMINDER, REPLY_SCHEMA, buildPrompt, toReply } from "./prompt.ts";
import type { Reply } from "./prompt.ts";

const MAX_OUTPUT_TOKENS = 600;
// Los modelos que razonan (GPT-OSS) gastan parte del cupo pensando antes de responder
const OPENAI_COMPATIBLE_MAX_TOKENS = 1500;
const TEMPERATURE = 0.6;
const MAX_RETRY_AFTER_SECONDS = 600;

export type FailureKind = "quota" | "unavailable" | "invalid";

/** Falla de un proveedor. `kind` decide si se lo saltea un tiempo (cooldown). */
export class ProviderError extends Error {
  provider: string;
  kind: FailureKind;
  retryAfter: number | null;

  constructor(provider: string, kind: FailureKind, detail: string, retryAfter: number | null = null) {
    super(`${provider}: ${kind}: ${detail}`);
    this.provider = provider;
    this.kind = kind;
    this.retryAfter = retryAfter;
  }
}

/** Ningún proveedor de la cadena pudo responder: hay que usar el modo reglas. */
export class NoProviderAvailable extends Error {}

export type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

export interface Provider {
  name: string;
  isConfigured(): boolean;
  generate(question: string, history: readonly Turn[], documents: readonly Document[]): Promise<Reply>;
}

/** Convierte el texto del modelo en un `Reply`. Tolera bloques de código y texto alrededor. */
export function parseReply(provider: string, text: string): Reply {
  let candidate = text.trim();
  const fenced = candidate.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/);
  if (fenced) candidate = fenced[1];
  const attempts = [candidate];
  const start = candidate.indexOf("{");
  const end = candidate.lastIndexOf("}");
  if (start !== -1 && end > start) attempts.push(candidate.slice(start, end + 1));
  for (const attempt of attempts) {
    try {
      const reply = toReply(JSON.parse(attempt));
      if (reply) return reply;
    } catch {
      // probar el siguiente intento
    }
  }
  throw new ProviderError(provider, "invalid", "the answer is not a valid reply");
}

function retryAfter(response: Response): number | null {
  const value = response.headers.get("retry-after") ?? "";
  return /^\d+$/.test(value) ? Math.min(Number(value), MAX_RETRY_AFTER_SECONDS) : null;
}

/** Gemini 2.x apaga el razonamiento con `thinkingBudget`; Gemini 3 en adelante lo rechaza (HTTP 400) y usa `thinkingLevel`. */
export function thinkingConfig(model: string): Record<string, unknown> {
  return model.startsWith("gemini-2") ? { thinkingBudget: 0 } : { thinkingLevel: "LOW" };
}

async function post(
  provider: string,
  fetchFn: FetchFn,
  url: string,
  headers: Record<string, string>,
  body: unknown,
  timeoutSeconds: number,
): Promise<Response> {
  let response: Response;
  try {
    response = await fetchFn(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutSeconds * 1000),
    });
  } catch (error) {
    // timeout, red caída
    throw new ProviderError(provider, "unavailable", error instanceof Error ? error.name : "error");
  }
  if (response.status === 429 || response.status === 402) {
    throw new ProviderError(provider, "quota", `HTTP ${response.status}`, retryAfter(response));
  }
  if (response.status >= 400) {
    throw new ProviderError(provider, "unavailable", `HTTP ${response.status}`);
  }
  return response;
}

/** Gemini con salida estructurada (`responseSchema`). */
export class GeminiProvider implements Provider {
  name = "gemini";
  private apiKey: string;
  private model: string;
  private timeoutSeconds: number;
  private fetchFn: FetchFn;

  constructor(apiKey: string, model: string, timeoutSeconds: number, fetchFn: FetchFn = fetch) {
    this.apiKey = apiKey;
    this.model = model;
    this.timeoutSeconds = timeoutSeconds;
    this.fetchFn = fetchFn;
  }

  isConfigured(): boolean {
    return Boolean(this.apiKey && this.model);
  }

  async generate(question: string, history: readonly Turn[], documents: readonly Document[]) {
    const contents = [...history, { role: "user", content: question }].map((turn) => ({
      role: turn.role === "assistant" ? "model" : "user",
      parts: [{ text: turn.content }],
    }));
    const response = await post(
      this.name,
      this.fetchFn,
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(this.model)}:generateContent`,
      { "x-goog-api-key": this.apiKey },
      {
        systemInstruction: { parts: [{ text: buildPrompt(documents) }] },
        contents,
        generationConfig: {
          responseMimeType: "application/json",
          responseSchema: REPLY_SCHEMA,
          maxOutputTokens: MAX_OUTPUT_TOKENS,
          // Algo de variedad para que las respuestas no salgan calcadas
          temperature: TEMPERATURE,
          // Lo mínimo de "pensar": para esta tarea no hace falta
          thinkingConfig: thinkingConfig(this.model),
        },
      },
      this.timeoutSeconds,
    );
    let text = "";
    try {
      const data = await response.json();
      text = (data.candidates[0].content.parts as { text?: string }[])
        .map((part) => part.text ?? "")
        .join("");
    } catch {
      throw new ProviderError(this.name, "invalid", "unexpected response shape");
    }
    return parseReply(this.name, text);
  }
}

/** Cualquier servicio que acepte el formato de OpenAI (Groq, NVIDIA NIM, OpenRouter). */
export class OpenAICompatibleProvider implements Provider {
  name: string;
  private baseUrl: string;
  private apiKey: string;
  private model: string;
  private timeoutSeconds: number;
  private jsonMode: boolean;
  private fetchFn: FetchFn;

  constructor(
    name: string,
    baseUrl: string,
    apiKey: string,
    model: string,
    timeoutSeconds: number,
    // No todos los servicios aceptan `response_format`: sin él se pide el JSON en el prompt
    jsonMode = true,
    fetchFn: FetchFn = fetch,
  ) {
    this.name = name;
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.model = model;
    this.timeoutSeconds = timeoutSeconds;
    this.jsonMode = jsonMode;
    this.fetchFn = fetchFn;
  }

  isConfigured(): boolean {
    return Boolean(this.apiKey && this.model && this.baseUrl);
  }

  async generate(question: string, history: readonly Turn[], documents: readonly Document[]) {
    const payload: Record<string, unknown> = {
      model: this.model,
      messages: [
        { role: "system", content: `${buildPrompt(documents)}\n\n${JSON_REMINDER}` },
        ...history.map((turn) => ({ role: turn.role, content: turn.content })),
        { role: "user", content: question },
      ],
      temperature: TEMPERATURE,
      max_tokens: OPENAI_COMPATIBLE_MAX_TOKENS,
    };
    if (this.jsonMode) payload.response_format = { type: "json_object" };
    const response = await post(
      this.name,
      this.fetchFn,
      `${this.baseUrl.replace(/\/+$/, "")}/chat/completions`,
      { Authorization: `Bearer ${this.apiKey}` },
      payload,
      this.timeoutSeconds,
    );
    let content = "";
    try {
      content = (await response.json()).choices[0].message.content ?? "";
    } catch {
      throw new ProviderError(this.name, "invalid", "unexpected response shape");
    }
    return parseReply(this.name, content);
  }
}

/** Arma el proveedor con ese nombre, o null si el nombre no se conoce. */
export function buildProvider(name: string, config: Config, fetchFn: FetchFn = fetch): Provider | null {
  const timeout = config.llmTimeoutSeconds;
  if (name === "gemini") {
    return new GeminiProvider(config.gemini.apiKey, config.gemini.model, timeout, fetchFn);
  }
  if (name === "groq") {
    const { baseUrl, apiKey, model } = config.groq;
    return new OpenAICompatibleProvider("groq", baseUrl, apiKey, model, timeout, true, fetchFn);
  }
  if (name === "nvidia") {
    // NIM no documenta `response_format`: el JSON se pide en el prompt
    const { baseUrl, apiKey, model } = config.nvidia;
    return new OpenAICompatibleProvider("nvidia", baseUrl, apiKey, model, timeout, false, fetchFn);
  }
  if (name === "openrouter") {
    const { baseUrl, apiKey, model } = config.openrouter;
    return new OpenAICompatibleProvider("openrouter", baseUrl, apiKey, model, timeout, true, fetchFn);
  }
  return null;
}

/** Los proveedores configurados (con clave), en el orden de CHATBOT_LLM_PROVIDERS. */
export function providerChain(config: Config, fetchFn: FetchFn = fetch): Provider[] {
  const chain: Provider[] = [];
  for (const name of config.llmProviders) {
    const provider = buildProvider(name, config, fetchFn);
    if (provider === null) {
      console.warn(`Unknown provider in CHATBOT_LLM_PROVIDERS: ${name}`);
    } else if (provider.isConfigured() && !chain.some((p) => p.name === provider.name)) {
      chain.push(provider);
    }
  }
  return chain;
}

/** Lo que la cadena necesita de la base: a quién saltear y cómo anotar a uno caído. */
export interface CooldownStore {
  providersDown(): Promise<string[]>;
  markProviderDown(provider: string, seconds: number): Promise<void>;
}

/**
 * Prueba cada proveedor en orden y devuelve la primera respuesta válida.
 *
 * Un proveedor sin cuota o caído se saltea durante el cooldown. Si ninguno responde, levanta
 * `NoProviderAvailable` para que el servicio use el modo reglas.
 */
export async function generateWithFallback(
  providers: readonly Provider[],
  cooldown: CooldownStore,
  cooldownSeconds: number,
  question: string,
  history: readonly Turn[],
  documents: readonly Document[],
): Promise<Reply> {
  const down = new Set(await cooldown.providersDown().catch(() => [] as string[]));
  for (const provider of providers) {
    if (down.has(provider.name)) {
      console.info(`Skipping ${provider.name}: cooling down`);
      continue;
    }
    try {
      const reply = await provider.generate(question, history, documents);
      return { ...reply, provider: provider.name };
    } catch (error) {
      if (error instanceof ProviderError) {
        console.warn(`Provider failed (${error.kind}): ${error.message}`);
        if (error.kind === "quota" || error.kind === "unavailable") {
          await cooldown
            .markProviderDown(provider.name, error.retryAfter ?? cooldownSeconds)
            .catch(() => {});
        }
      } else {
        console.error(`Unexpected failure in provider ${provider.name}`, error);
        await cooldown.markProviderDown(provider.name, cooldownSeconds).catch(() => {});
      }
    }
  }
  throw new NoProviderAvailable("no language model provider could answer");
}
