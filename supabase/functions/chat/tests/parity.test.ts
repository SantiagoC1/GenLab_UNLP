// Paridad con la versión de referencia en Python: las mismas consultas tienen que dar las mismas
// decisiones. El fixture lo genera gen_parity_fixture.py a partir de chatbot/app.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { buildDocuments, search } from "../knowledge.ts";
import { KNOWLEDGE } from "../knowledge.generated.ts";
import { answerWithRules, cacheKey, scrub } from "../handler.ts";
import { asksForDiagnosis, isAboutGenetics, isCourtesy, isGreeting } from "../scope.ts";

interface Case {
  question: string;
  history: { role: "user" | "assistant"; content: string }[];
  greeting: boolean;
  courtesy: boolean;
  refers: boolean;
  genetics: boolean;
  matches: [string, number][];
  rules_text: string;
  rules_kind: string;
  scrub: string;
  cache_key: string;
}

const cases: Case[] = JSON.parse(readFileSync(new URL("./parity.json", import.meta.url), "utf-8"));
const documents = buildDocuments(KNOWLEDGE);

test("el fixture de paridad tiene casos", () => {
  assert.ok(cases.length >= 80);
});

for (const [index, c] of cases.entries()) {
  test(`paridad ${index}: ${JSON.stringify(c.question)}${c.history.length ? " (con historial)" : ""}`, () => {
    assert.equal(isGreeting(c.question), c.greeting, "saludo");
    assert.equal(isCourtesy(c.question), c.courtesy, "cortesía");
    assert.equal(asksForDiagnosis(c.question), c.refers, "derivación al médico");
    assert.equal(isAboutGenetics(c.question), c.genetics, "es del tema");
    assert.deepEqual(
      search(c.question, documents).map((m) => [m.doc.topic, m.score]),
      c.matches,
      "búsqueda",
    );
    const [text, kind] = answerWithRules(c.question, c.history, documents);
    assert.equal(kind, c.rules_kind, "tipo en modo reglas");
    assert.equal(text, c.rules_text, "texto en modo reglas");
    assert.equal(scrub(c.question.trim()), c.scrub, "datos tapados");
    assert.equal(cacheKey(c.question), c.cache_key, "clave de caché");
  });
}
