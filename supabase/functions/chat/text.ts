// Normalización y tokenización de texto. Port de chatbot/app/text.py.

// Palabras que no sirven para encontrar un tema.
export const STOPWORDS: ReadonlySet<string> = new Set(
  (
    "el la los las un una unos unas de del al y o u a en con por para que como cual cuales " +
    "es son ser fue sobre su sus se lo le les me mi mis te tu tus nos este esta esto estos " +
    "estas ese esa eso muy mas menos hay hace hacer puede pueden tiene tienen quiero quisiera " +
    "saber decir explicame explicar cuentame dime tipo"
  ).split(" "),
);

// Palabras del tema que no alcanzan para elegir un texto (aparecen en casi todos),
// pero sí sirven para saber que la consulta es del tema.
const GENERIC_WORDS =
  "enfermedad enfermedades patologia patologias estudio estudios genetico geneticos genetica " +
  "geneticas gen genes adn analisis paciente muestra sangre laboratorio resultado resultados " +
  "variante variantes mutacion mutaciones hereditaria hereditario herencia secuenciacion " +
  "sintoma sintomas diagnostico";

/** Pasa a minúsculas y saca las tildes. */
export function normalize(text: string): string {
  return text.toLowerCase().normalize("NFD").replace(/\p{Mn}/gu, "");
}

/** Saca el plural más común, para que 'exomas' encuentre 'exoma'. */
function stem(word: string): string {
  if (word.length > 4 && word.endsWith("es")) return word.slice(0, -2);
  if (word.length > 3 && word.endsWith("s")) return word.slice(0, -1);
  return word;
}

export const GENERIC_DOMAIN_TERMS: ReadonlySet<string> = new Set(
  GENERIC_WORDS.split(" ").map(stem),
);

/** Devuelve las palabras con significado de un texto, normalizadas. */
export function tokenize(text: string): Set<string> {
  const words = normalize(text).match(/[a-z0-9]+/g) ?? [];
  return new Set(words.filter((w) => w.length >= 3 && !STOPWORDS.has(w)).map(stem));
}

/** Diferencia de conjuntos: los elementos de `a` que no están en ninguno de `others`. */
export function minus(a: Set<string>, ...others: ReadonlySet<string>[]): Set<string> {
  return new Set([...a].filter((w) => !others.some((o) => o.has(w))));
}

export function isSubset(a: ReadonlySet<string>, b: ReadonlySet<string>): boolean {
  return [...a].every((w) => b.has(w));
}
