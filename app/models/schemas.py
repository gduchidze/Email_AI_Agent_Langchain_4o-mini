from typing import List, Optional, Union
from pydantic import BaseModel, Field

class SearchArgsSchema(BaseModel):
    message_id: str = Field(..., description="The unique ID of the email message, retrieved from a search.")

class SendMessageSchema(BaseModel):
    message: str = Field(..., description="The message to send.")
    to: Union[str, List[str]] = Field(..., description="The list of recipients.")
    subject: str = Field(..., description="The subject of the message.")
    cc: Optional[Union[str, List[str]]] = Field(default=None, description="The list of CC recipients.")
    bcc: Optional[Union[str, List[str]]] = Field(default=None, description="The list of BCC recipients.")

class GetThreadSchema(BaseModel):
    thread_id: str = Field(..., description="The thread ID.")