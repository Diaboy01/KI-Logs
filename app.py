# File: app.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import joblib
import pandas as pd
import requests
import os


# Azure OpenAI-Konfigurationsvariablen
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = "2023-05-15"
GPT_DEPLOYMENT_NAME = "gpt-4o"

# FastAPI App erstellen
app = FastAPI()
favicon_path = 'favicon.ico'

class AzureRequest(BaseModel):
    log: str

# CORS-Konfiguration hinzufügen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Passe hier die erlaubten Domains an
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modell und Vektorisierer laden
model = joblib.load("log_classifier.pkl")
vectorizer = joblib.load("log_vectorizer.pkl")

# API-Klassen
class LogRequest(BaseModel):
    logs: list

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)

@app.get("/")
async def serve_html():
    """
    Liefert die HTML-Seite
    """
    try:
        return FileResponse("index.html")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="HTML-Datei nicht gefunden.")

@app.post("/predict-text")
async def predict_text(request: LogRequest):
    """
    Vorhersage für eingegebene Log-Daten
    """
    try:
        logs = request.logs
        logs_df = pd.DataFrame({"log": logs})
        logs_tfidf = vectorizer.transform(logs_df["log"])
        predictions = model.predict_proba(logs_tfidf)

        results = [
            {"log": log, "normal": round(prob[0], 2), "malicious": round(prob[1], 2)}
            for log, prob in zip(logs, predictions)
        ]
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Verarbeitung: {e}")
    

@app.post("/azure-ai")
async def azure_ai(request: AzureRequest):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY,
    }

    payload = {
        "messages": [
            {"role": "system", "content": "Analysiere den folgenden Log-Eintrag und liefere eine Bewertung."},
            {"role": "user", "content": request.log},
        ]
    }

    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{GPT_DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_API_VERSION}"

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return {"response": data["choices"][0]["message"]["content"]}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Azure OpenAI Fehler: {e}")


# Starte FastAPI über Uvicorn (optional direkt im Skript)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # http://127.0.0.1:8000/
    print("API gestartet unter: http://127.0.0.1:8000/")
