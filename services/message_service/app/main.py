from app.mailer import send_mail
from fastapi import BackgroundTasks, FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import MailBody

app = FastAPI()
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "catalogue.localhost",
        "orders.localhost",
        "accounts.localhost",
        "message.localhost",
        "localhost",
        "127.0.0.1"
    ]
)

@app.get("/")
def ready_root():
    return {"message":"ready!!!"}

@app.post("/send-email")
def schedule_mail(req: MailBody, tasks:BackgroundTasks): # type: ignore
    data = req.dict()
    tasks.add_task(send_mail,data)
    return {"status":200,"message":"email has been scheduled"}