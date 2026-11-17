// Acceso a la base: llama a las funciones `chatbot_*` de supabase/chatbot.sql por la API REST de
// Supabase (PostgREST), con la service role. No usa librerías: solo fetch.

import type { Turn } from "./knowledge.ts";
import type { Kind } from "./scope.ts";
import type { CooldownStore, FetchFn } from "./providers.ts";

export interface CachedAnswer {
  text: string;
  kind: Kind;
}

export interface Store extends CooldownStore {
  /** Id del consumidor dueño del token, o null si es inválido o está revocado. */
  authenticate(token: string): Promise<string | null>;
  /** 0 si puede consultar; si no, los segundos que faltan para el próximo minuto. */
  checkRateLimit(consumer: string, limit: number): Promise<number>;
  history(consumer: string, conversationId: string, ttlMinutes: number, maxMessages: number): Promise<Turn[]>;
  addTurn(
    consumer: string,
    conversationId: string,
    question: string,
    answer: string,
    ttlMinutes: number,
    maxMessages: number,
  ): Promise<void>;
  cacheGet(key: string): Promise<CachedAnswer | null>;
  cachePut(key: string, text: string, kind: Kind, ttlMinutes: number, maxEntries: number): Promise<void>;
  logQuery(
    consumer: string,
    conversationId: string,
    kind: Kind,
    provider: string,
    question: string,
    answer: string,
  ): Promise<void>;
}

export function createStore(url: string, serviceKey: string, fetchFn: FetchFn = fetch): Store {
  const base = url.replace(/\/+$/, "");
  // Las claves nuevas (sb_secret_...) no son un JWT: van solo en `apikey`
  const headers: Record<string, string> = { "Content-Type": "application/json", apikey: serviceKey };
  if (!serviceKey.startsWith("sb_")) headers.Authorization = `Bearer ${serviceKey}`;

  async function rpc<T>(name: string, args: Record<string, unknown> = {}): Promise<T> {
    const response = await fetchFn(`${base}/rest/v1/rpc/${name}`, {
      method: "POST",
      headers,
      body: JSON.stringify(args),
    });
    if (!response.ok) {
      throw new Error(`rpc ${name} failed: HTTP ${response.status}`);
    }
    const text = await response.text();
    return (text ? JSON.parse(text) : null) as T;
  }

  return {
    async authenticate(token) {
      return (await rpc<string | null>("chatbot_authenticate", { p_token: token })) ?? null;
    },
    async checkRateLimit(consumer, limit) {
      return Number(await rpc<number>("chatbot_check_rate_limit", { p_consumer: consumer, p_limit: limit }));
    },
    async history(consumer, conversationId, ttlMinutes, maxMessages) {
      const rows = await rpc<Turn[]>("chatbot_get_history", {
        p_consumer: consumer,
        p_conversation: conversationId,
        p_ttl_minutes: ttlMinutes,
        p_max_messages: maxMessages,
      });
      return (rows ?? []).map((row) => ({ role: row.role, content: row.content }));
    },
    async addTurn(consumer, conversationId, question, answer, ttlMinutes, maxMessages) {
      await rpc("chatbot_add_turn", {
        p_consumer: consumer,
        p_conversation: conversationId,
        p_question: question,
        p_answer: answer,
        p_ttl_minutes: ttlMinutes,
        p_max_messages: maxMessages,
      });
    },
    async cacheGet(key) {
      const rows = await rpc<{ answer: string; kind: Kind }[]>("chatbot_cache_get", { p_key: key });
      return rows?.length ? { text: rows[0].answer, kind: rows[0].kind } : null;
    },
    async cachePut(key, text, kind, ttlMinutes, maxEntries) {
      await rpc("chatbot_cache_put", {
        p_key: key,
        p_answer: text,
        p_kind: kind,
        p_ttl_minutes: ttlMinutes,
        p_max_entries: maxEntries,
      });
    },
    async providersDown() {
      return (await rpc<string[]>("chatbot_providers_down")) ?? [];
    },
    async markProviderDown(provider, seconds) {
      await rpc("chatbot_mark_provider_down", { p_provider: provider, p_seconds: Math.ceil(seconds) });
    },
    async logQuery(consumer, conversationId, kind, provider, question, answer) {
      await rpc("chatbot_log_query", {
        p_consumer: consumer,
        p_conversation: conversationId,
        p_kind: kind,
        p_provider: provider,
        p_question: question,
        p_answer: answer,
      });
    },
  };
}
