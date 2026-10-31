import pytest

from app.scope import asks_for_diagnosis

# Casos personales, tratamientos y pronósticos: se derivan al médico tratante.
REFERRALS = [
    # síntomas propios
    "¿Me duele el pecho, es Fabry?",
    "me duelen las manos",
    "Tengo dolor en las manos",
    "siento mucho cansancio",
    "me canso mucho al caminar",
    "Me duele el pecho y tengo debilidad, ¿es lo que tengo?",
    # diagnóstico propio o de un familiar
    "Tengo Fabry, ¿qué hago?",
    "Tengo una duda: ¿tengo Fabry?",
    "creo que tengo Fabry",
    "¿Puedo tener Gaucher?",
    "Me diagnosticaron Pompe, ¿y ahora?",
    "Mi hijo tiene Fabry, ¿qué es?",
    "¿Mi hija tiene Gaucher?",
    "mi mamá tiene dolor en las manos",
    "mi bebé tiene fiebre y le diagnosticaron MPS",
    # resultado propio con pedido de valoración
    "Me salió una variante patogénica, ¿es grave?",
    "Me salió una VUS, ¿tengo que preocuparme?",
    "me dieron un resultado positivo, ¿qué hago?",
    "¿Mi resultado quiere decir que estoy enfermo?",
    "¿Mis hijos pueden heredar Fabry?",
    # tratamientos
    "¿Qué medicación tomo?",
    "¿Qué pastillas debo tomar?",
    "¿Se cura el Pompe?",
    "¿Tiene cura el Gaucher?",
    "Tengo Gaucher, ¿qué tomo?",
    "¿Qué medicamento me recomiendas?",
    # pronóstico
    "¿Cuánto vive alguien con Gaucher?",
    "¿Cuál es el pronóstico del Pompe?",
]

# Preguntas generales: se responden. Incluye los casos donde alguien cuenta algo suyo pero
# pregunta por el concepto.
GENERAL_QUESTIONS = [
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
]


@pytest.mark.parametrize("message", REFERRALS)
def test_personal_cases_treatments_and_prognosis_are_referred(message):
    assert asks_for_diagnosis(message), message


@pytest.mark.parametrize("message", GENERAL_QUESTIONS)
def test_general_questions_are_not_referred(message):
    assert not asks_for_diagnosis(message), message


def test_a_result_the_patient_brings_gets_the_general_explanation_only(client):
    """Decisión: "me salió una VUS, ¿qué es?" se responde en general, sin leer el caso personal."""
    body = client.post("/chat", json={"mensaje": "Me salió una VUS, ¿qué es?"}).json()
    assert body["tipo"] == "respuesta"
    assert "significado incierto" in body["respuesta"]
    assert "médico tratante" in body["respuesta"]


def test_a_symptom_question_is_referred_to_the_treating_doctor_not_to_the_lab(client):
    body = client.post("/chat", json={"mensaje": "¿Me duele el pecho, es Fabry?"}).json()
    assert body["tipo"] == "derivar_medico"
    assert "médico tratante" in body["respuesta"]
    assert "laboratorio" not in body["respuesta"].lower()
