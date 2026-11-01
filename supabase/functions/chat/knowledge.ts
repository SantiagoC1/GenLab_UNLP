// Base de conocimiento: búsqueda y selección de textos. Port de chatbot/app/knowledge.py.
//
// Los textos curados siguen siendo los `.md` de chatbot/knowledge/. El script
// scripts/build-knowledge.mjs los empaqueta en knowledge.generated.ts, que es lo que se despliega.

import { GENERIC_DOMAIN_TERMS, minus, tokenize } from "./text.ts";

const TITLE_WEIGHT = 3;
const BODY_WEIGHT = 1;
const MIN_SCORE = 3;

/** Un texto tal como lo deja el script de empaquetado (sin tokens). */
export interface RawDocument {
  topic: string;
  claves: string;
  source: string;
  status: string;
  body: string;
}

export interface Document {
  topic: string;
  source: string;
  status: string;
  body: string;
  titleTokens: Set<string>;
  bodyTokens: Set<string>;
}

export interface Turn {
  role: "user" | "assistant";
  content: string;
}

export function buildDocuments(raw: readonly RawDocument[]): Document[] {
  return raw.map((doc) => ({
    topic: doc.topic,
    source: doc.source,
    status: doc.status,
    body: doc.body,
    // El título sale del tema y de las palabras clave del encabezado
    titleTokens: minus(tokenize(`${doc.topic} ${doc.claves}`), GENERIC_DOMAIN_TERMS),
    bodyTokens: minus(tokenize(doc.body), GENERIC_DOMAIN_TERMS),
  }));
}

/**
 * Devuelve los textos que responden la consulta, del más al menos parecido.
 *
 * El puntaje suma 3 por cada palabra de la consulta que está en el tema o en las claves del
 * texto, y 1 por cada una que está en el cuerpo. Solo cuentan los que llegan al mínimo.
 */
export function search(
  question: string,
  documents: readonly Document[],
): { doc: Document; score: number }[] {
  const words = minus(tokenize(question), GENERIC_DOMAIN_TERMS);
  const scored: { doc: Document; score: number }[] = [];
  for (const doc of documents) {
    let score = 0;
    for (const word of words) {
      if (doc.titleTokens.has(word)) score += TITLE_WEIGHT;
      else if (doc.bodyTokens.has(word)) score += BODY_WEIGHT;
    }
    if (score >= MIN_SCORE) scored.push({ doc, score });
  }
  // sort es estable: a igual puntaje se conserva el orden de la base, como en Python
  return scored.sort((a, b) => b.score - a.score);
}

export interface PromptLimits {
  maxDocuments: number;
  topDocuments: number;
}

/**
 * Elige los textos que se le pasan al modelo.
 *
 * Con una base chica van todos (el modelo resuelve sinónimos y continuaciones). Cuando la base
 * supera `maxDocuments`, van solo los más parecidos a la consulta (junto con la anterior, si es una
 * continuación). Si el buscador no encuentra nada, van todos.
 */
export function selectForPrompt(
  question: string,
  history: readonly Turn[],
  documents: readonly Document[],
  limits: PromptLimits,
): Document[] {
  if (documents.length <= limits.maxDocuments) return [...documents];
  const previous = history.filter((t) => t.role === "user").map((t) => t.content);
  const query = previous.length ? `${previous[previous.length - 1]} ${question}` : question;
  const matches = search(query, documents);
  if (!matches.length) return [...documents];
  return matches.slice(0, limits.topDocuments).map((m) => m.doc);
}

/** Párrafos del texto; las listas con guiones se parten en un elemento por línea. */
function units(body: string): string[] {
  const result: string[] = [];
  for (const block of body.trim().split(/\n\s*\n/)) {
    const lines = block
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length && lines.every((l) => l.startsWith("- "))) {
      result.push(...lines.map((l) => l.slice(2)));
    } else if (lines.length) {
      const text = lines.join("\n");
      if (result.length && result[result.length - 1].endsWith(":")) {
        // Una introducción ("…estas etapas:") va con la lista que presenta, no sola
        result[result.length - 1] = `${result[result.length - 1]}\n\n${text}`;
      } else {
        result.push(text);
      }
    }
  }
  return result;
}

/**
 * Devuelve la parte del texto que responde la consulta, más su frase final.
 *
 * Las palabras que solo nombran el tema ("Pompe") no cuentan: lo que importa es lo que se pregunta
 * sobre él. Cada palabra de la consulta pesa más cuanto en menos párrafos aparece. Gana el párrafo
 * de mayor puntaje y, a igual puntaje, el primero. La última frase (que sugiere consultar al médico
 * tratante) siempre acompaña la respuesta y no participa del puntaje. Si ningún párrafo comparte
 * palabras con la consulta, o si la consulta solo nombra el tema ("¿qué es Pompe?"), devuelve el
 * texto completo.
 */
export function bestFragment(question: string, document: Document): string {
  const parts = units(document.body);
  if (parts.length < 3) return parts.join("\n\n");
  const closing = parts[parts.length - 1];
  const candidates = parts.slice(0, -1);
  const words = minus(tokenize(question), GENERIC_DOMAIN_TERMS, tokenize(document.topic));
  if (!words.size) return parts.join("\n\n");
  const unitTokens = candidates.map((c) => tokenize(c));
  const weights = new Map<string, number>();
  for (const word of words) {
    const count = unitTokens.filter((tokens) => tokens.has(word)).length;
    if (count) weights.set(word, 1 / count);
  }
  const scores = unitTokens.map((tokens) => {
    let total = 0;
    for (const word of tokens) total += weights.get(word) ?? 0;
    return total;
  });
  const best = Math.max(...scores);
  if (best === 0) return parts.join("\n\n");
  return `${candidates[scores.indexOf(best)]}\n\n${closing}`;
}
