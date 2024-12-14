import mysql.connector
from datetime import datetime
import random
import re

# MySQL-Datenbankkonfiguration
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""  # Falls nötig, Passwort hinzufügen
DB_NAME = "log_generator"

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

# Daten aus einer Tabelle abrufen
def fetch_data_from_table(table_name):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM {table_name}")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

# Angriffsmuster bereinigen
def clean_attack_entry(entry):
    return re.sub(r"^\d+\.\s*|`$", "", entry).strip()

# Log-Eintrag generieren (basiert auf Angriffsmuster und Log-Struktur)
def generate_malicious_log(base_row, attack_entry):
    attack_entry = clean_attack_entry(attack_entry)

    # Standardwerte setzen, falls Felder fehlen
    base_row = {
        'ip': base_row.get('ip', '-'),
        'user': base_row.get('user', '-'),
        'timestamp': base_row.get('timestamp', datetime.now()),
        'method': base_row.get('method', 'GET'),
        'url': base_row.get('url', '/'),
        'http_version': base_row.get('http_version', 'HTTP/1.1'),
        'status': base_row.get('status', 200),
        'size': base_row.get('size', 617),
        'referrer': base_row.get('referrer', '-'),
        'user_agent': base_row.get('user_agent', 'Mozilla/5.0')
    }

    # Angriffsmuster in die URL einfügen
    new_url = base_row['url'] + ("?" if "?" not in base_row['url'] else "&") + attack_entry

    timestamp = base_row['timestamp'].strftime("%d/%b/%Y:%H:%M:%S +0000")
    log_entry = (
        f"{base_row['ip']} - {base_row['user']} [{timestamp}] \"{base_row['method']} {new_url} {base_row['http_version']}\" "
        f"{base_row['status']} {base_row['size']} \"{base_row['referrer']}\" \"{base_row['user_agent']}\""
    )

    return log_entry

# Böse Logs generieren und in Dateien speichern
def generate_malicious_logs(entry_count=50):
    # Angriffsmuster abrufen
    attack_tables = {
        "sql_injection": "sql_injection_logs",
        "xss": "xss_logs",
        "command_injection": "command_injection_logs",
        "directory_traversal": "directory_traversal_logs",
        "http_exploits": "http_method_exploit_logs"
    }

    attack_patterns = {}
    for attack_type, table_name in attack_tables.items():
        attack_patterns[attack_type] = [clean_attack_entry(row['entry']) for row in fetch_data_from_table(table_name)]

    # Basis-Logs abrufen
    base_logs = fetch_data_from_table("myfiles_logs")

    # Datei für Logs vorbereiten
    log_file = f"malicious_myfiles_{datetime.now().strftime('%Y%m%d%H%M%S')}.log"

    # Böse Logs generieren
    malicious_logs = []

    for _ in range(entry_count):
        base_row = random.choice(base_logs)
        attack_type = random.choice(list(attack_patterns.keys()))
        attack_entry = random.choice(attack_patterns[attack_type])

        log_entry = generate_malicious_log(base_row, attack_entry)
        malicious_logs.append(log_entry)

    # In Datei speichern
    with open(log_file, "w", encoding="utf-8") as file:
        file.write("\n".join(malicious_logs))
    print(f"[INFO] {len(malicious_logs)} böse Logs wurden in '{log_file}' gespeichert.")

if __name__ == "__main__":
    # Anzahl der zu generierenden bösen Logs
    entry_count = 50
    generate_malicious_logs(entry_count=entry_count)