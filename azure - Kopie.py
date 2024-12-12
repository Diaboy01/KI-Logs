# File: azure.py

import os
import logging
import requests

# Logging konfigurieren
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

# Azure OpenAI-Konfigurationsvariablen
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = "2023-05-15"
GPT_DEPLOYMENT_NAME = "gpt-4o"

# Anfrage an Azure OpenAI senden
def send_chat_request(user_input, page_context=None):
    if not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT:
        logging.error("API-Schlüssel oder Endpoint fehlen.")
        return None

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY
    }

    payload = {
        "messages": [
            {"role": "system", "content": f"Der Kontext der Seite ist: {page_context or 'Kein Kontext'}"},
            {"role": "user", "content": user_input}
        ]
    }

    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{GPT_DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_API_VERSION}"

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler bei der Anfrage: {e}")
        return None

# Hauptablauf
if __name__ == "__main__":
    logging.info("Chatbot gestartet.")
    user_input = input("Was möchtest du fragen? ")

    # Optionaler Seitenkontext (kann auch aus einer Datei oder Webanfrage kommen)
    page_context = "Hier könnte ein Webseitenkontext stehen."

    if user_input:
        response = send_chat_request(user_input, page_context)
        if response:
            logging.info(f"Antwort: {response}")
            print(f"Antwort: {response}")
        else:
            logging.error("Keine Antwort erhalten.")
    
