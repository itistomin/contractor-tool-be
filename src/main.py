from dotenv import load_dotenv
from fastapi import FastAPI

from database.connection import query


load_dotenv()


app = FastAPI()


@app.get("/health")
async def get_health():
    return {"status": "ok"}
