# File: python_log_generator.py

import random
import datetime
import json

# Wahrscheinlichkeitstabelle für Statuscodes
entry_probabilities = {
    "200_OK": 0.85,
    "301_Redirect": 0.05,
    "404_Not_Found": 0.05,
    "403_Forbidden": 0.02,
    "500_Internal_Error": 0.01,
    "502_Bad_Gateway": 0.01,
    "504_Timeout": 0.01
}

# IPv4- und IPv6-Adressen generieren
def random_ipv4():
    return ".".join(str(random.randint(0, 255)) for _ in range(4))

def random_ipv6():
    return ":".join(f"{random.randint(0, 65535):x}" for _ in range(8))

# Log-Eintrag generieren
def generate_log_entry(user_agents, paths):
    # IP-Adresse (entweder IPv4 oder IPv6)
    ip_address = random.choice([random_ipv4(), random_ipv6()])

    # Benutzer und Zeitstempel
    user = "-"
    timestamp = datetime.datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")

    # Zufälliger Statuscode und zugehöriger Pfad
    log_type = random.choices(list(entry_probabilities.keys()), weights=entry_probabilities.values())[0]
    path = random.choice(paths)
    
    # HTTP-Methode und Version
    request_line = f"GET {path} HTTP/1.1"
    
    # Statuscode und Body-Größe
    if log_type == "200_OK":
        status_code = 200
        body_bytes_sent = random.randint(100, 5000)
    elif log_type == "301_Redirect":
        status_code = 301
        body_bytes_sent = 0
    elif log_type == "404_Not_Found":
        status_code = 404
        body_bytes_sent = 0
    elif log_type == "403_Forbidden":
        status_code = 403
        body_bytes_sent = 0
    elif log_type == "500_Internal_Error":
        status_code = 500
        body_bytes_sent = 0
    elif log_type == "502_Bad_Gateway":
        status_code = 502
        body_bytes_sent = 0
    elif log_type == "504_Timeout":
        status_code = 504
        body_bytes_sent = 0

    # User-Agent
    user_agent = random.choice(user_agents)

    # Zusammenstellen des Log-Eintrags
    log_entry = (
        f'{ip_address} - {user} [{timestamp}] "{request_line}" {status_code} {body_bytes_sent} "-" "{user_agent}"'
    )
    return log_entry

# Logs generieren
def generate_logs(num_logs, user_agents_file, paths_file):
    # User-Agents und Pfade laden
    with open(user_agents_file, "r", encoding="utf-8") as ua_file:
        user_agents = json.load(ua_file)

    with open(paths_file, "r", encoding="utf-8") as paths_file:
        paths = json.load(paths_file)

    # Logs erstellen
    logs = [generate_log_entry(user_agents, paths) for _ in range(num_logs)]
    return logs

# Hauptprogramm
if __name__ == "__main__":
    user_agents_file = "user_agents.json"
    paths_file = "paths.json"
    num_logs = 100  # Anzahl der Logs

    # Logs generieren und in Datei speichern
    logs = generate_logs(num_logs, user_agents_file, paths_file)
    with open("access.log", "w", encoding="utf-8") as log_file:
        log_file.write("\n".join(logs))

    print(f"{num_logs} Logs wurden erfolgreich in 'access.log' gespeichert.")
