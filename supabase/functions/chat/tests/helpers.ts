// Ayudas de los tests: una base en memoria y proveedores simulados. No usan red ni Supabase.

import { loadConfig } from "../config.ts";
import type { Env } from "../config.ts";
import type { Deps } from "../handler.ts";
import { buildDocuments } from "../knowledge.ts";
import type { Turn } from "../knowledge.ts";
import { KNOWLEDGE } from "../knowledge.generated.ts";
import { ProviderError } from "../providers.ts";
import type { Provider } from "../providers.ts";
import type { Kind } from "../scope.ts";
import type { CachedAnswer, Store } from "../store.ts";

export const PUBLISHABLE_KEY = "sb_publishable_test";
export const TOKEN = "token-del-grupo-2";
export const CONSUMER = "grupo-2";

/** Implementación en memoria de `Store`, con las mismas reglas que supabase/chatbot.sql. */
export class MemoryStore implements Store {
  tokens = new Map<string, string>([[TOKEN, CONSUMER]]);
  hits = new Map<string, number>();
  conversations = new Map<string, Turn[]>();
  cache = new Map<string, CachedAnswer>();
  down = new Map<string, number>();
  queries: { consumer: string; kind: Kind; provider: string; question: string; answer: string }[] = [];
  failing = new Set<string>();

  private check(name: string) {
    if (this.failing.has(name)) throw new Error(`${name} failed`);
  }

  async authenticate(token: string) {
    this.check("authenticate");
    return this.tokens.get(token) ?? null;
  }
  async checkRateLimit(consumer: string, limit: number): Promise<number> {
    this.check("checkRateLimit");
    const hits = this.hits.get(consumer) ?? 0;
    if (hits >= limit) return 17;
    this.hits.set(consumer, hits + 1);
    return 0;
  }
  async history(consumer: string, conversationId: string) {
    this.check("history");
    return [...(this.conversations.get(`${consumer}/${conversationId}`) ?? [])];
  }
  async addTurn(consumer: string, conversationId: string, question: string, answer: string, _ttl: number, max: number) {
    this.check("addTurn");
    const key = `${consumer}/${conversationId}`;
    const turns = [...(this.conversations.get(key) ?? []), { role: "user", content: question }, { role: "assistant", content: answer }] as Turn[];
    this.conversations.set(key, turns.slice(-max));
  }
  async cacheGet(key: string) {
    this.check("cacheGet");
    return this.cache.get(key) ?? null;
  }
  async cachePut(key: string, text: string, kind: Kind) {
    this.check("cachePut");
    this.cache.set(key, { text, kind });
  }
  async providersDown() {
    return [...this.down.keys()];
  }
  async markProviderDown(provider: string, seconds: number) {
    this.down.set(provider, seconds);
  }
  async logQuery(consumer: string, _conversationId: string, kind: Kind, provider: string, question: string, answer: string) {
    this.check("logQuery");
    this.queries.push({ consumer, kind, provider, question, answer });
  }
}

/** Proveedor simulado: responde `reply`, o falla con `error`. Cuenta las llamadas. */
export class FakeProvider implements Provider {
  name: string;
  calls: { question: string; history: readonly Turn[]; documents: number }[] = [];
  private outcome: { tipo: Kind; respuesta: string } | ProviderError;

  constructor(name: string, outcome: { tipo: Kind; respuesta: string } | ProviderError) {
    this.name = name;
    this.outcome = outcome;
  }
  isConfigured() {
    return true;
  }
  async generate(question: string, history: readonly Turn[], documents: readonly unknown[]) {
    this.calls.push({ question, history, documents: documents.length });
    if (this.outcome instanceof ProviderError) throw this.outcome;
    return { ...this.outcome };
  }
}

export function makeDeps(overrides: { env?: Env; providers?: Provider[]; store?: MemoryStore } = {}) {
  const store = overrides.store ?? new MemoryStore();
  const deps: Deps = {
    config: loadConfig({ PUBLISHABLE_KEY, ...overrides.env }),
    store,
    providers: overrides.providers ?? [],
    documents: buildDocuments(KNOWLEDGE),
  };
  return { deps, store };
}

/** Pedido a `POST /chat` con las credenciales correctas, salvo que se indique otra cosa. */
export function chatRequest(
  body: unknown,
  headers: Record<string, string | null> = {},
  method = "POST",
): Request {
  const all: Record<string, string | null> = {
    apikey: PUBLISHABLE_KEY,
    "x-chatbot-token": TOKEN,
    "content-type": "application/json",
    ...headers,
  };
  const clean = Object.fromEntries(Object.entries(all).filter(([, v]) => v !== null)) as Record<string, string>;
  return new Request("http://localhost/functions/v1/chat", {
    method,
    headers: clean,
    body: method === "GET" ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
}
