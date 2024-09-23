import base64
from typing import Dict, List
from googleapiclient.discovery import build

def fetch_unread_emails(credentials) -> List[Dict]:
    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD']).execute()
    messages = results.get('messages', [])

    unread_emails = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        email_data = {
            'id': msg['id'],
            'threadId': msg['threadId'],
            'subject': next(header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'),
            'sender': next(header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'),
            'body': msg['snippet']
        }
        unread_emails.append(email_data)

    return unread_emails

def mark_as_read(credentials, email_id: str):
    service = build('gmail', 'v1', credentials=credentials)
    service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()


def fetch_thread_messages(credentials, thread_id: str) -> List[Dict[str, str]]:
    try:
        service = build('gmail', 'v1', credentials=credentials)
        thread = service.users().threads().get(userId='me', id=thread_id).execute()

        messages = []

        for message in thread['messages']:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = {header['name']: header['value'] for header in msg['payload']['headers']}

            if 'parts' in msg['payload']:
                body = msg['payload']['parts'][0]['body']
            else:
                body = msg['payload']['body']

            if 'data' in body:
                body_data = base64.urlsafe_b64decode(body['data'].encode('ASCII')).decode('utf-8')
            else:
                body_data = ''
            message_dict = {
                'id': msg['id'],
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'subject': headers.get('Subject', ''),
                'date': headers.get('Date', ''),
                'body': body_data
            }

            messages.append(message_dict)

        return messages

    except Exception as e:
        print(f"An error occurred: {e}")
        return []