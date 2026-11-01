from app.integrations.chatbot import ChatbotIntegration


def ask_chatbot(chatbot: ChatbotIntegration, data: dict) -> dict:
    """
    Escenario 40: el paciente consulta al chatbot y se le muestra la respuesta.

    No se guarda nada en GenLab (M11-RF7: no se almacenan datos personales); el historial de la
    conversación lo mantiene el chatbot.
    """
    return chatbot.ask(data["message"].strip(), data.get("conversation_id") or None)
