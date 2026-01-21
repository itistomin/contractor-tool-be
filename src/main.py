from dotenv import load_dotenv
from fastapi import FastAPI

from views import (
    authorization_router,
    contractors_router,
    contracts_router,
)


load_dotenv()


app = FastAPI()


@app.get("/api/health")
async def get_health():
    return {"status": "ok"}


app.include_router(authorization_router, prefix="/api")
app.include_router(contractors_router, prefix="/api")
app.include_router(contracts_router, prefix="/api")