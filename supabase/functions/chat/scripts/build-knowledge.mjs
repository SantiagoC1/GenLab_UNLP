// Empaqueta los textos curados de chatbot/knowledge/*.md en knowledge.generated.ts.
//
// La Edge Function no lee archivos del disco al responder: la base de conocimiento viaja dentro
// del código desplegado. Correr este script cada vez que se cambia un texto y antes de desplegar:
//
//   node supabase/functions/chat/scripts/build-knowledge.mjs
//
// Con --check no escribe nada: falla si el archivo generado está desactualizado (lo usa el CI).

import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, basename } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const knowledgeDir = join(here, "..", "..", "..", "..", "chatbot", "knowledge");
const outputFile = join(here, "..", "knowledge.generated.ts");

/** Lee un archivo con encabezado `---`. Devuelve null si no lo tiene (el README). */
function parse(file) {
  const raw = readFileSync(join(knowledgeDir, file), "utf-8").replace(/\r\n/g, "\n");
  const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return null;
  const header = {};
  for (const line of match[1].split("\n")) {
    const at = line.indexOf(":");
    if (at !== -1) header[line.slice(0, at).trim()] = line.slice(at + 1).trim();
  }
  return {
    topic: header.tema ?? basename(file, ".md"),
    claves: header.claves ?? "",
    source: header.fuente ?? "",
    status: header.estado ?? "borrador",
    body: match[2].trim(),
  };
}

const documents = readdirSync(knowledgeDir)
  .filter((file) => file.endsWith(".md"))
  .sort()
  .map(parse)
  .filter(Boolean);

const content =
  "// GENERADO por scripts/build-knowledge.mjs a partir de chatbot/knowledge/*.md. No editar a mano.\n\n" +
  'import type { RawDocument } from "./knowledge.ts";\n\n' +
  `export const KNOWLEDGE: RawDocument[] = ${JSON.stringify(documents, null, 2)};\n`;

if (process.argv.includes("--check")) {
  let current = "";
  try {
    current = readFileSync(outputFile, "utf-8").replace(/\r\n/g, "\n");
  } catch {
    // no existe: se informa abajo
  }
  if (current !== content) {
    console.error("knowledge.generated.ts está desactualizado. Correr build-knowledge.mjs.");
    process.exit(1);
  }
  console.log(`knowledge.generated.ts al día (${documents.length} textos).`);
} else {
  writeFileSync(outputFile, content, "utf-8");
  console.log(`Escrito ${outputFile} con ${documents.length} textos.`);
}
