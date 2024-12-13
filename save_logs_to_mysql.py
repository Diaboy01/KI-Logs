# File: save_logs_to_mysql.py

import os
import re
import mysql.connector
import pandas as pd

def log(message, level="INFO"):
    levels = {"INFO": "[INFO]", "WARNING": "[WARNING]", "ERROR": "[ERROR]"}
    prefix = levels.get(level, "[INFO]")
    print(f"{prefix} {message}")

# MySQL-Datenbankkonfiguration
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "log_generator"
TABLE_NAME = "log_components"  # Standard-Tabelle, wird dynamisch angepasst

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
            ip VARCHAR(255),
            timestamp DATETIME,
            request VARCHAR(255),
            status_code INT,
            user_agent TEXT,
            user VARCHAR(255) NULL,
            referrer TEXT NULL,
            message TEXT NULL
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    log(f"Tabelle '{table_name}' erstellt oder existiert bereits.", "INFO")

# Spalte hinzufügen, falls sie fehlt
def add_missing_columns(table_name, column_definitions):
    conn = connect_to_db()
    cursor = conn.cursor()
    for column_name, column_definition in column_definitions.items():
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
            log(f"Spalte '{column_name}' zur Tabelle '{table_name}' hinzugefügt.", "INFO")
        except mysql.connector.Error as err:
            if "Duplicate column name" in str(err):
                log(f"Spalte '{column_name}' existiert bereits in Tabelle '{table_name}'.", "INFO")
            else:
                log(f"Fehler beim Hinzufügen der Spalte '{column_name}': {err}", "ERROR")
                raise SystemExit
    conn.commit()
    cursor.close()
    conn.close()

# Funktion zur Verarbeitung einer einzelnen Log-Datei
def process_log_file(log_file, log_type):
    data = []
    with open(log_file, "r") as file:
        for line_num, line in enumerate(file, start=1):
            if log_type == "access":
                match = re.match(r'(?P<ip>\S+) - - \[(?P<timestamp>[^\]]+)] \"(?P<method>\S+) (?P<url>\S+) (?P<http_version>\S+)\" (?P<status>\d+) (?P<size>\d+) \"(?P<referrer>[^\"]*)\" \"(?P<user_agent>[^\"]*)\"', line)
                if match:
                    data.append(match.groupdict())
            elif log_type == "error":
                match = re.match(r'\[(?P<timestamp>[^\]]+)] \[(?P<module>[^\]]+)] \[(?P<severity>[^\]]+)] \[pid (?P<pid>\d+)] \[client (?P<client>[^\]]+)] (?P<message>.+)', line)
                if match:
                    data.append(match.groupdict())
            elif log_type == "myfiles-access":
                match = re.match(r'(?P<ip>\S+) - (?P<user>\S+) \[(?P<timestamp>[^\]]+)] \"(?P<method>\S+) (?P<url>\S+) (?P<http_version>\S+)\" (?P<status>\d+) (?P<size>\d+) \"(?P<referrer>[^\"]*)\" \"(?P<user_agent>[^\"]*)\"', line)
                if match:
                    data.append(match.groupdict())
    return pd.DataFrame(data)

# Daten in die MySQL-Datenbank einfügen
def save_to_database(df, table_name):
    conn = connect_to_db()
    cursor = conn.cursor()

    for _, row in df.iterrows():
        try:
            cursor.execute(f"""
                INSERT INTO {table_name} (ip, timestamp, request, status_code, user_agent, user, referrer, message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row.get("ip"),
                row.get("timestamp"),
                row.get("method", "") + " " + row.get("url", "") if "method" in row else None,
                row.get("status"),
                row.get("user_agent"),
                row.get("user"),
                row.get("referrer"),
                row.get("message")
            ))
        except mysql.connector.Error as err:
            log(f"Fehler beim Einfügen von Daten: {err}", "ERROR")
            raise SystemExit

    conn.commit()
    cursor.close()
    conn.close()
    log(f"{len(df)} Datensätze in die Datenbank eingefügt.", "INFO")

# Funktion zur Ermittlung des Log-Typs basierend auf dem Dateinamen
def determine_log_type_and_table(log_file):
    if "access" in log_file:
        return "access", "access_logs"
    elif "error" in log_file:
        return "error", "error_logs"
    elif "myfiles-access" in log_file:
        return "myfiles-access", "myfiles_access_logs"
    else:
        return "unknown", "log_components"

# Hauptablauf
def main():
    log_folder = "share_logs"
    all_files = [os.path.join(log_folder, f) for f in os.listdir(log_folder) if os.path.isfile(os.path.join(log_folder, f))]

    if not all_files:
        log("Keine Log-Dateien im Verzeichnis gefunden.", "ERROR")
        raise SystemExit

    for log_file in all_files:
        log_type, table_name = determine_log_type_and_table(log_file)

        if log_type == "unknown":
            log(f"Unbekannter Log-Typ für Datei: {log_file}", "WARNING")
            continue

        create_table_if_not_exists(table_name)

        column_definitions = {
            "user": "VARCHAR(255) NULL",
            "referrer": "TEXT NULL",
            "message": "TEXT NULL"
        }
        add_missing_columns(table_name, column_definitions)

        log(f"Verarbeite Datei: {log_file} als Typ: {log_type}", "INFO")
        df = process_log_file(log_file, log_type)

        if df.empty:
            log(f"Datei {log_file} ist leer oder enthält ungültige Daten.", "WARNING")
            continue

        save_to_database(df, table_name)

if __name__ == "__main__":
    main()
