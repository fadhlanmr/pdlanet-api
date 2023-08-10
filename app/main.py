from fastapi import FastAPI
from .routers import crawler, ryan

app = FastAPI()
app.include_router(crawler.router)
app.include_router(ryan.router)

@app.get("/")
def read_root():
    return {"Pdlanet-API": "access api.pdlanet.com/docs for swagger"}