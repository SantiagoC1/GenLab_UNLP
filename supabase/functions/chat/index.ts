// Edge Function `chat`: punto de entrada público del chatbot (M11) sobre Supabase.
//
//   POST /functions/v1/chat    consulta
//   GET  /functions/v1/chat    health
//
// Contrato y guía: docs/Contrato_API_Chatbot.md y docs/Guia_consumo_chatbot.md.

import { loadConfig } from "./config.ts";
import { handleRequest } from "./handler.ts";
import type { Deps } from "./handler.ts";
import { buildDocuments } from "./knowledge.ts";
import { KNOWLEDGE } from "./knowledge.generated.ts";
import { providerChain } from "./providers.ts";
import { createStore } from "./store.ts";

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
