export type Env = Record<string, string | undefined>;

export interface Config {
  publishableKey: string;
  /** Solo desarrollo: no pide `apikey` ni token. */
  authDisabled: boolean;
  corsOrigins: string;

  // Servicio
  available: boolean;
  rateLimit: number;
  conversationTtlMinutes: number;
  conversationMaxTurns: number;
  cacheTtlMinutes: number;
  cacheMaxEntries: number;
  promptMaxDocuments: number;
  promptTopDocuments: number;

  // Modelos de lenguaje
  useLlm: boolean;
  llmProviders: string[];
  llmTimeoutSeconds: number;
  providerCooldownSeconds: number;
  gemini: { apiKey: string; model: string };
  groq: { apiKey: string; model: string; baseUrl: string };
  nvidia: { apiKey: string; model: string; baseUrl: string };
  openrouter: { apiKey: string; model: string; baseUrl: string };
}

function text(env: Env, name: string, fallback = ""): string {
  const value = env[name]?.trim();
  return value ? value : fallback;
}

function number(env: Env, name: string, fallback: number): number {
  const value = Number(env[name]);
  return env[name]?.trim() && Number.isFinite(value) ? value : fallback;
}

function flag(env: Env, name: string, fallback: boolean): boolean {
  const value = env[name]?.trim().toLowerCase();
  if (!value) return fallback;
  return ["1", "true", "yes", "si"].includes(value);
}

export function loadConfig(env: Env): Config {
  return {
    publishableKey: text(env, "PUBLISHABLE_KEY"),
    authDisabled: flag(env, "CHATBOT_AUTH_DISABLED", false),
    corsOrigins: text(env, "CORS_ORIGINS", "*"),

    available: flag(env, "CHATBOT_AVAILABLE", true),
    rateLimit: number(env, "CHATBOT_RATE_LIMIT", 20),
    conversationTtlMinutes: number(env, "CONVERSATION_TTL_MINUTES", 30),
    conversationMaxTurns: number(env, "CONVERSATION_MAX_TURNS", 6),
    cacheTtlMinutes: number(env, "CHATBOT_CACHE_TTL_MINUTES", 60),
    cacheMaxEntries: number(env, "CHATBOT_CACHE_MAX_ENTRIES", 500),
    promptMaxDocuments: number(env, "CHATBOT_PROMPT_MAX_DOCUMENTS", 12),
    promptTopDocuments: number(env, "CHATBOT_PROMPT_TOP_DOCUMENTS", 3),

    useLlm: flag(env, "CHATBOT_USE_LLM", true),
    llmProviders: text(env, "CHATBOT_LLM_PROVIDERS", "gemini,groq,nvidia")
      .split(",")
      .map((name) => name.trim().toLowerCase())
      .filter(Boolean),
    llmTimeoutSeconds: number(env, "CHATBOT_LLM_TIMEOUT_SECONDS", 12),
    providerCooldownSeconds: number(env, "CHATBOT_PROVIDER_COOLDOWN_SECONDS", 90),
    gemini: { apiKey: text(env, "GEMINI_API_KEY"), model: text(env, "GEMINI_MODEL") },
    groq: {
      apiKey: text(env, "GROQ_API_KEY"),
      model: text(env, "GROQ_MODEL", "openai/gpt-oss-120b"),
      baseUrl: text(env, "GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
    },
    nvidia: {
      apiKey: text(env, "NVIDIA_API_KEY"),
      model: text(env, "NVIDIA_MODEL", "openai/gpt-oss-120b"),
      baseUrl: text(env, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    },
    openrouter: {
      apiKey: text(env, "OPENROUTER_API_KEY"),
      model: text(env, "OPENROUTER_MODEL"),
      baseUrl: text(env, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    },
  };
}
