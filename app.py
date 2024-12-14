# File: app.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import joblib
import pandas as pd

# FastAPI App erstellen
app = FastAPI()
favicon_path = 'favicon.ico'

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

# Starte FastAPI über Uvicorn (optional direkt im Skript)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # http://127.0.0.1:8000/
    print("API gestartet unter: http://127.0.0.1:8000/")
