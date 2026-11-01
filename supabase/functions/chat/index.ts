// Edge Function `chat`: punto de entrada público del chatbot (M11) sobre Supabase.
//
//   POST /functions/v1/chat    consulta
//   GET  /functions/v1/chat    health
//
// Se despliega sin verificación de JWT, porque la clave publishable no es un JWT y la validamos
// nosotros (ver handler.ts):
//
//   supabase functions deploy chat --no-verify-jwt
//
// Contrato y guía: docs/Contrato_API_Chatbot.md y docs/Guia_consumo_chatbot.md.

import { loadConfig } from "./config.ts";
import { handleRequest } from "./handler.ts";
import type { Deps } from "./handler.ts";
import { buildDocuments } from "./knowledge.ts";
import { KNOWLEDGE } from "./knowledge.generated.ts";
import { providerChain } from "./providers.ts";
import { createStore } from "./store.ts";

// SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY los inyecta Supabase en cada función

let deps: Deps | undefined;

function getDeps(): Deps {
  if (!deps) {
    const env = Deno.env.toObject();
    const config = loadConfig(env);
    deps = {
      config,
      store: createStore(env.SUPABASE_URL ?? "", env.SUPABASE_SERVICE_ROLE_KEY ?? ""),
      providers: providerChain(config),
      documents: buildDocuments(KNOWLEDGE),
    };
  }
  return deps;
}

Deno.serve((req) => handleRequest(req, getDeps()));
