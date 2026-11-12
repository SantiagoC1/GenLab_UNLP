from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.enums import Rol
from app.core.security import require_role
from app.core.validation import raise_if_invalid
from app.integrations.chatbot import ChatbotIntegration, get_chatbot
from app.modules.chatbot import service
from app.modules.chatbot.schemas import MessageData
from app.modules.chatbot.validate import validate_message

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

PATIENT_ONLY = require_role(Rol.PACIENTE)


@router.post("/messages")
def send_message(
    data: MessageData,
    chatbot: Annotated[ChatbotIntegration, Depends(get_chatbot)],
    patient: Annotated[dict, Depends(PATIENT_ONLY)],
):
    """Escenario 40: reenvía la consulta del paciente al chatbot y devuelve su respuesta."""
    data = data.model_dump()
    raise_if_invalid(validate_message(data))
    return service.ask_chatbot(chatbot, data)
