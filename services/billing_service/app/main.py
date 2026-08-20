from fastapi import FastAPI
from .database import engine
from .models import Base
from contextlib import asynccontextmanager
from .rabbitmq import connect_rabbitmq,consume_orders
import asyncio
Base.metadata.create_all(bind=engine)
print(">>> Main.py Charche")
@asynccontextmanager
async def lifespan(app: FastAPI):

    print(">>> LIFESPAN START")

    connection, channel, queue = await connect_rabbitmq()

    task = asyncio.create_task(
        consume_orders(queue)
    )

    print(">>> CONSUMER TASK CREATED")

    yield

    print(">>> LIFESPAN SHUTDOWN")

    task.cancel()

    await connection.close()
app = FastAPI(
    title="Billing Service",
    description="Service de facturation",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
def root():
    return {
        "service": "billing-service",
        "status": "ok",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }

@app.get("/db-check")
def db_check():
    with engine.connect() as connection:
        return {
            "database":"connected"
        }