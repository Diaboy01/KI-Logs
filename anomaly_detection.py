# File: anomaly_detection.py

import os
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import LabelEncoder, StandardScaler
from tensorflow.keras.models import Sequential  # type: ignore
from tensorflow.keras.layers import Dense  # type: ignore
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns
import re

# Log-Parsing-Funktionen
def parse_access_log(line):
    pattern = re.compile(
        r'(?P<ip>\S+) - - \[(?P<timestamp>[^\]]+)] \"(?P<method>\S+) (?P<url>\S+) (?P<http_version>HTTP/\d\.\d)\" (?P<status_code>\d+) (?P<size>\d+|-) \"(?P<referrer>[^\"]*)\" \"(?P<user_agent>[^\"]*)\"'
    )
    match = pattern.match(line)
    if match:
        data = match.groupdict()
        data["timestamp"] = pd.to_datetime(data["timestamp"], format="%d/%b/%Y:%H:%M:%S %z", errors="coerce")
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
        data["timestamp"] = pd.to_datetime(data["timestamp"], format="%Y/%m/%d %H:%M:%S", errors="coerce")
        return data
    return None

def parse_myfiles_log(line):
    pattern = re.compile(
        r'(?P<ip>\S+) - (?P<user>\S+) \[(?P<timestamp>[^\]]+)] \"(?P<method>\S+) (?P<url>\S+) (?P<http_version>HTTP/\d\.\d)\" (?P<status_code>\d+) (?P<size>\d+|-) \"(?P<referrer>[^\"]*)\" \"(?P<user_agent>[^\"]*)\"'
    )
    match = pattern.match(line)
    if match:
        data = match.groupdict()
        data["timestamp"] = pd.to_datetime(data["timestamp"], format="%d/%b/%Y:%H:%M:%S %z", errors="coerce")
        data["size"] = None if data["size"] == "-" else int(data["size"])
        return data
    return None

# Funktion zur Verarbeitung einer einzelnen Log-Datei
def process_log_file(log_file, log_type):
    data = []
    with open(log_file, "r") as file:
        for line in file:
            if log_type == "access":
                entry = parse_access_log(line)
            elif log_type == "error":
                entry = parse_error_log(line)
            elif log_type == "myfiles":
                entry = parse_myfiles_log(line)
            else:
                entry = None

            if entry:
                entry["log_file"] = os.path.basename(log_file)
                data.append(entry)
    return pd.DataFrame(data)

# Funktion zum Extrahieren von zusätzlichen Features
def extract_features(df, log_type):
    if log_type == "access" or log_type == "myfiles":
        df["ip_count"] = df["ip"].map(df["ip"].value_counts())
        df["user_agent_length"] = df["user_agent"].str.len()
        df["time_diff"] = df["timestamp"].diff().dt.total_seconds().fillna(0)
        df["is_suspicious_path"] = df["url"].str.contains(r"(../|.env|.git/config)", regex=True).astype(int)
        df["status_code"] = df["status_code"].astype(str)

        # Label-Encoding für kategoriale Features
        status_encoder = LabelEncoder()
        df["status_code_encoded"] = status_encoder.fit_transform(df["status_code"])

    elif log_type == "error":
        df["pid"] = df["pid"].astype(int)
        df["message_length"] = df["message"].str.len()

    return df

# Ordner mit Log-Dateien
log_folder = "share_logs"
all_files = [os.path.join(log_folder, f) for f in os.listdir(log_folder) if os.path.isfile(os.path.join(log_folder, f))]

