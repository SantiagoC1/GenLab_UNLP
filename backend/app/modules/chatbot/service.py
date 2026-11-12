from app.integrations.chatbot import ChatbotIntegration


def ask_chatbot(chatbot: ChatbotIntegration, data: dict):
    """
    Envía un mensaje al chatbot y devuelve su respuesta.
    """
    return chatbot.ask(data["message"].strip(), data.get("conversation_id") or None)
