import mysql.connector
from datetime import datetime
import random
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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

# Angriffsmuster in die URL integrieren
def integrate_attack_in_url(original_url, attack_patterns):
    parsed_url = urlparse(original_url)
    query_params = parse_qs(parsed_url.query)

    # Dynamische Auswahl von Angriffsmustern und Parametern
    for attack_pattern in attack_patterns:
        if "=" in attack_pattern and not attack_pattern.startswith("GET"):
            key, value = attack_pattern.split("=", 1)
            query_params[key] = value
        elif "GET " in attack_pattern:
            attack_pattern = attack_pattern.replace("GET ", "")
            query_params[random.choice(["param", "action", "id"])] = attack_pattern
        else:
            query_params[random.choice(["malicious", "exploit", "test"])] = attack_pattern

    new_query = urlencode(query_params, doseq=True)
    parsed_url = parsed_url._replace(query=new_query)
    return urlunparse(parsed_url)

# Doppelte GET-Anfragen in der URL bereinigen
def clean_redundant_get_requests(url):
    parts = url.split(" ")
    cleaned_parts = []
    seen_get = False
    for part in parts:
        if part.startswith("GET"):
            if not seen_get:
                seen_get = True
                cleaned_parts.append(part)
        else:
            cleaned_parts.append(part)
    return " ".join(cleaned_parts)

# Log-Eintrag generieren (basiert auf Angriffsmuster und Log-Struktur)
def generate_malicious_log(base_row, attack_entries):
    attack_entries = [clean_attack_entry(entry) for entry in attack_entries]

    # Standardwerte setzen, falls Felder fehlen
    base_row = {
        'ip': base_row.get('ip', '-'),
        'user': base_row.get('user', '-'),
        'timestamp': base_row.get('timestamp', datetime.now()),
        'method': base_row.get('method', random.choice(['GET', 'POST', 'DELETE'])),
        'url': base_row.get('url', '/'),
        'http_version': base_row.get('http_version', 'HTTP/1.1'),
        'status': base_row.get('status', 200),
        'size': base_row.get('size', 617),
        'referrer': base_row.get('referrer', 'https://example.com'),
        'user_agent': base_row.get('user_agent', random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'curl/7.68.0',
            'wget/1.20.3 (linux-gnu)',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]))
    }

    # Angriffsmuster in die URL einfügen
    new_url = integrate_attack_in_url(base_row['url'], attack_entries)
    new_url = clean_redundant_get_requests(new_url)

    timestamp = base_row['timestamp'].strftime("%d/%b/%Y:%H:%M:%S +0000")
    log_entry = (
        f"{base_row['ip']} - {base_row['user']} [{timestamp}] \"{base_row['method']} {new_url} {base_row['http_version']}\" "
        f"{base_row['status']} {base_row['size']} \"{base_row['referrer']}\" \"{base_row['user_agent']}\""
    )

    return log_entry

# Wahrscheinlichkeitsfunktion für Angriffs-Logs
def should_generate_attack_log(attack_probability=0.1):
    return random.random() < attack_probability

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
        if should_generate_attack_log(attack_probability=0.2):
            attack_type = random.choice(list(attack_patterns.keys()))
            attack_entries = random.sample(attack_patterns[attack_type], k=random.randint(1, 3))

            log_entry = generate_malicious_log(base_row, attack_entries)
        else:
            log_entry = generate_malicious_log(base_row, [])

        malicious_logs.append(log_entry)

    # In Datei speichern
    with open(log_file, "w", encoding="utf-8") as file:
        file.write("\n".join(malicious_logs))
    print(f"[INFO] {len(malicious_logs)} böse Logs wurden in '{log_file}' gespeichert.")

if __name__ == "__main__":
    # Anzahl der zu generierenden bösen Logs
    entry_count = 50
    generate_malicious_logs(entry_count=entry_count)
