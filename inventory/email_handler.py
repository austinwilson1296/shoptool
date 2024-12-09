import os
from dotenv import load_dotenv
from pathlib import Path
import requests
from datetime import datetime

load_dotenv(Path("/home/austin/workspace/work/ShopTool12Refactor/.env"))
key = os.getenv("MAILGUNAPIKEY")
if not key:
    raise ValueError("Mailgun API key not found in environment variables")


def send_supply_request(requstor,request):
    now = datetime.now()
    formatted_date = now.strftime("%B %d, %Y")
    try:
        response = requests.post(
            "https://api.mailgun.net/v3/mg.brrshoptool.com/messages",
            auth=("api", key),
            data={
                "from": "postmaster@mg.brrshoptool.com",
                "to": ["awilson@shopashley.com"],
                "subject": f"Supply Request for {formatted_date} for {requstor}",
                "text": request,
            },
        )
        response.raise_for_status()  # Raise an error for bad responses
        print("Email sent successfully")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send email: {e}")


send_supply_request("Austin Wilson","Id like to order some tools")


