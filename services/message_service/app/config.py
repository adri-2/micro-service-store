import os 
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel
from typing import List


HOST= os.environ.get("MAIL_HOST")
PORT =os.environ.get("MAIL_PORT",465)
USERNAME =os.environ.get("MAIL_USERNAME")
PASSWORD =os.environ.get("MAIL_PASSWORD")
class MailBody(BaseModel):
    to: List[str]
    subject: str
    body: str