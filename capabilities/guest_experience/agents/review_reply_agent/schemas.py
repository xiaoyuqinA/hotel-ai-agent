from pydantic import BaseModel

class ReplyResult(BaseModel):
    reply_content: str