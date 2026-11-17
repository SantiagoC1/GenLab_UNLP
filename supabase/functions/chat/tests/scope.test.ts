// Reglas de alcance: qué se deriva al médico y qué se responde. Las mismas listas que
// chatbot/tests/test_scope.py (la paridad con Python la comprueba parity.test.ts).

import assert from "node:assert/strict";
import test from "node:test";

import { asksForDiagnosis } from "../scope.ts";

// Casos personales, tratamientos y pronósticos: se derivan al médico tratante.
const REFERRALS = [
  "¿Me duele el pecho, es Fabry?",
  "me duelen las manos",
  "Tengo dolor en las manos",
  "siento mucho cansancio",
  "me canso mucho al caminar",
  "Me duele el pecho y tengo debilidad, ¿es lo que tengo?",
  "Tengo Fabry, ¿qué hago?",
  "Tengo una duda: ¿tengo Fabry?",
  "creo que tengo Fabry",
  "¿Puedo tener Gaucher?",
  "Me diagnosticaron Pompe, ¿y ahora?",
  "Mi hijo tiene Fabry, ¿qué es?",
  "¿Mi hija tiene Gaucher?",
  "mi mamá tiene dolor en las manos",
  "mi bebé tiene fiebre y le diagnosticaron MPS",
  "Me salió una variante patogénica, ¿es grave?",
  "Me salió una VUS, ¿tengo que preocuparme?",
  "me dieron un resultado positivo, ¿qué hago?",
  "¿Mi resultado quiere decir que estoy enfermo?",
  "¿Mis hijos pueden heredar Fabry?",
  "¿Qué medicación tomo?",
  "¿Qué pastillas debo tomar?",
  "¿Se cura el Pompe?",
  "¿Tiene cura el Gaucher?",
  "Tengo Gaucher, ¿qué tomo?",
  "¿Qué medicamento me recomiendas?",
  "¿Cuánto vive alguien con Gaucher?",
  "¿Cuál es el pronóstico del Pompe?",
];

// Preguntas generales: se responden, incluso si alguien cuenta algo suyo pero pregunta por el concepto.
const GENERAL_QUESTIONS = [
  "tengo una duda, ¿qué es un exoma?",
  "Hola, tengo una consulta: ¿qué es la enfermedad de Fabry?",
  "Tengo una duda sobre Pompe",
  "Tengo curiosidad: ¿cómo se hereda Gaucher?",
  "Tengo que saber qué síntomas tiene el ASMD",
  "¿Qué síntomas tiene la enfermedad de Fabry?",
  "¿Cuáles son los síntomas de Pompe?",
  "¿Cuántas personas tienen Fabry?",
  "¿Cómo se hereda Pompe?",
  "¿Qué es una VUS?",
  "¿Qué es una variante patogénica?",
  "Me salió una VUS, ¿qué es?",
  "me salió una variante patogénica, ¿qué significa?",
  "Mi médico me pidió un exoma, ¿qué es?",
  "Mi hija tiene 7 años, ¿qué es Gaucher?",
  "¿Qué hago para sacar un turno?",
  "¿Mi hijo puede ir solo a la extracción?",
  "tengo el resultado, ¿dónde lo veo?",
  "¿Qué es el exoma clínico?",
  "Hola",
  "gracias",
];

for (const message of REFERRALS) {
  test(`se deriva al médico: ${message}`, () => assert.ok(asksForDiagnosis(message), message));
}

for (const message of GENERAL_QUESTIONS) {
  test(`se responde: ${message}`, () => assert.ok(!asksForDiagnosis(message), message));
}
