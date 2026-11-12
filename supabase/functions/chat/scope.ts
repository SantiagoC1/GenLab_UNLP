// Alcance del chatbot: saludos, cortesías y derivaciones al médico. Port de chatbot/app/scope.py.

import { GENERIC_DOMAIN_TERMS, isSubset, normalize, tokenize } from "./text.ts";

/** Cómo trató el servicio la consulta. Es el campo `tipo` de la respuesta. */
export const Kind = {
  ANSWER: "respuesta",
  OUT_OF_SCOPE: "fuera_de_alcance",
  REFER_TO_DOCTOR: "derivar_medico",
  NO_INFORMATION: "sin_informacion",
} as const;
export type Kind = (typeof Kind)[keyof typeof Kind];

export const KINDS: readonly Kind[] = Object.values(Kind);

export const MESSAGES: Record<Exclude<Kind, "respuesta">, string> = {
  [Kind.OUT_OF_SCOPE]:
    "Solo puedo responder consultas sobre estudios genéticos, como el exoma clínico, " +
    "el proceso del estudio y las patologías lisosomales. Probá con otra pregunta.",
  [Kind.REFER_TO_DOCTOR]:
    "No puedo dar diagnósticos, interpretar resultados de un paciente ni recomendar " +
    "tratamientos. Te sugiero hablar de esto con tu médico tratante.",
  [Kind.NO_INFORMATION]:
    "No tengo información suficiente para responder eso. " +
    "Si es una duda sobre tu caso, consultá a tu médico tratante.",
};

export const GREETING_MESSAGE =
  "Hola, soy el asistente del laboratorio de genética. Estoy acá para ayudarte. " +
  "¿Qué querés saber?";

export const COURTESY_MESSAGE =
  "¡De nada! Si te queda alguna duda sobre estudios genéticos, preguntame.";

// --- Detección de consultas que piden un diagnóstico, un resultado propio o un tratamiento ---
//
// Todo se aplica sobre el texto sin tildes ni mayúsculas. La idea es separar dos cosas:
//   - una pregunta general ("¿qué síntomas tiene Fabry?", "¿qué es una VUS?"), que se responde;
//   - un caso personal (lo que me pasa, lo que tengo, lo que me salió y qué hacer con eso), que se
//     deriva al médico tratante.
// Los patrones de caso personal exigen un verbo en primera persona o un familiar ("mi hijo"),
// y un término médico a pocas palabras. Así "tiene" en tercera persona no alcanza.

const DISEASES =
  String.raw`fabry|pompe|gaucher|asmd|mps|mucopolisacaridosis|niemann|enfermedad|enfermedades|` +
  String.raw`lisosomal|lisosomales|patologia`;
const VARIANT_TERMS = String.raw`variantes?|vus|patogenic[ao]s?|benign[ao]s?|mutacion|mutaciones`;
const RESULT_TERMS = String.raw`resultados?|informe|positivo|negativo`;
const SYMPTOMS =
  String.raw`dolor|dolores|cansancio|debilidad|mareos?|fiebre|hormigueo|vomitos?|nauseas?|` +
  String.raw`falta de aire|ahogo|palpitaciones|calambres?|hinchazon|manchas?|picazon|ardor|` +
  String.raw`sintomas?|molestias?`;
const FAMILY =
  String.raw`hij[oa]s?|bebes?|nen[ea]s?|mama|papa|madre|padre|espos[oa]|marido|mujer|pareja|` +
  String.raw`hermano|hermana|abuel[oa]|ti[oa]|prim[oa]|familiares?|familia`;
// Hasta tres palabras entre el verbo y el término: "tengo la enfermedad de Fabry" sí,
// "tengo muchas ganas de entender qué es Fabry" no.
const GAP = String.raw`[\s,]+(?:\w+[\s,]+){0,3}?`;
const ANY_TERM = String.raw`\b(${DISEASES}|${VARIANT_TERMS}|${RESULT_TERMS}|${SYMPTOMS})\b`;

