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
def create_table_if_not_exists(table_name, fields):
    conn = connect_to_db()
    cursor = conn.cursor()

    columns = ", ".join([f"{field} {datatype}" for field, datatype in fields.items()])
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            {columns}
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    log(f"Tabelle '{table_name}' erstellt oder existiert bereits.", "INFO")

# Log-Parsing-Funktionen
def parse_access_log(line):
    pattern = re.compile(
        r'(?P<ip>\S+) - - \[(?P<timestamp>[^\]]+)] \"(?P<method>\S+) (?P<url>\S+) (?P<http_version>HTTP/\d\.\d)\" (?P<status>\d+) (?P<size>\d+|-) \"(?P<referrer>[^\"]*)\" \"(?P<user_agent>[^\"]*)\"'
    )
    match = pattern.match(line)
    if match:
        data = match.groupdict()
        data["timestamp"] = datetime.strptime(data["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
        data["size"] = None if data["size"] == "-" else int(data["size"])
        return data
    return None

def parse_error_log(line):
    pattern = re.compile(
        r'(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[(?P<severity>error)] (?P<module>[^:]+): \*(?P<pid>\d+) (?P<message>.+), client: (?P<client>[^,]+), server: (?P<server>[^,]+), request: \"(?P<request>[^\"]+)\", host: \"(?P<host>[^\"]+)\"'
    )
    match = pattern.match(line)
    if match:
        data = match.groupdict()
        data["timestamp"] = datetime.strptime(data["timestamp"], "%Y/%m/%d %H:%M:%S")
        return data
    return None

def parse_myfiles_log(line):
    pattern = re.compile(
        r'(?P<ip>\S+) - (?P<user>\S+) \[(?P<timestamp>[^\]]+)] \"(?P<method>\S+) (?P<url>\S+) (?P<http_version>HTTP/\d\.\d)\" (?P<status>\d+) (?P<size>\d+|-) \"(?P<referrer>[^\"]*)\" \"(?P<user_agent>[^\"]*)\"'
    )
    match = pattern.match(line)
    if match:
        data = match.groupdict()
        data["timestamp"] = datetime.strptime(data["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
        data["size"] = None if data["size"] == "-" else int(data["size"])
        return data
    return None

# Log-Datei verarbeiten
def process_log_file(log_file, log_type):
    data = []
    with open(log_file, "r") as file:
        for line in file:
            if log_type == "myfiles" and "myfiles" in log_file:
                entry = parse_myfiles_log(line)
            elif log_type == "error" and "error" in log_file:
                entry = parse_error_log(line)
            elif log_type == "access":
                entry = parse_access_log(line)
            else:
                entry = None

            if entry:
                entry["log_file"] = os.path.basename(log_file)
                data.append(entry)
    return pd.DataFrame(data)

# Daten in die MySQL-Datenbank einfügen
def save_to_database(df, table_name):
    conn = connect_to_db()
    cursor = conn.cursor()

    for _, row in df.iterrows():
        columns = ", ".join(row.keys())
        placeholders = ", ".join(["%s"] * len(row))
        values = tuple(row)

        try:
            cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values)
        except mysql.connector.Error as err:
            log(f"Fehler beim Einfügen von Daten: {err}", "ERROR")
            raise SystemExit

    conn.commit()
    cursor.close()
    conn.close()
    log(f"{len(df)} Datensätze in die Tabelle '{table_name}' eingefügt.", "INFO")

# Hauptablauf
def main():
    log_folder = "share_logs"
    log_definitions = {
        "access": {
            "table": "access_logs",
            "fields": {
                "ip": "VARCHAR(255)",
                "timestamp": "DATETIME",
                "method": "VARCHAR(10)",
                "url": "VARCHAR(255)",
                "http_version": "VARCHAR(10)",
                "status": "INT",
                "size": "INT",
                "referrer": "TEXT",
                "user_agent": "TEXT",
                "log_file": "VARCHAR(255)"
            }
        },
        "error": {
            "table": "error_logs",
            "fields": {
                "timestamp": "DATETIME",
                "severity": "VARCHAR(10)",
                "module": "VARCHAR(255)",
                "pid": "INT",
                "message": "TEXT",
                "client": "VARCHAR(255)",
                "server": "VARCHAR(255)",
                "request": "TEXT",
                "host": "VARCHAR(255)",
                "log_file": "VARCHAR(255)"
            }
        },
        "myfiles": {
            "table": "myfiles_logs",
            "fields": {
                "ip": "VARCHAR(255)",
                "user": "VARCHAR(255)",
                "timestamp": "DATETIME",
                "method": "VARCHAR(10)",
                "url": "VARCHAR(255)",
                "http_version": "VARCHAR(10)",
                "status": "INT",
                "size": "INT",
                "referrer": "TEXT",
                "user_agent": "TEXT",
                "log_file": "VARCHAR(255)"
            }
        }
    }

    all_files = [os.path.join(log_folder, f) for f in os.listdir(log_folder) if os.path.isfile(os.path.join(log_folder, f))]

    if not all_files:
        log("Keine Log-Dateien im Verzeichnis gefunden.", "ERROR")
        raise SystemExit

    for log_type, definition in log_definitions.items():
        create_table_if_not_exists(definition["table"], definition["fields"])

    total_files = len(all_files)
    for idx, log_file in enumerate(all_files, start=1):
        if "myfiles" in log_file:
            log_type = "myfiles"
        elif "error" in log_file:
            log_type = "error"
        else:
            log_type = "access"

        table_name = log_definitions[log_type]["table"]

        log(f"Verarbeite Datei {idx}/{total_files}: {log_file} als Typ: {log_type}", "INFO")
        df = process_log_file(log_file, log_type)

        if df.empty:
            log(f"Datei {log_file} enthält keine gültigen Daten.", "WARNING")
            continue

        save_to_database(df, table_name)
        log(f"Fortschritt: {idx}/{total_files} Dateien verarbeitet.", "INFO")

if __name__ == "__main__":
    main()
