import logging
from dotenv import load_dotenv
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError('The OPENAI_API_KEY environment variable is not set')

current_dir = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(current_dir, 'credentials')
TOKEN_FILE = os.path.join(CREDENTIALS_PATH, 'token.json')
CREDENTIALS_FILE = os.path.join(CREDENTIALS_PATH, 'credentials.json')

if not os.path.exists(TOKEN_FILE):
    logging.error(f"Token file not found: {TOKEN_FILE}")
if not os.path.exists(CREDENTIALS_FILE):
    logging.error(f"Credentials file not found: {CREDENTIALS_FILE}")

logging.info(f"Using token file: {TOKEN_FILE}")
logging.info(f"Using credentials file: {CREDENTIALS_FILE}")
print(CREDENTIALS_PATH)