const REFERRAL_PATTERNS: string[] = [
  // Dice que tiene una enfermedad o una variante
  String.raw`\b(tengo|tenemos|padezco|sufro|me diagnosticaron|me detectaron|me confirmaron|` +
    String.raw`soy portador|soy portadora)${GAP}(${DISEASES}|${VARIANT_TERMS})\b`,
  // Un familiar la tiene
  String.raw`\b(mi|mis|nuestro|nuestra)\s+(${FAMILY})\b.*?\b(tiene|tienen|tuvo|padece|sufre|siente|` +
    String.raw`presenta|le diagnosticaron|le detectaron|le confirmaron|le salio|le dio|le duele|le duelen)` +
    String.raw`${GAP}(${DISEASES}|${VARIANT_TERMS}|${SYMPTOMS})\b`,
  // Cuenta síntomas propios
  String.raw`\b(tengo|tenemos|siento|sentimos|noto|notamos|presento|sufro|tuve)(?! que\b)${GAP}` +
    String.raw`(${SYMPTOMS})\b`,
  String.raw`\bme (duele|duelen|dolia|molesta|molestan|marea|mareo|canso|cansa|agota|hormiguea|` +
    String.raw`hormiguean|late|sangra|hincha|hinchan|quema|arde)\b`,
  String.raw`\b(estos|mis|mi)\s+sintomas?\b`,
  String.raw`\b(estoy|esta|esta mi (hijo|hija))\b.*\b(enfermo|enferma|sano|sana)\b`,
  // Pregunta si puede tener o va a tener una enfermedad
  String.raw`\b(puedo|podria|sera que)\b.*\b(tener|padecer)\b`,
  String.raw`\bes (hereditario|hereditaria) (en )?(mi|mis)\b`,
  // Resultado propio
  String.raw`\b(mi|mis)\b.*\b(resultado|resultados|variante|variantes|informe)\b.*` +
    String.raw`\b(significa|quiere decir|indica|es grave|es normal|salio|dio|positivo|negativo)\b`,
  // Cualquier mención de tratamiento, general o personal, se deriva al médico
  String.raw`\b(tratamientos?|tratar|tratarse|trata|tratan|curar|curarse|cura|sanar|terapias?|` +
    String.raw`medicamentos?|medicacion|remedios?|pastillas?|dosis|drogas?|farmacos?|inyecciones|` +
    String.raw`infusiones|reemplazo enzimatico)\b`,
  String.raw`\b(debo|tengo que|puedo|deberia)\b.*\b(tomar|tratar|medicar|operar)\b`,
  String.raw`\bque (tomo|me tomo|debo tomar|puedo tomar)\b`,
  String.raw`\b(me recomienda|me recomiendas|me aconseja|me aconsejas)\b`,
  // Cuánto va a vivir alguien: el pronóstico es del médico
  String.raw`\b(pronostico|esperanza de vida|mortal|morir|muere|se muere|cuanto (tiempo )?vive|` +
    String.raw`cuanto (tiempo )?(voy a|va a) vivir)\b`,
];
const REFERRAL = REFERRAL_PATTERNS.map((p) => new RegExp(p));

// Pedidos de valoración o de consejo sobre algo propio. Solos no alcanzan ("¿qué hago para
// sacar un turno?"): tienen que ir con un término médico. Por eso "me salió una VUS, ¿qué es?"
// es una pregunta general, y "me salió una VUS, ¿es grave?" es un caso personal.
const JUDGMENT_PATTERNS: string[] = [
  String.raw`\b(es|sera|seria|esta|estoy)\s+(muy\s+)?(grave|peligros[oa]|malo|mala|preocupante|serio|` +
    String.raw`seria|normal)\b`,
  String.raw`\bque (hago|debo hacer|tengo que hacer|puedo hacer|me conviene|hacemos)\b`,
  String.raw`\b(tengo|debo|tendria)\s+que\s+(preocup\w+|operar\w*|consultar\w*)\b`,
  String.raw`\b(me preocupo|preocuparme|preocuparnos)\b`,
  String.raw`\b(en mi caso|en nuestro caso|para mi caso)\b`,
  String.raw`\bme (afecta|va a afectar|implica)\b`,
  String.raw`\b(voy a|va a) (morir|enfermar|empeorar|curar|estar bien)\b`,
  String.raw`\b(mis|mi)\s+(hij\w+|nietos?)\b.*\b(heredar\w*|transmit\w+|heredan?)\b`,
  String.raw`\b(lo|la) (voy a|puedo|podria) (heredar|transmitir|pasar)\b`,
];
const JUDGMENT = JUDGMENT_PATTERNS.map((p) => new RegExp(p));
const ANY_TERM_RE = new RegExp(ANY_TERM);

// Frases que solo anuncian una pregunta ("tengo una duda"): no cuentan como un caso personal.
const PREAMBLE = new RegExp(
  String.raw`\b(tengo|tenia|tenemos|me quedo|me quedaron)\s+(una|unas|otra|otras|alguna|algunas|mucha|` +
    String.raw`muchas)?\s*(duda|dudas|consulta|consultas|pregunta|preguntas|curiosidad|ganas de saber)\b` +
    String.raw`|\b(tengo|tenemos) que (saber|entender|preguntar|consultar)\b`,
  "g",
);

const GREETING = /^\s*(hola|buenas|buen dia|buenos dias|buenas tardes|buenas noches|hey)\b/;
// Palabras que pueden acompañar a un saludo o agradecimiento sin ser una consulta.
const SMALL_TALK: ReadonlySet<string> = tokenize(
  "hola buenas buen dias tardes noches hey como estas todo bien tal gracias muchas mil " +
    "chau adios hasta luego listo ok dale",
);
const COURTESY = /^\s*(muchas |mil )?(gracias|chau|adios|hasta luego|listo|ok|dale)\b/;

/** Indica si el mensaje es solo un saludo (sin otra consulta). */
export function isGreeting(message: string): boolean {
  const text = normalize(message);
  return GREETING.test(text) && isSubset(tokenize(text), SMALL_TALK);
}

/** Indica si el mensaje es solo un agradecimiento o una despedida. */
export function isCourtesy(message: string): boolean {
  const text = normalize(message);
  return COURTESY.test(text) && isSubset(tokenize(text), SMALL_TALK);
}

/** Indica si la consulta pide un diagnóstico, interpretar un resultado o un tratamiento. */
export function asksForDiagnosis(message: string): boolean {
  const text = normalize(message).replace(PREAMBLE, " ");
  if (REFERRAL.some((pattern) => pattern.test(text))) return true;
  return ANY_TERM_RE.test(text) && JUDGMENT.some((pattern) => pattern.test(text));
}

/** Indica si la consulta menciona algún término del tema, aunque no haya texto para responderla. */
export function isAboutGenetics(message: string): boolean {
  return [...tokenize(message)].some((w) => GENERIC_DOMAIN_TERMS.has(w));
}
