# File: mysql_log_generator.py

import mysql.connector
from datetime import datetime

# MySQL-Datenbankkonfiguration
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""  # Falls nötig, Passwort hinzufügen
DB_NAME = "log_generator"

# Standardkonfiguration für die Anzahl der Einträge und Filter
DEFAULT_ENTRY_COUNT = 100
DEFAULT_ID_RANGE = (1, 1000)  # Standardmäßiger ID-Bereich
DEFAULT_TIME_SPAN = None  # Kein Zeitfilter standardmäßig

# Verbindung zur MySQL-Datenbank herstellen
def connect_to_db():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print("[INFO] Datenbankverbindung erfolgreich hergestellt.")
        return conn
    except mysql.connector.Error as err:
        print(f"[ERROR] Fehler bei der Verbindung zur Datenbank: {err}")
        raise SystemExit

# Daten aus der MySQL-Datenbank abrufen
def fetch_data_from_db(query):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

# Log-Einträge generieren
def generate_access_log_entry(row):
    timestamp = row['timestamp'].strftime("%d/%b/%Y:%H:%M:%S +0000")
    log_entry = (
        f"{row['ip']} - {row.get('user', '-')} [{timestamp}] \"{row['method']} {row['url']} {row['http_version']}\" "
        f"{row['status']} {row['size']} \"{row['referrer']}\" \"{row['user_agent']}\""
    )
    return log_entry

def generate_error_log_entry(row):
    timestamp = row['timestamp'].strftime("%Y/%m/%d %H:%M:%S")
    log_entry = (
        f"{timestamp} [error] {row['module']}: *{row['pid']} {row['message']}, client: {row['client']}, "
        f"server: {row['server']}, request: \"{row['request']}\", host: \"{row['host']}\""
    )
    return log_entry

def generate_myfiles_log_entry(row):
    timestamp = row['timestamp'].strftime("%d/%b/%Y:%H:%M:%S +0000")
    log_entry = (
        f"{row['ip']} - {row['user']} [{timestamp}] \"{row['method']} {row['url']} {row['http_version']}\" "
        f"{row['status']} {row['size']} \"{row['referrer']}\" \"{row['user_agent']}\""
    )
    return log_entry

# Logs generieren und in Dateien speichern
def generate_logs(entry_count=DEFAULT_ENTRY_COUNT, id_range=DEFAULT_ID_RANGE, time_span=DEFAULT_TIME_SPAN):
    # Queries für verschiedene Logtypen
    queries = {
        "access": f"SELECT * FROM access_logs WHERE id BETWEEN {id_range[0]} AND {id_range[1]} ",
        "error": f"SELECT * FROM error_logs WHERE id BETWEEN {id_range[0]} AND {id_range[1]} ",
        "myfiles": f"SELECT * FROM myfiles_logs WHERE id BETWEEN {id_range[0]} AND {id_range[1]} "
    }

    if time_span:
        start_time, end_time = time_span
        for log_type in queries:
            queries[log_type] += f"AND timestamp BETWEEN '{start_time}' AND '{end_time}'"

    log_files = {
        "access": "access" + datetime.now().strftime("%Y%m%d%H%M%S") + ".log",
        "error": "error" + datetime.now().strftime("%Y%m%d%H%M%S") + ".log",
        "myfiles": "myfiles" + datetime.now().strftime("%Y%m%d%H%M%S") + ".log"
    }

    for log_type, query in queries.items():
        print(f"[INFO] Generiere {log_type}-Logs...")
        data = fetch_data_from_db(query)
        
        # Prüfen, ob genügend Einträge vorhanden sind
        available_entries = len(data)
        if available_entries < entry_count:
            print(f"[WARNING] Für {log_type}-Logs sind nur {available_entries} Einträge verfügbar. "
                  f"Angefordert: {entry_count}.")
            entry_count = available_entries  # Nur so viele Einträge generieren, wie verfügbar sind

        log_entries = []
        for i, row in enumerate(data[:entry_count]):  # Nur bis zur verfügbaren Anzahl iterieren
            if log_type == "access":
                log_entries.append(generate_access_log_entry(row))
            elif log_type == "error":
                log_entries.append(generate_error_log_entry(row))
            elif log_type == "myfiles":
                log_entries.append(generate_myfiles_log_entry(row))

        # Logs in Datei speichern
        with open(log_files[log_type], "w", encoding="utf-8") as file:
            file.write("\n".join(log_entries))
        print(f"[INFO] {len(log_entries)} {log_type}-Logs wurden in '{log_files[log_type]}' gespeichert.")


if __name__ == "__main__":
    # Benutzerdefinierte Einstellungen
    entry_count = 100  # Anzahl der Einträge
    id_range = (1, 500)  # ID-Bereich (1 bis 500)
    time_span = ("2022-01-01 00:00:00", "2024-12-31 23:59:59")  # Zeitspanne (optional)

    generate_logs(entry_count=entry_count, id_range=id_range, time_span=time_span)
