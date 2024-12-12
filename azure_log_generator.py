# File: azure_log_generator.py

import os
import requests
import re
import random
import time
import json
import mysql.connector
from collections import Counter

# Einfache Logging-Funktion
def log(message, level="INFO"):
    levels = {"INFO": "[INFO]", "WARNING": "[WARNING]", "ERROR": "[ERROR]"}
    prefix = levels.get(level, "[INFO]")
    print(f"{prefix} {message}")

# Azure OpenAI-Konfigurationsvariablen
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = "2023-05-15"
GPT_DEPLOYMENT_NAME = "gpt-4o"

# MySQL-Datenbankkonfiguration
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "log_generator"

# Konfigurierbare Wartezeiten
SHORT_DELAY = 1  # Sekunden zwischen erfolgreichen Anfragen
LONG_DELAY = 30  # Sekunden bei einem Fehler, bevor erneut versucht wird

# Gewünschte Anzahl der Einträge
DESIRED_NUM_ENTRIES = 100

# Wiederholte Einträge verfolgen
REPEATED_ENTRIES_FILE = "repeated_entries.json"

# Verbindung zur MySQL-Datenbank herstellen
def connect_to_db():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            database=DB_NAME
        )
        log("Datenbankverbindung erfolgreich hergestellt.", "INFO")
        return conn
    except mysql.connector.Error as err:
        log(f"Fehler bei der Verbindung zur Datenbank: {err}", "ERROR")
        raise SystemExit

# Tabelle erstellen, falls nicht vorhanden
def create_table_if_not_exists(table_name):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            entry TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    log(f"Tabelle '{table_name}' erstellt oder existiert bereits.", "INFO")

# Einträge aus der Datenbank laden
def load_existing_entries(table_name):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT entry FROM {table_name}")
    results = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    log(f"{len(results)} Einträge aus Tabelle '{table_name}' geladen.", "INFO")
    return results

# Neue Einträge in die Datenbank einfügen
def save_entries_to_db(table_name, entries):
    conn = connect_to_db()
    cursor = conn.cursor()
    successful_inserts = 0
    for entry in entries:
        try:
            cursor.execute(f"INSERT IGNORE INTO {table_name} (entry) VALUES (%s)", (entry,))
            if cursor.rowcount > 0:
                log(f"Eintrag erfolgreich hinzugefügt: {entry}", "INFO")
                successful_inserts += 1
            else:
                log(f"Eintrag bereits vorhanden: {entry}", "WARNING")
        except mysql.connector.Error as err:
            log(f"Fehler beim Einfügen von Eintrag '{entry}': {err}", "ERROR")
    conn.commit()
    cursor.close()
    conn.close()
    log(f"{successful_inserts} von {len(entries)} neuen Einträgen in Tabelle '{table_name}' gespeichert.", "INFO")

# Einträge in JSON-Datei speichern
def save_entries_to_json(file_path, entries):
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(list(entries), file, ensure_ascii=False, indent=4)
        log(f"{len(entries)} Einträge erfolgreich in {file_path} gespeichert.", "INFO")
    except Exception as e:
        log(f"Fehler beim Schreiben der Datei {file_path}: {e}", "ERROR")

# Wiederholte Einträge speichern
def save_repeated_entries(entries):
    try:
        with open(REPEATED_ENTRIES_FILE, "w", encoding="utf-8") as file:
            json.dump(entries, file, ensure_ascii=False, indent=4)
        log(f"{len(entries)} wiederholte Einträge in {REPEATED_ENTRIES_FILE} gespeichert.", "INFO")
    except Exception as e:
        log(f"Fehler beim Speichern der wiederholten Einträge: {e}", "ERROR")

# Überprüfen, ob der Eintrag gültig ist
def validate_entry(entry, format_regex):
    is_valid = bool(re.match(format_regex, entry))
    log(f"Validierung für '{entry}': {'gültig' if is_valid else 'ungültig'}", "INFO")
    return is_valid

# Anfrage an Azure OpenAI senden
def send_chat_request(prompt):
    if not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT:
        log("API-Schlüssel oder Endpoint fehlen.", "ERROR")
        raise SystemExit

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY
    }

    payload = {
        "messages": [
            {"role": "system", "content": "Bitte generiere einzigartige Einträge im angegebenen Format."},
            {"role": "user", "content": prompt}
        ]
    }

    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{GPT_DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_API_VERSION}"

    while True:
        try:
            log(f"Sende Anfrage an Azure OpenAI mit Prompt: {prompt}", "INFO")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            log(f"Antwort erhalten: {data['choices'][0]['message']['content']}", "INFO")
            time.sleep(SHORT_DELAY)  # Kurze Pause nach einer erfolgreichen Anfrage
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            log(f"Fehler bei der Anfrage: {e}", "ERROR")
            log("Warte auf erneute Anfrage...", "INFO")
            time.sleep(LONG_DELAY)  # Lange Pause bei einem Fehler

