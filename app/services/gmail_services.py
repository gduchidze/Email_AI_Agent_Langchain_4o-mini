import logging
from typing import Dict, Optional, Any, Union, List, Type
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_google_community.gmail.base import GmailBaseTool
from app.models.schemas import SearchArgsSchema, SendMessageSchema, GetThreadSchema
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email
from langchain_google_community.gmail.utils import clean_email_body

logger = logging.getLogger(__name__)


class GmailSendMessage(GmailBaseTool):
    name: str = "send_gmail_message"
    description: str = "Use this tool to send email messages. The input is the message, recipients"
    args_schema: Type[SendMessageSchema] = SendMessageSchema

    def _prepare_message(self, message: str, to: Union[str, List[str]], subject: str,
                         thread_id: Optional[str] = None, bcc: Optional[str] = None) -> Dict[str, Any]:
        mime_message = MIMEMultipart()
        mime_message.attach(MIMEText(message, "html"))
        mime_message["To"] = ", ".join(to if isinstance(to, list) else [to])
        mime_message["Subject"] = subject
        if bcc:
            mime_message["Bcc"] = bcc

        if thread_id:
            thread = self.api_resource.users().threads().get(userId="me", id=thread_id).execute()
            original_message = thread['messages'][0]
            original_headers = {header['name']: header['value'] for header in original_message['payload']['headers']}

            if 'Message-ID' in original_headers:
                mime_message["In-Reply-To"] = original_headers['Message-ID']
                mime_message["References"] = original_headers['Message-ID']

        raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
        return {"raw": raw_message, "threadId": thread_id} if thread_id else {"raw": raw_message}

    def _run(self, message: str, to: Union[str, List[str]], subject: str,
             thread_id: Optional[str] = None, bcc: Optional[str] = "giorgiduchidze@pulsarai.ge",
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            create_message = self._prepare_message(message, to, subject, thread_id, bcc)
            send_message = self.api_resource.users().messages().send(userId="me", body=create_message)
            sent_message = send_message.execute()
            return f'Message sent. Message Id: {sent_message["id"]}'
        except Exception as error:
            raise Exception(f"An error occurred: {error}")

class GmailGetMessage(GmailBaseTool):
    name: str = "get_gmail_message"
    description: str = (
        "Use this tool to fetch an email by message ID."
        " Returns the thread ID, snippet, body, subject, and sender."
    )
    args_schema: Type[SearchArgsSchema] = SearchArgsSchema

    def _run(
        self,
        message_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        query = (
            self.api_resource.users()
            .messages()
            .get(userId="me", format="raw", id=message_id)
        )
        message_data = query.execute()
        raw_message = base64.urlsafe_b64decode(message_data["raw"])
        email_msg = email.message_from_bytes(raw_message)
        subject = email_msg["Subject"]
        sender = email_msg["From"]
        message_body = ""
        if email_msg.is_multipart():
            for part in email_msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in cdispo:
                    message_body = part.get_payload(decode=True).decode("utf-8")
                    break
        else:
            message_body = email_msg.get_payload(decode=True).decode("utf-8")
        body = clean_email_body(message_body)
        return {
            "id": message_id,
            "threadId": message_data["threadId"],
            "snippet": message_data["snippet"],
            "body": body,
            "subject": subject,
            "sender": sender,
        }

class GmailGetThread(GmailBaseTool):
    name: str = "get_gmail_thread"
    description: str = (
        "Use this tool to search for email messages."
        " The input must be a valid Gmail query."
        " The output is a JSON list of messages."
    )
    args_schema: Type[GetThreadSchema] = GetThreadSchema

    def _run(
        self,
        thread_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        query = self.api_resource.users().threads().get(userId="me", id=thread_id)
        thread_data = query.execute()
        if not isinstance(thread_data, dict):
            raise ValueError("The output of the query must be a list.")
        messages = thread_data["messages"]
        thread_data["messages"] = []
        keys_to_keep = ["id", "snippet"]
        for message in messages:
            thread_data["messages"].append(
                {k: message[k] for k in keys_to_keep if k in message}
            )
        return thread_data

