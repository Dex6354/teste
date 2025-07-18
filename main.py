from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Olá, mundo! Esta é uma aplicação de teste."}
