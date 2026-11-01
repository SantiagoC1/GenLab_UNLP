import type { Config } from "./config.ts";
import { bestFragment, search, selectForPrompt } from "./knowledge.ts";
import type { Document, Turn } from "./knowledge.ts";
import { NoProviderAvailable, generateWithFallback } from "./providers.ts";
import type { Provider } from "./providers.ts";
import {
  COURTESY_MESSAGE,
  GREETING_MESSAGE,
  Kind,
  MESSAGES,
  asksForDiagnosis,
  isAboutGenetics,
  isCourtesy,
  isGreeting,
} from "./scope.ts";
import type { Store } from "./store.ts";
import { normalize } from "./text.ts";

export const MAX_MESSAGE_LENGTH = 1000;
const MAX_CONVERSATION_ID_LENGTH = 200;
const TOKEN_HEADER = "x-chatbot-token";

// Una derivación al médico puede reflejar el caso personal de quien preguntó: no se reutiliza
const CACHEABLE_KINDS: readonly Kind[] = [Kind.ANSWER, Kind.OUT_OF_SCOPE, Kind.NO_INFORMATION];

export interface Deps {
  config: Config;
  store: Store;
  providers: Provider[];
  documents: Document[];
}


function corsHeaders(config: Config): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": config.corsOrigins,
    "Access-Control-Allow-Headers": `apikey, content-type, ${TOKEN_HEADER}`,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Expose-Headers": "retry-after",
  };
}

function json(config: Config, status: number, body: unknown, extra: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders(config), ...extra },
  });
}

function detail(config: Config, status: number, message: string, extra: Record<string, string> = {}) {
  return json(config, status, { detail: message }, extra);
}

const UNAVAILABLE_MESSAGE = "El chatbot no está disponible por el momento. Intentá de nuevo más tarde.";



interface ValidationError {
  type: string;
  loc: (string | number)[];
  msg: string;
  input: unknown;
}

type ParsedRequest =
  | { ok: true; message: string; conversationId: string | null }
  | { ok: false; errors: ValidationError[] };

/** Valida el cuerpo con el mismo formato de errores que devolvía FastAPI (422). */
export function parseRequest(raw: string): ParsedRequest {
  let body: unknown;
  try {
    body = JSON.parse(raw);
  } catch {
    return { ok: false, errors: [{ type: "json_invalid", loc: ["body", 0], msg: "JSON decode error", input: {} }] };
  }
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return {
      ok: false,
      errors: [{ type: "model_attributes_type", loc: ["body"], msg: "Input should be a valid dictionary or object", input: body }],
    };
  }
  const { mensaje, conversacion_id: conversationId } = body as Record<string, unknown>;
  const errors: ValidationError[] = [];

  if (mensaje === undefined) {
    errors.push({ type: "missing", loc: ["body", "mensaje"], msg: "Field required", input: body });
  } else if (typeof mensaje !== "string") {
    errors.push({ type: "string_type", loc: ["body", "mensaje"], msg: "Input should be a valid string", input: mensaje });
  } else if (mensaje.length < 1) {
    errors.push({ type: "string_too_short", loc: ["body", "mensaje"], msg: "String should have at least 1 character", input: mensaje });
  } else if (mensaje.length > MAX_MESSAGE_LENGTH) {
    errors.push({
      type: "string_too_long",
      loc: ["body", "mensaje"],
      msg: `String should have at most ${MAX_MESSAGE_LENGTH} characters`,
      input: mensaje,
    });
  } else if (!mensaje.trim()) {
    errors.push({ type: "value_error", loc: ["body", "mensaje"], msg: "Value error, La consulta no puede estar vacía.", input: mensaje });
  }

  if (conversationId !== undefined && conversationId !== null) {
    if (typeof conversationId !== "string") {
      errors.push({ type: "string_type", loc: ["body", "conversacion_id"], msg: "Input should be a valid string", input: conversationId });
    } else if (conversationId.length > MAX_CONVERSATION_ID_LENGTH) {
      errors.push({
        type: "string_too_long",
        loc: ["body", "conversacion_id"],
        msg: `String should have at most ${MAX_CONVERSATION_ID_LENGTH} characters`,
        input: conversationId,
      });
    }
  }
  if (errors.length) return { ok: false, errors };
  return { ok: true, message: mensaje as string, conversationId: (conversationId as string | null | undefined) ?? null };
}


async function authenticate(req: Request, deps: Deps): Promise<string | null> {
  const { config, store } = deps;
  if (config.authDisabled) return "anonimo";
  if (!config.publishableKey) {
    console.error("PUBLISHABLE_KEY no está configurada: se rechazan todos los pedidos.");
    return null;
  }
  if (req.headers.get("apikey") !== config.publishableKey) return null;
  const token = req.headers.get(TOKEN_HEADER);
  if (!token) return null;
  return await store.authenticate(token);
}

/** Tapa mails y números largos (DNI, teléfonos) antes de guardar la consulta (M11-RF7 y RF10). */
export function scrub(text: string): string {
  return text.replace(/[^\s@]+@[^\s@]+\.[^\s@]+/g, "[mail]").replace(/\d{6,}/g, "[número]");
}

/** Minúsculas, sin tildes ni signos y con los espacios colapsados. */
export function cacheKey(question: string): string {
  return normalize(question).replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
}

/** Respuesta fija a lo que las reglas resuelven del todo: no hace falta gastar cuota del modelo. */
function shortcut(question: string): [string, Kind] | null {
  if (isGreeting(question)) return [GREETING_MESSAGE, Kind.ANSWER];
  if (isCourtesy(question)) return [COURTESY_MESSAGE, Kind.ANSWER];
  if (asksForDiagnosis(question)) return [MESSAGES[Kind.REFER_TO_DOCTOR], Kind.REFER_TO_DOCTOR];
  return null;
}

