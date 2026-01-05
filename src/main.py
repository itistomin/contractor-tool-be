from dotenv import load_dotenv
from fastapi import FastAPI

from views import (
    authorization_router,
)


load_dotenv()


app = FastAPI()


@app.get("/health")
async def get_health():
    return {"status": "ok"}


app.include_router(authorization_router)
