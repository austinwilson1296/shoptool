import os
from dotenv import load_dotenv
from pathlib import Path
import requests

load_dotenv(Path("/home/austin/workspace/work/ShopTool12Refactor/.env"))
key = os.getenv("MAILGUNSENDINGKEY")
print(key)
if not key:
    raise ValueError("Mailgun API key not found in environment variables")


def send_simple_message():
    try:
        response = requests.post(
            "https://api.mailgun.net/v3/brrshoptool/messages",
            auth=("api", key),
            data={
                "from": "mail.brrshoptool.com",
                "to": ["awilson@shopashley.com"],
                "subject": "Hello",
                "text": "Testing some Mailgun awesomeness!",
            },
        )
        response.raise_for_status()  # Raise an error for bad responses
        print("Email sent successfully")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send email: {e}")


send_simple_message()
