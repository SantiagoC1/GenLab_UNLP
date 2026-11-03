// Base de conocimiento: búsqueda y selección de textos. Port de chatbot/app/knowledge.py.
//
// Los textos curados siguen siendo los `.md` de chatbot/knowledge/.

import { GENERIC_DOMAIN_TERMS, minus, tokenize } from "./text.ts";

const TITLE_WEIGHT = 3;
const BODY_WEIGHT = 1;
const MIN_SCORE = 3;

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
/** Identifica preguntas que dependen del contexto anterior. */
export function isFollowUp(question: string): boolean {
  const normalized = question
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

  return /^(?:[¿?]?\s*)?(?:y\s+)?(?:eso|esto|esa|ese|como|cuando|por que|de que manera|se hereda|que significa)\b/.test(normalized)
    && !/\b(?:enfermedad de|sindrome de)\b/.test(normalized);
}

export function selectForPrompt(
  question: string,
  history: readonly Turn[],
  documents: readonly Document[],
  limits: PromptLimits,
): Document[] {
  if (documents.length <= limits.maxDocuments) return [...documents];

  let matches = search(question, documents);

  if (!matches.length && isFollowUp(question)) {
    const previous = history
      .filter((t) => t.role === "user")
      .map((t) => t.content);

    if (previous.length) {
      matches = search(
        `${previous[previous.length - 1]} ${question}`,
        documents,
      );
    }
  }

  if (!matches.length) return [];

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
