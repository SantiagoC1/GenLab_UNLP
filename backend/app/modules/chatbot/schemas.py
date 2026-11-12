from pydantic import BaseModel


class MessageData(BaseModel):
    message: str | None = None
    conversation_id: str | None = None
