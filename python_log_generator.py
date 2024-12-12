# File: python_log_generator.py

import random
import datetime

# Konfiguration der Wahrscheinlichkeiten für jeden Eintragstyp
entry_probabilities = {
    "200_OK": 0.85,  # Erfolgreiche Anfragen
    "301_Redirect": 0.05,  # Weiterleitungen
    "404_Not_Found": 0.05,  # Nicht gefundene Ressourcen
    "403_Forbidden": 0.02,  # Zugriff verweigert
    "500_Internal_Error": 0.01,  # Serverfehler
    "502_Bad_Gateway": 0.01,  # Fehler bei Upstream-Verbindung
    "504_Timeout": 0.01  # Zeitüberschreitung
}

# User-Agents aus externer Datei laden
def load_user_agents(file_path):
    with open(file_path, "r") as file:
        return [line.strip() for line in file if line.strip()]

# Pfade/Seiten/Dateien aus externer Datei laden
def load_paths(file_path):
    with open(file_path, "r") as file:
        return [line.strip() for line in file if line.strip()]

# Zufällige IPv4- und IPv6-Adressen generieren
def random_ipv4():
    return ".".join(str(random.randint(0, 255)) for _ in range(4))

def random_ipv6():
    return ":".join(
        f"{random.randint(0, 65535):x}" for _ in range(8)
    )

# Log-Eintrag generieren
def generate_log_entry(user_agents, paths):
    # Wähle zufälligen Log-Typ basierend auf Wahrscheinlichkeiten
    log_type = random.choices(
        list(entry_probabilities.keys()),
        list(entry_probabilities.values())
    )[0]

    # IP-Adresse zufällig auswählen
    ip = random.choice([random_ipv4(), random_ipv6()])

    # Benutzername (meistens "-" für keinen Benutzer)
    user = "-"

    # Zeitstempel
    timestamp = datetime.datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")

    # Anfrage basierend auf Log-Typ
    path = random.choice(paths)
    if log_type == "200_OK":
        request = f"GET {path} HTTP/1.1"
        status = 200
    elif log_type == "301_Redirect":
        request = f"GET {path} HTTP/1.1"
        status = 301
    elif log_type == "404_Not_Found":
        request = f"GET {path} HTTP/1.1"
        status = 404
    elif log_type == "403_Forbidden":
        request = f"GET {path} HTTP/1.1"
        status = 403
    elif log_type == "500_Internal_Error":
        request = f"GET {path} HTTP/1.1"
        status = 500
    elif log_type == "502_Bad_Gateway":
        request = f"GET {path} HTTP/1.1"
        status = 502
    elif log_type == "504_Timeout":
        request = f"GET {path} HTTP/1.1"
        status = 504

    # Größe der Antwort (zufällig, abhängig vom Typ)
    body_bytes_sent = random.randint(0, 5000) if status == 200 else 0

    # Referer (meistens "-")
    referer = random.choice(["-"])

    # User-Agent
    user_agent = random.choice(user_agents)

    # Log-Eintrag formatieren
    log_entry = (
        f"{ip} - {user} [{timestamp}] \"{request}\" {status} {body_bytes_sent} \"{referer}\" \"{user_agent}\""
    )
    return log_entry

# Anzahl der Log-Einträge generieren
def generate_logs(num_entries, user_agents, paths):
    logs = [generate_log_entry(user_agents, paths) for _ in range(num_entries)]
    return logs

# Beispiel: 100 Log-Einträge generieren und ausgeben
if __name__ == "__main__":
    user_agents = load_user_agents("user_agents.txt")
    paths = load_paths("paths.txt")
    log_entries = generate_logs(100, user_agents, paths)
    for log in log_entries:
        print(log)