# Ergebnisse speichern
for log_file in all_files:
    # Falls Name der Datei mit einem Punkt beginnt, überspringen
    if os.path.basename(log_file).startswith("."):
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
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    df["anomaly_score"] = iso_forest.fit_predict(features_scaled)
    isolation_anomalies = df[df["anomaly_score"] == -1]  # -1 bedeutet Anomalie

    print(f"Anzahl der Anomalien in {log_file} (Isolation Forest): {len(isolation_anomalies)}")

    # Unsupervised Learning mit DBSCAN
    dbscan = DBSCAN(eps=0.5, min_samples=5)
    df["dbscan_cluster"] = dbscan.fit_predict(features_scaled)
    dbscan_anomalies = df[df["dbscan_cluster"] == -1]

    print(f"Anzahl der Anomalien in {log_file} (DBSCAN): {len(dbscan_anomalies)}")

    # Autoencoder-Analyse
    autoencoder = Sequential([
        Dense(16, activation='relu', input_dim=features_scaled.shape[1]),
        Dense(8, activation='relu'),
        Dense(16, activation='relu'),
        Dense(features_scaled.shape[1], activation='sigmoid')
    ])

    autoencoder.compile(optimizer='adam', loss='mse')

    # Train/Test-Split
    X_train, X_test = train_test_split(features_scaled, test_size=0.2, random_state=42)
    autoencoder.fit(X_train, X_train, epochs=50, batch_size=32, validation_data=(X_test, X_test))

    # Rekonstruktionsfehler berechnen
    reconstruction_error = autoencoder.predict(features_scaled) - features_scaled
    reconstruction_error = (reconstruction_error ** 2).mean(axis=1)

    # Anomalien bestimmen
    threshold = np.percentile(reconstruction_error, 95)  # 95. Perzentil als Schwelle
    autoencoder_anomalies = df[reconstruction_error > threshold]

    print(f"Anzahl der Anomalien in {log_file} (Autoencoder): {len(autoencoder_anomalies)}")

    # Ergebnisse visualisieren und speichern
    log_file_name = os.path.splitext(os.path.basename(log_file))[0]
    output_folder = os.path.join("results", log_file_name)

    # Erstelle den Ordner, falls er noch nicht existiert
    os.makedirs(output_folder, exist_ok=True)

    # Rekonstruktionsfehler visualisieren
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(reconstruction_error)), reconstruction_error, label="Rekonstruktionsfehler")
    plt.axhline(y=threshold, color='r', linestyle='--', label="Threshold")
    plt.xlabel("Zeile im Log")
    plt.ylabel("Rekonstruktionsfehler")
    plt.title(f"Anomalien in {log_file} (Autoencoder)")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_folder, f"{log_file_name}_reconstruction_errors.png"))
    plt.close()

    # Heatmap der IP-Aktivitäten (nur für Access- und MyFiles-Logs)
    if log_type != "error":
        ip_activity = df.groupby("ip")["timestamp"].count().sort_values(ascending=False)
        plt.figure(figsize=(12, 8))
        sns.barplot(x=ip_activity.index[:20], y=ip_activity.values[:20], palette="coolwarm")
        plt.xticks(rotation=90)
        plt.title(f"Top 20 IP-Adressen nach Anzahl der Anfragen in {log_file}")
        plt.xlabel("IP-Adresse")
        plt.ylabel("Anfragen")
        plt.grid(axis='y')
        plt.savefig(os.path.join(output_folder, f"{log_file_name}_ip_activity.png"))
        plt.close()

    # Anomalien spezifisch visualisieren
    if log_type == "error":
        # Scatterplot für Error Logs
        plt.figure(figsize=(10, 6))
        plt.scatter(df["pid"], df["message_length"], c=(df["anomaly_score"] == -1), cmap="coolwarm", alpha=0.7)
        plt.title(f"Anomalien in {log_file} (Error Logs)")
        plt.xlabel("PID")
        plt.ylabel("Länge der Fehlermeldung")
        plt.grid(True)
        plt.savefig(os.path.join(output_folder, f"{log_file_name}_error_anomalies.png"))
        plt.close()

        # Fehlerhäufigkeit nach Zeit darstellen
        plt.figure(figsize=(12, 6))
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
        time_anomalies = df[df["anomaly_score"] == -1].groupby(df["timestamp"].dt.hour).size()
        plt.bar(time_anomalies.index, time_anomalies.values, color="orange", alpha=0.7)
        plt.title(f"Häufigkeit der Anomalien nach Stunden in {log_file}")
        plt.xlabel("Stunde des Tages")
        plt.ylabel("Anzahl der Anomalien")
        plt.grid(axis='y')
        plt.savefig(os.path.join(output_folder, f"{log_file_name}_time_error_anomalies.png"))
        plt.close()

    else:
        # Scatterplot für Access/MyFiles Logs
        plt.figure(figsize=(10, 6))
        plt.scatter(df["time_diff"], df["status_code_encoded"], c=(df["anomaly_score"] == -1), cmap="coolwarm", alpha=0.7)
        plt.title(f"Anomalien in {log_file} (Access/MyFiles Logs)")
        plt.xlabel("Zeitunterschied zwischen Anfragen (Sekunden)")
        plt.ylabel("Status-Code (kodiert)")
        plt.grid(True)
        plt.savefig(os.path.join(output_folder, f"{log_file_name}_access_anomalies.png"))
        plt.close()

    print(f"Visualisierungen gespeichert in: {output_folder}")

    isolation_anomalies.to_json(os.path.join(output_folder, "anomalies_isolation_forest.json"), orient="records", lines=True)
    dbscan_anomalies.to_json(os.path.join(output_folder, "anomalies_dbscan.json"), orient="records", lines=True)
    autoencoder_anomalies.to_json(os.path.join(output_folder, "anomalies_autoencoder.json"), orient="records", lines=True)

print("Analyse abgeschlossen.")
