# File: anomaly_log_ai.py

import os
from anomaly_detection import process_log_file, extract_features
from azure_log_generator import send_chat_request

# Funktion zur Interaktion mit dem Benutzer, wenn eine Anomalie gefunden wird
def handle_anomalies(df, anomalies, log_type):
    if anomalies.empty:
        print("Keine Anomalien gefunden.")
        return

    for index, anomaly in anomalies.iterrows():
        print(f"Anomalie im {log_type}-Log gefunden:")
        print(anomaly)

        user_input = input("Möchten Sie diese Anomalie analysieren lassen? (ja/nein): ").strip().lower()
        if user_input == "ja":
            # Bereite die Daten für das Sprachmodell vor
            anomaly_json = anomaly.to_json()
            prompt = f"Analysieren Sie die folgende Anomalie aus einem {log_type}-Log und geben Sie eine Einschätzung, was zu tun ist:\n{anomaly_json}"
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

        log_type = "access" if "access" in log_file else "error" if "error" in log_file else "myfiles"

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
        handle_anomalies(df, isolation_anomalies, log_type)

    print("Analyse abgeschlossen.")
