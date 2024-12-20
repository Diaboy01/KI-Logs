# File: app.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import joblib
import pandas as pd
import requests
import os
import mysql.connector
import random
import datetime
import google.generativeai as genai
import logging
from dotenv import load_dotenv

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("gemini_logs.log"),  # Logs werden in Datei geschrieben
        logging.StreamHandler(),                # Logs erscheinen im Terminal
    ],
)

# .env-Datei laden 
load_dotenv()

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
log_classifier_model = joblib.load("log_classifier.pkl")
tfidf_vectorizer = joblib.load("log_vectorizer.pkl")

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
        # Eingehende Logs empfangen
        logs = request.logs
        logging.info(f"[INFO] Eingehende Log-Daten zur Vorhersage: {logs}")

        # Logs in DataFrame umwandeln
        logs_df = pd.DataFrame({"log": logs})
        logging.debug(f"[DEBUG] DataFrame erstellt: {logs_df.head()}")

        # Transformation der Logs
        logs_tfidf = tfidf_vectorizer.transform(logs_df["log"])
        logging.debug(f"[DEBUG] TF-IDF Transformation abgeschlossen.")

        # Vorhersagen durchführen
        predictions = log_classifier_model.predict_proba(logs_tfidf)
        logging.debug(f"[DEBUG] Vorhersagen abgeschlossen: {predictions}")

        # Ergebnisse zusammenstellen
        results = [
            {"log": log, "normal": round(prob[0], 2), "malicious": round(prob[1], 2)}
            for log, prob in zip(logs, predictions)
        ]
        logging.info(f"[INFO] Vorhersageergebnisse: {results}")

        return {"results": results}
    except Exception as e:
        logging.error(f"[ERROR] Fehler bei der Vorhersage: {str(e)}")
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
        logging.error(f"[ERROR] Azure OpenAI Fehler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Azure OpenAI Fehler: {e}")

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "log_generator"

# Verbindung zur Datenbank
def connect_to_db():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Zufälligen Wert aus einer Tabelle abrufen
@app.get("/random/{attribute}")
async def random_value(attribute: str):
    try:
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)

        if attribute == "ip":
            cursor.execute("SELECT ip FROM myfiles_logs ORDER BY RAND() LIMIT 1")
            result = cursor.fetchone()
            return {"value": result["ip"] if result else "Keine IP gefunden"}
        elif attribute == "user":
            cursor.execute("SELECT user FROM myfiles_logs ORDER BY RAND() LIMIT 1")
            result = cursor.fetchone()
            return {"value": result["user"] if result else "Kein Benutzer gefunden"}
        elif attribute == "timestamp":
            timestamp = datetime.datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")
            return {"value": timestamp}
        elif attribute == "url":
            cursor.execute("SELECT url FROM myfiles_logs ORDER BY RAND() LIMIT 1")
            result = cursor.fetchone()
            return {"value": result["url"] if result else "Keine URL gefunden"}
        elif attribute == "method":
            method = random.choice(["GET", "POST", "DELETE"])
            return {"value": method}
        else:
            return {"value": "Unbekanntes Attribut"}
    except Exception as e:
        logging.error(f"[ERROR] Datenbankfehler: {str(e)}")
        return {"error": str(e)}
    finally:
        conn.close()

# Google Gemini-API-Schlüssel konfigurieren
gemini_api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)

# Generative Modellkonfiguration
gemini_generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1024,
    "response_mime_type": "text/plain",
}
gemini_safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    safety_settings=gemini_safety_settings,
    generation_config=gemini_generation_config,
)

# Chat-Session erstellen
gemini_chat_session = gemini_model.start_chat(history=[])

class GeminiChatRequest(BaseModel):
    message: str

@app.post("/gemini-chat")
async def gemini_chat(request: GeminiChatRequest):
    """
    API für Gemini-Chat
    """
    try:
        user_message = request.message
        logging.info(f"Empfangene Nachricht vom Benutzer: {user_message}")

        # Gemini-Anfrage senden
        response = gemini_chat_session.send_message({"role": "user", "parts": [{"text": user_message}]})
        gemini_response = response.text

        logging.info(f"Antwort von Gemini: {gemini_response}")
        return {"response": gemini_response}
    except Exception as e:
        logging.error(f"[ERROR] Fehler bei der Verarbeitung durch Gemini: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gemini-Chat Fehler: {str(e)}")


# Starte FastAPI über Uvicorn (optional direkt im Skript)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    print("API gestartet unter: http://127.0.0.1:8000/")