# Einträge generieren
def generate_entries(table_name, json_file_path, prompt_template, format_regex):
    # Lade bestehende Daten aus der Datenbank und JSON-Datei
    existing_db_entries = set(load_existing_entries(table_name))
    try:
        with open(json_file_path, "r", encoding="utf-8") as file:
            existing_json_entries = set(json.load(file))
    except (FileNotFoundError, json.JSONDecodeError):
        existing_json_entries = set()
        log(f"Keine oder ungültige Datei gefunden. Neue Datei wird erstellt: {json_file_path}", "WARNING")

    entries = existing_db_entries.union(existing_json_entries)
    repeated_entries = Counter()

    while len(entries) < DESIRED_NUM_ENTRIES:
        # Prompt erstellen
        sampled_entries = random.sample(list(existing_db_entries), min(len(existing_db_entries), 10)) if existing_db_entries else []
        sampled_text = "\n".join(sampled_entries)
        # Falls Einträge in repeatet_entries vorhanden sind
        repated_entries = [entry for entry, count in repeated_entries.items() if count > 0]
        repeated_text = "\n".join(repated_entries)
        if repeated_text:
            prompt = (prompt_template + "\nBereits vorhandene Einträge:\n" + sampled_text +
                      "\nVermeide solche Einträge:\n" + repeated_text +
                      "\nBitte generiere komplett andere, zufällige Einträge.").format(existing_count=len(entries))
        else:
            prompt = (prompt_template + "\nBereits vorhandene Einträge:\n" + sampled_text +
                        "\nBitte generiere andere, zufällige Einträge.").format(existing_count=len(entries))

        log(f"Sende Anfrage mit Prompt: {prompt}", "INFO")
        response = send_chat_request(prompt)

        if response:
            for line in response.splitlines():
                line = line.strip()
                line = re.sub(r"^\d+\.\s*", "", line)  # Entferne führende Zahlen und Punkte
                if validate_entry(line, format_regex):
                    if line not in entries:
                        entries.add(line)
                        save_entries_to_db(table_name, [line])  # Speichere sofort in der Datenbank
                        save_entries_to_json(json_file_path, entries)  # Speichere sofort in JSON
                    else:
                        log(f"Doppelter Eintrag entdeckt: {line}", "WARNING")
                        repeated_entries[line] += 1
                else:
                    log(f"Ungültiges Format: {line}", "WARNING")
        else:
            log("Keine Antwort erhalten.", "ERROR")

    save_repeated_entries(repeated_entries)
    log(f"{DESIRED_NUM_ENTRIES} Einträge erfolgreich generiert.", "INFO")

# Hauptablauf
if __name__ == "__main__":
    log("Automatische Eintragsgenerierung gestartet.", "INFO")

    print("Bitte wählen Sie aus, was generiert werden soll:")
    print("1: User-Agents")
    print("2: Paths")
    print("3: (Coming Soon)")

    choice = input("Ihre Auswahl (1-3): ").strip()

    if choice == "1":
        # Parameter für User-Agents
        table_name = "user_agents"
        json_file_path = "user_agents.json"
        user_agents_prompt = "Generiere User-Agent-Einträge im Format: 'Browsername/Browserversion (URL)':"
        user_agents_regex = r"^[^\s]+/[^\s]+ \([^)]+\)$"

        # Tabelle erstellen, falls nicht vorhanden
        create_table_if_not_exists(table_name)

        # Generiere User-Agents
        generate_entries(table_name, json_file_path, user_agents_prompt, user_agents_regex)

    elif choice == "2":
        # Parameter für Pfade
        table_name = "paths"
        json_file_path = "paths.json"
        paths_prompt = "Generiere Website Pfade (ohne Umlaute) im Format: '/beispiel-pfad':"
        paths_regex = r"^/[-a-zA-Z0-9_/]+$"

        # Tabelle erstellen, falls nicht vorhanden
        create_table_if_not_exists(table_name)

        # Generiere Pfade
        generate_entries(table_name, json_file_path, paths_prompt, paths_regex)

    elif choice == "3":
        log("Funktion 'Coming Soon' ist noch nicht verfügbar.", "INFO")

    else:
        log("Ungültige Auswahl. Das Programm wird beendet.", "ERROR")

    log("Eintragsgenerierung abgeschlossen.", "INFO")