/** Responde sin modelo: reglas de alcance y la parte del texto de la base que corresponde. */
export function answerWithRules(
  question: string,
  history: readonly Turn[],
  documents: readonly Document[],
): [string, Kind] {
  const fixed = shortcut(question);
  if (fixed) return fixed;

  let matches = search(question, documents);
  const previous = history.filter((t) => t.role === "user").map((t) => t.content);
  if (!matches.length && previous.length) {
    // Una continuación ("¿y cómo se hereda?") se entiende con la consulta anterior
    matches = search(`${previous[previous.length - 1]} ${question}`, documents);
  }
  if (!matches.length) {
    const kind = isAboutGenetics(question) ? Kind.NO_INFORMATION : Kind.OUT_OF_SCOPE;
    return [MESSAGES[kind], kind];
  }
  return [bestFragment(question, matches[0].doc), Kind.ANSWER];
}

/** Ignora el fallo de algo accesorio (caché, registro): el paciente igual recibe su respuesta. */
async function bestEffort(label: string, action: () => Promise<unknown>): Promise<void> {
  try {
    await action();
  } catch (error) {
    console.error(`${label} falló`, error);
  }
}

/**
 * Decide cómo responder la consulta y devuelve [texto, tipo, quién respondió].
 *
 * Primero lo que las reglas resuelven solas (saludos, derivaciones) y caché de consultas
 * repetidas, para no gastar cuota. Después, el modelo, que interpreta y clasifica la consulta.
 * Si no hay modelo o fallan todos los proveedores, se responde con reglas y con el texto de la
 * base, para no dejar al paciente sin respuesta.
 */
async function answer(
  deps: Deps,
  question: string,
  history: Turn[],
  cacheable: boolean,
): Promise<[string, Kind, string]> {
  const { config, store, providers, documents } = deps;

  const fixed = shortcut(question);
  if (fixed) return [...fixed, "rules"];

  // Solo el primer mensaje de una conversación: con historial la respuesta depende del contexto
  const useCache = cacheable && history.length === 0 && config.cacheMaxEntries > 0;
  const key = cacheKey(question);
  if (useCache && key) {
    try {
      const hit = await store.cacheGet(key);
      if (hit) return [hit.text, hit.kind, "cache"];
    } catch (error) {
      console.error("caché falló", error);
    }
  }

  if (config.useLlm && providers.length) {
    const prompt = selectForPrompt(question, history, documents, {
      maxDocuments: config.promptMaxDocuments,
      topDocuments: config.promptTopDocuments,
    });
    try {
      const reply = await generateWithFallback(
        providers,
        store,
        config.providerCooldownSeconds,
        question,
        history,
        prompt,
      );
      const text = reply.respuesta.trim();
      if (useCache && key && CACHEABLE_KINDS.includes(reply.tipo)) {
        await bestEffort("caché", () =>
          store.cachePut(key, text, reply.tipo, config.cacheTtlMinutes, config.cacheMaxEntries),
        );
      }
      return [text, reply.tipo, reply.provider ?? "model"];
    } catch (error) {
      if (error instanceof NoProviderAvailable) {
        console.warn("No language model provider answered; falling back to the rules");
      } else {
        console.error("Falló el modelo de lenguaje", error);
      }
    }
  }
  const [text, kind] = answerWithRules(question, history, documents);
  return [text, kind, "rules"];
}

export async function handleRequest(req: Request, deps: Deps): Promise<Response> {
  const { config, store } = deps;
  try {
    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(config) });
    }

    if (req.method === "GET") {
      return config.available
        ? json(config, 200, { estado: "ok" })
        : detail(config, 503, UNAVAILABLE_MESSAGE);
    }
    if (req.method !== "POST") return detail(config, 405, "Método no permitido.");

    const consumer = await authenticate(req, deps);
    if (consumer === null) return detail(config, 401, "Clave de API inválida.");

    const parsed = parseRequest(await req.text());
    if (!parsed.ok) return json(config, 422, { detail: parsed.errors });

    if (!config.available) return detail(config, 503, UNAVAILABLE_MESSAGE);

    const retryAfter = await store.checkRateLimit(consumer, config.rateLimit);
    if (retryAfter > 0) {
      return detail(config, 429, "Demasiadas consultas. Probá de nuevo en unos segundos.", {
        "Retry-After": String(retryAfter),
      });
    }

    const stripped = parsed.message.trim();
    const question = scrub(stripped);
    const conversationId = parsed.conversationId || crypto.randomUUID();

    const maxMessages = config.conversationMaxTurns * 2;
    let history: Turn[] = [];
    try {
      history = await store.history(consumer, conversationId, config.conversationTtlMinutes, maxMessages);
    } catch (error) {
      console.error("historial falló", error);
    }


    const [text, kind, provider] = await answer(deps, question, history, question === stripped);

    await bestEffort("guardar conversación", () =>
      store.addTurn(consumer, conversationId, question, text, config.conversationTtlMinutes, maxMessages),
    );
    console.log(
      JSON.stringify({
        consumidor: consumer,
        conversacion_id: conversationId,
        tipo: kind,
        provider,
        consulta: question,
        respuesta: scrub(text),
      }),
    );
    await bestEffort("registro", () =>
      store.logQuery(consumer, conversationId, kind, provider, question, scrub(text)),
    );

    return json(config, 200, { respuesta: text, conversacion_id: conversationId, tipo: kind });
  } catch (error) {
    console.error("Error no esperado", error);
    return detail(config, 500, "Error interno del servicio. Intentá de nuevo más tarde.");
  }
}
