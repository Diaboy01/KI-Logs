# File: anomaly_log_ai.py

import os
from anomaly_detection import process_log_file, extract_features
from azure_log_generator import send_chat_request

# Funktion zur Interaktion mit dem Benutzer, wenn eine Anomalie gefunden wird
def handle_anomalies(df, anomalies, log_type, log_file):
    if anomalies.empty:
        print("Keine Anomalien gefunden.")
        return

    # Gefährlichkeitsbewertung für jede Anomalie hinzufügen
    def calculate_severity(anomaly):
        severity = 1  # Minimale Gefährlichkeit als Standardwert

        # Beispielkriterien für Gefährlichkeitsbewertung
        if anomaly.get("is_suspicious_path", 0) == 1:
            severity += 4  # Verdächtiger Pfad
        if anomaly.get("time_diff", 0) > 300:
            severity += 2  # Lange Zeitdifferenz
        if anomaly.get("ip_count", 0) < 2:
            severity += 1  # IP-Adresse nur einmal verwendet (niedrige Priorität)
        if anomaly.get("status_code_encoded", -1) in [4, 5]:  # 4xx oder 5xx Fehlercodes
            severity += 3  # Fehlerhafte Statuscodes
        if anomaly.get("user_agent_length", 0) > 200:
            severity += 2  # Ungewöhnlich langer User-Agent-String

        return severity

    # Gefährlichkeitsbewertung berechnen und Anomalien sortieren
    anomalies["severity"] = anomalies.apply(calculate_severity, axis=1)
    sorted_anomalies = anomalies.sort_values(by="severity", ascending=False)

    for index, anomaly in sorted_anomalies.iterrows():
        print(f"Anomalie im {log_type}-Log gefunden (Datei: {log_file}, Zeile: {index + 1}):")
        print(anomaly)

        # Gefährlichkeitsbewertung anzeigen
        print(f"Gefährlichkeitsbewertung: {anomaly['severity']} von 10")

        # Zusätzliche Diagnose der Anomalie
        issues = []
        if anomaly.get("is_suspicious_path", 0) == 1:
            issues.append("Verdächtiger Pfad möglicherweise")
        if anomaly.get("time_diff", 0) > 300:
            issues.append("Ungewöhnlich lange Zeitdifferenz zwischen Anfragen")
        if anomaly.get("ip_count", 0) < 2:
            issues.append("IP-Adresse wurde nur einmal verwendet, möglicherweise ungewöhnlich")
        if anomaly.get("status_code_encoded", -1) in [4, 5]:
            issues.append("Fehlerhafte HTTP-Statuscodes (4xx oder 5xx)")
        if anomaly.get("user_agent_length", 0) > 200:
            issues.append("Ungewöhnlich langer User-Agent-String")
        if not issues:
            issues.append("Keine spezifischen Probleme identifiziert, aber als Anomalie markiert")

        print("Mögliche Probleme bei dieser Anomalie:")
        for issue in issues:
            print(f"- {issue}")

        user_input = input("Möchten Sie diese Anomalie analysieren lassen? (ja/nein): ").strip().lower()
        if user_input == "ja":
            # Bereite die Daten für das Sprachmodell vor
            anomaly_json = anomaly.to_json()
            prompt = f"Analysiere den folgenden {log_type} Log Eintrag und gebe eine Einschätzung auf Deutsch, was zu tun ist: \n{anomaly_json}"
            print("Sende Anfrage an das Sprachmodell...")

            response = send_chat_request(prompt)
            print("Antwort des Sprachmodells:")
            print(response)
        else:
            print("Analyse für diese Anomalie übersprungen.")

# Hauptfunktion
if __name__ == "__main__":
    log_folder = "share_logs"
    all_files = [os.path.join(log_folder, f) for f in os.listdir(log_folder) if os.path.isfile(os.path.join(log_folder, f))]

    for log_file in all_files:
        # Falls Name der Datei mit einem Punkt beginnt, überspringen
        if os.path.basename(log_file).startswith("."):
            print(f"Überspringe Datei: {log_file}")
            continue

        if "myfiles" in os.path.basename(log_file):
            log_type = "myfiles"
        elif "access" in os.path.basename(log_file):
            log_type = "access"
        elif "error" in os.path.basename(log_file):
            log_type = "error"
        else:
            log_type = "unknown"

        if log_type == "unknown":
            print(f"Warnung: Der Datei-Typ für {log_file} konnte nicht bestimmt werden. Überspringe diese Datei.")
            continue

        print(f"Verarbeite Datei: {log_file} als Typ: {log_type}")

        # Log-Datei einlesen
        df = process_log_file(log_file, log_type)

        if df.empty:
            print(f"Datei {log_file} ist leer oder enthält ungültige Daten.")
            continue

        # Feature-Engineering
        df = extract_features(df, log_type)

        if log_type == "error":
            features = df[["pid", "message_length"]]
        else:
            features = df[["ip_count", "status_code_encoded", "user_agent_length", "time_diff", "is_suspicious_path"]]

        # Unsupervised Learning mit Isolation Forest
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)

        iso_forest = IsolationForest(contamination=0.05, random_state=42)
        df["anomaly_score"] = iso_forest.fit_predict(features_scaled)
        isolation_anomalies = df[df["anomaly_score"] == -1]  # -1 bedeutet Anomalie

        # Anomalien behandeln
        handle_anomalies(df, isolation_anomalies, log_type, log_file)

    print("Analyse abgeschlossen.")
