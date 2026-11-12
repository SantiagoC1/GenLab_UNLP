from app.modules.acceso.validate import required_field_error

MAX_MESSAGE_LENGTH = 1000 
MAX_CONVERSATION_ID_LENGTH = 200


def validate_message(data: dict):
    """Valida el mensaje del paciente y, si viene, el identificador de la conversación."""
    errors = []
    message = data.get("message")
    if message is None or not message.strip():
        errors.append(required_field_error("message"))
    elif len(message) > MAX_MESSAGE_LENGTH:
        errors.append(f"El mensaje no puede tener más de {MAX_MESSAGE_LENGTH} caracteres.")

    conversation_id = data.get("conversation_id")
    if conversation_id is not None and len(conversation_id) > MAX_CONVERSATION_ID_LENGTH:
        errors.append("El identificador de la conversación no es válido.")
    return errors
