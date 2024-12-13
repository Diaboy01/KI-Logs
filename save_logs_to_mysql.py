# File: save_logs_to_mysql.py

import os
import re
import mysql.connector
import pandas as pd
from datetime import datetime

def log(message, level="INFO"):
    levels = {"INFO": "[INFO]", "WARNING": "[WARNING]", "ERROR": "[ERROR]"}
    prefix = levels.get(level, "[INFO]")
    print(f"{prefix} {message}")

# MySQL-Datenbankkonfiguration
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "log_generator"
TABLE_NAME = "access_logs"

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
def create_table_if_not_exists():
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ip VARCHAR(255),
            timestamp DATETIME,
            request VARCHAR(255),
            status_code INT,
            user_agent TEXT,
            referrer TEXT,
            log_file VARCHAR(255)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    log(f"Tabelle '{TABLE_NAME}' erstellt oder existiert bereits.", "INFO")

# Funktion zur Verarbeitung einer Log-Datei
def process_log_file(log_file):
    data = []
    log_pattern = re.compile(
        r'(?P<ip>\S+)\s+-\s+-\s+\[(?P<timestamp>[^\]]+)]\s+"(?P<method>\S+)\s+(?P<url>\S+)\s+(?P<http_version>HTTP/\d\.\d)"\s+(?P<status>\d+)\s+(?P<size>\d+|-)\s+"(?P<referrer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
    )

    with open(log_file, "r") as file:
        for line in file:
            match = log_pattern.match(line)
            if match:
                log_entry = match.groupdict()

                # Zeitstempel in das richtige Format umwandeln
                log_entry["timestamp"] = datetime.strptime(
                    log_entry["timestamp"], "%d/%b/%Y:%H:%M:%S %z"
                )

                # Falls 'size' "-" ist, als None speichern
                log_entry["size"] = None if log_entry["size"] == "-" else int(log_entry["size"])

                # Log-Dateiname hinzufügen
                log_entry["log_file"] = os.path.basename(log_file)

                data.append(log_entry)
    return pd.DataFrame(data)

# Daten in die MySQL-Datenbank einfügen
def save_to_database(df):
    conn = connect_to_db()
    cursor = conn.cursor()

    for i, row in df.iterrows():
        try:
            cursor.execute(f"""
                INSERT INTO {TABLE_NAME} 
                (ip, timestamp, request, status_code, user_agent, referrer, log_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                row["ip"],
                row["timestamp"],
                f"{row['method']} {row['url']}",
                int(row["status"]),
                row["user_agent"],
                row["referrer"],
                row["log_file"]
            ))
        except mysql.connector.Error as err:
            log(f"Fehler beim Einfügen von Daten: {err}", "ERROR")
            raise SystemExit
    conn.commit()
    cursor.close()
    conn.close()
    log(f"{len(df)} Datensätze in die Datenbank eingefügt.", "INFO")

# Hauptablauf
def main():
    log_folder = "share_logs"
    all_files = [os.path.join(log_folder, f) for f in os.listdir(log_folder) if os.path.isfile(os.path.join(log_folder, f))]
    if not all_files:
        log("Keine Log-Dateien im Verzeichnis gefunden.", "ERROR")
        raise SystemExit

    create_table_if_not_exists()

    total_files = len(all_files)
    for idx, log_file in enumerate(all_files, start=1):
        log(f"Verarbeite Datei {idx}/{total_files}: {log_file}", "INFO")
        df = process_log_file(log_file)
        if df.empty:
            log(f"Datei {log_file} enthält keine gültigen Daten.", "WARNING")
            continue
        save_to_database(df)
        log(f"Fortschritt: {idx}/{total_files} Dateien verarbeitet.", "INFO")

if __name__ == "__main__":
    main()
