// Servidor local para probar la función SIN Supabase.
//
// Corre exactamente el mismo `handleRequest` que la Edge Function, pero con la base en memoria
// (se pierde al apagarlo) y con los proveedores de IA de verdad, si hay claves en el `.env`.
// Sirve para probar el contrato, ensayar la demo con docs/chatbot.http y comprobar que la clave y
// el modelo de Gemini andan, antes de tener el proyecto de Supabase.
//
//   cd supabase/functions/chat
//   node --experimental-strip-types --no-warnings scripts/local-server.ts
//   node --experimental-strip-types --no-warnings scripts/local-server.ts --env otro.env --port 9000
//
// Lee supabase/functions/chat/.env (el mismo archivo que después se sube con `supabase secrets set`).
// No es para producción: no usa la base de datos y el token es fijo.

import { existsSync, readFileSync } from "node:fs";
import { createServer } from "node:http";
import { fileURLToPath } from "node:url";

import { loadConfig } from "../config.ts";
import type { Env } from "../config.ts";
import { handleRequest } from "../handler.ts";
import type { Deps } from "../handler.ts";
import { buildDocuments } from "../knowledge.ts";
import { KNOWLEDGE } from "../knowledge.generated.ts";
import { providerChain } from "../providers.ts";
import { MemoryStore } from "../tests/helpers.ts";

const LOCAL_TOKEN = "token-local";
const LOCAL_CONSUMER = "pruebas";
const DEFAULT_PUBLISHABLE_KEY = "sb_publishable_local";

function argument(name: string, fallback: string): string {
  const at = process.argv.indexOf(name);
  return at !== -1 && process.argv[at + 1] ? process.argv[at + 1] : fallback;
}

/** Lee un archivo `.env` simple: CLAVE=valor, comentarios con #, comillas opcionales. */
function readEnvFile(path: string): Env {
  const env: Env = {};
  if (!existsSync(path)) return env;
  for (const line of readFileSync(path, "utf-8").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!match || line.trim().startsWith("#")) continue;
    env[match[1]] = match[2].replace(/^(['"])(.*)\1$/, "$2");
  }
  return env;
}

/** Igual que la base real, pero el límite de consultas se reinicia cada minuto. */
class LocalStore extends MemoryStore {
  private window = 0;

  async checkRateLimit(consumer: string, limit: number) {
    const minute = Math.floor(Date.now() / 60000);
    if (minute !== this.window) {
      this.window = minute;
      this.hits.clear();
    }
    const hits = this.hits.get(consumer) ?? 0;
    if (hits >= limit) return Math.max(1, 60 - (Math.floor(Date.now() / 1000) % 60));
    this.hits.set(consumer, hits + 1);
    return 0;
  }
}

const envFile = argument("--env", fileURLToPath(new URL("../.env", import.meta.url)));
const port = Number(argument("--port", "8787"));
const env = readEnvFile(envFile);
const config = loadConfig({ ...env, PUBLISHABLE_KEY: env.PUBLISHABLE_KEY || DEFAULT_PUBLISHABLE_KEY });

const store = new LocalStore();
store.tokens = new Map([[LOCAL_TOKEN, LOCAL_CONSUMER]]);
const providers = providerChain(config);
const deps: Deps = { config, store, providers, documents: buildDocuments(KNOWLEDGE) };

createServer(async (incoming, outgoing) => {
  const chunks: Buffer[] = [];
  for await (const chunk of incoming) chunks.push(chunk as Buffer);
  const method = incoming.method ?? "GET";
  const headers = new Headers();
  for (const [key, value] of Object.entries(incoming.headers)) {
    if (typeof value === "string") headers.set(key, value);
  }
  const request = new Request(`http://localhost:${port}${incoming.url ?? "/"}`, {
    method,
    headers,
    body: method === "GET" || method === "HEAD" ? undefined : Buffer.concat(chunks),
  });
  const response = await handleRequest(request, deps);
  outgoing.writeHead(response.status, Object.fromEntries(response.headers));
  outgoing.end(Buffer.from(await response.arrayBuffer()));
}).listen(port, () => {
  const names = providers.map((p) => p.name);
  console.log(`\nChatbot local en http://localhost:${port}   (base en memoria, sin Supabase)`);
  console.log(
    existsSync(envFile)
      ? `Configuración leída de: ${envFile}`
      : `No existe ${envFile}: sin claves de IA, responde solo con reglas.`,
  );
  console.log(
    names.length && config.useLlm
      ? `IA configurada, en este orden: ${names.join(" → ")}`
      : "Sin proveedor de IA (falta clave o modelo, o CHATBOT_USE_LLM=false): modo reglas.",
  );
  console.log("\nPara chatbot.http:");
  console.log(`  @base   = http://localhost:${port}`);
  console.log(
    `  @apikey = ${env.PUBLISHABLE_KEY ? "(el PUBLISHABLE_KEY de tu .env)" : DEFAULT_PUBLISHABLE_KEY}`,
  );
  console.log(`  @token  = ${LOCAL_TOKEN}`);
  console.log("\nCtrl+C para apagarlo.\n");
});
