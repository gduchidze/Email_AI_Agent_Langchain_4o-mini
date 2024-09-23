from contextlib import asynccontextmanager
import uvicorn
import sys
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from langchain_community.tools.gmail.utils import get_gmail_credentials, build_resource_service
from app.services.gmail_services import GmailSendMessage
import asyncio
import uuid
import logging
from app.services.ai_service import AIService
from app.utils.helpers import fetch_unread_emails, mark_as_read, fetch_thread_messages
from app.config import TOKEN_FILE, CREDENTIALS_FILE
from app.prompt import instructions

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

logger = logging.getLogger(__name__)

credentials = get_gmail_credentials(
    token_file=TOKEN_FILE,
    scopes=["https://mail.google.com/"],
    client_secrets_file=CREDENTIALS_FILE,
)

ai_service = AIService(credentials, instructions)
api_resource = build_resource_service(credentials)
gmail_send_service = GmailSendMessage(api_resource=api_resource)
chat_history: Dict[str, Dict[str, List[Dict[str, str]]]] = {}


class EmailResponse(BaseModel):
    message: str
    to: str
    subject: str


class GiantiEmailAssistant:
    def __init__(self):
        self.credentials = credentials
        self.ai_service = ai_service
        self.unread_emails = []

    async def process_emails(self):
        self.unread_emails = fetch_unread_emails(self.credentials)
        for email in self.unread_emails:
            thread_id = email['threadId']
            if thread_id not in chat_history:
                chat_history[thread_id] = {"messages": []}
            thread_messages = fetch_thread_messages(self.credentials, thread_id)
            for message in thread_messages:
                chat_history[thread_id]["messages"].append({
                    'id': message['id'],
                    'sender': 'user' if message['from'] != 'me' else 'assistant',
                    'content': message['body']
                })
            if chat_history[thread_id]["messages"][-1]['sender'] == 'user':
                try:
                    thread_history = "\n".join(
                        [f"{'User' if msg['sender'] == 'user' else 'Assistant'}: {msg['content']}"
                         for msg in chat_history[thread_id]["messages"]])

                    input_data = {
                        "input": f"""
                        1. Read and analyze the following email thread:
                           Subject: {email['subject']}
                           Sender: {email['sender']}
                           Thread History:
                           {thread_history}
                        2. Generate an appropriate response based on the entire email thread content and the given instructions.
                        3. If you cannot respond or the question is irrelevant, return I cannot respond.
                        4. Write a formal email response in a polite and professional tone. Format the following text as an email, with the appropriate salutation, clear paragraphs, and a polite closing statement.
                        """
                    }
                    ai_response = self.ai_service.generate_response(input_data)

                    if "I cannot respond" in ai_response or "The question is irrelevant" in ai_response:
                        chat_history[thread_id]["messages"].append({
                            'id': str(uuid.uuid4()),
                            'sender': 'bot',
                            'content': ai_response,
                            'requires_human_attention': True
                        })
                    else:
                        chat_history[thread_id]["messages"].append({
                            'id': str(uuid.uuid4()),
                            'sender': 'bot',
                            'content': ai_response
                        })
                        gmail_send_service.run(
                            message=ai_response,
                            to=email['sender'],
                            subject=f"Re: {email['subject']}",
                            thread_id=thread_id
                        )
                except Exception as e:
                    logger.error(f"Error processing email from {email['sender']}: {str(e)}")
            mark_as_read(self.credentials, email['id'])
        logger.info(f"Processed and marked as read: {len(self.unread_emails)} emails.")


assistant = GiantiEmailAssistant()
async def process_emails_periodically():
    while True:
        await assistant.process_emails()
        await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(process_emails_periodically())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/chats")
async def get_chats():
    return {"chats": chat_history}


@app.get("/chat_history/{thread_id}")
async def get_chat_history(thread_id: str):
    if thread_id not in chat_history:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"thread_id": thread_id, "messages": chat_history[thread_id]}


@app.get("/thread_ids")
async def get_thread_ids():
    return {"thread_ids": list(chat_history.keys())}


@app.post("/manual_respond/{thread_id}")
async def manual_respond(thread_id: str, response: EmailResponse):
    if thread_id not in chat_history:
        raise HTTPException(status_code=404, detail="Thread not found")

    chat_history[thread_id]["messages"].append({
        'id': str(uuid.uuid4()),
        'sender': 'human',
        'content': response.message
    })

    try:
        gmail_send_service.run(
            message=response.message,
            to=response.to,
            subject=response.subject,
            thread_id=thread_id
        )
        return {"status": "success", "message": "Manual response sent successfully"}
    except Exception as e:
        logger.error(f"Error sending manual response: {str(e)}")
        return {"status": "error", "message": f"Failed to send manual response: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)