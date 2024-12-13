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

# Funktion zur Verarbeitung einer einzelnen Log-Datei
def process_log_file(log_file):
    data = []
    with open(log_file, "r") as file:
        for line_num, line in enumerate(file, start=1):
            parts = line.strip().split(" ")
            if len(parts) > 9:  # Sicherstellen, dass die Zeile gültig ist
                try:
                    data.append({
                        "line_num": line_num,
                        "ip": parts[0],
                        "timestamp": parts[3].strip("[]"),
                        "request": parts[5] + " " + parts[6],
                        "status_code": int(parts[8]),
                        "user_agent": " ".join(parts[11:])
                    })
                except ValueError:
                    pass  # Fehlerhafte Zeilen überspringen
    return pd.DataFrame(data)

# Funktion zum Extrahieren von zusätzlichen Features
def extract_features(df):
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d/%b/%Y:%H:%M:%S", errors="coerce")
    df["ip_count"] = df["ip"].map(df["ip"].value_counts())
    df["status_code"] = df["status_code"].astype(str)
    df["user_agent_length"] = df["user_agent"].str.len()
    df["time_diff"] = df["timestamp"].diff().dt.total_seconds().fillna(0)
    df["is_suspicious_path"] = df["request"].str.contains(r"(../|.env|.git/config)", regex=True).astype(int)

    # Label-Encoding für kategoriale Features
    status_encoder = LabelEncoder()
    df["status_code_encoded"] = status_encoder.fit_transform(df["status_code"])

    return df

# Ordner mit Log-Dateien
log_folder = "share_logs"
all_files = [os.path.join(log_folder, f) for f in os.listdir(log_folder) if os.path.isfile(os.path.join(log_folder, f))]

# Ergebnisse speichern
for log_file in all_files:
    print(f"Verarbeite Datei: {log_file}")

    # Log-Datei einlesen
    df = process_log_file(log_file)

    if df.empty:
        print(f"Datei {log_file} ist leer oder enthält ungültige Daten.")
        continue

    # Feature-Engineering
    df = extract_features(df)

    # Features extrahieren
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
    plt.figure(figsize=(10, 6))
    plt.plot(df["line_num"], reconstruction_error, label="Rekonstruktionsfehler")
    plt.axhline(y=threshold, color='r', linestyle='--', label="Threshold")
    plt.xlabel("Zeile im Log")
    plt.ylabel("Rekonstruktionsfehler")
    plt.title(f"Anomalien in {log_file}")
    plt.legend()
    plt.savefig(os.path.join(output_folder, f"{log_file_name}_errors.png"))
    plt.close()

    # Heatmap der IP-Aktivitäten
    ip_activity = df.groupby("ip")["timestamp"].count().sort_values(ascending=False)
    plt.figure(figsize=(12, 8))
    sns.barplot(x=ip_activity.index, y=ip_activity.values, palette="coolwarm")
    plt.xticks(rotation=90)
    plt.title("Anfragen pro IP")
    plt.xlabel("IP-Adresse")
    plt.ylabel("Anzahl der Anfragen")
    plt.savefig(os.path.join(output_folder, f"{log_file_name}_ip_activity.png"))
    plt.close()

    # Anomalien im Zeitverlauf
    plt.figure(figsize=(12, 6))
    plt.scatter(df["timestamp"], reconstruction_error, c=(reconstruction_error > threshold), cmap="coolwarm", label="Anomalien")
    plt.axhline(y=threshold, color='r', linestyle='--', label="Threshold")
    plt.title("Anomalien im Zeitverlauf")
    plt.xlabel("Zeit")
    plt.ylabel("Rekonstruktionsfehler")
    plt.legend()
    plt.savefig(os.path.join(output_folder, f"{log_file_name}_time_anomalies.png"))
    plt.close()

    print(f"Visualisierungen gespeichert in: {output_folder}")

    isolation_anomalies.to_json(os.path.join(output_folder, "anomalies_isolation_forest.json"), orient="records", lines=True)
    dbscan_anomalies.to_json(os.path.join(output_folder, "anomalies_dbscan.json"), orient="records", lines=True)
    autoencoder_anomalies.to_json(os.path.join(output_folder, "anomalies_autoencoder.json"), orient="records", lines=True)

print("Analyse abgeschlossen.")

