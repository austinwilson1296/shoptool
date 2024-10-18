import os
from dotenv import load_dotenv
from pathlib import Path
import requests

load_dotenv(Path('/home/austin/workspace/work/ShopTool12Refactor/.env'))
key = os.getenv('MAILGUNAPIKEY')
print(key)
if not key:
    raise ValueError("Mailgun API key not found in environment variables")

def send_simple_message():
    try:
        response = requests.post(
            "https://api.mailgun.net/v3/sandbox9b922c342a86463c91a4c9425fb18bc5.mailgun.org/messages",
            auth=("api", key),
            data={
                "from": "mail.brrshoptool.com",
                "to": ["austinlax20@gmail.com"],
                "subject": "Hello",
                "text": "Testing some Mailgun awesomeness!",
            },
        )
        response.raise_for_status()  # Raise an error for bad responses
        print("Email sent successfully")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send email: {e}")

send_simple_message()

