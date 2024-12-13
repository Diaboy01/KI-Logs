# File: anomaly_detection.py

import os
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from tensorflow.keras.models import Sequential  # type: ignore
from tensorflow.keras.layers import Dense  # type: ignore
from sklearn.model_selection import train_test_split

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

# Ordner mit Log-Dateien
log_folder = "share_logs"
all_files = [os.path.join(log_folder, f) for f in os.listdir(log_folder) if os.path.isfile(os.path.join(log_folder, f))]

# Ergebnisse speichern
for log_file in all_files:
    print(f"Verarbeite Datei: {log_file}")

    # Schritt 1: Log-Datei einlesen
    df = process_log_file(log_file)

    if df.empty:
        print(f"Datei {log_file} ist leer oder enthält ungültige Daten.")
        continue

    # Schritt 2: Feature-Engineering
    df["ip_count"] = df["ip"].map(df["ip"].value_counts())
    df["status_code"] = df["status_code"].astype(str)
    status_encoder = LabelEncoder()
    df["status_code_encoded"] = status_encoder.fit_transform(df["status_code"])
    df["user_agent_length"] = df["user_agent"].str.len()

    # Features extrahieren
    features = df[["ip_count", "status_code_encoded", "user_agent_length"]]

    # Schritt 3: Unsupervised Learning mit Isolation Forest
    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    df["anomaly_score"] = iso_forest.fit_predict(features)
    isolation_anomalies = df[df["anomaly_score"] == -1]  # -1 bedeutet Anomalie

    print(f"Anzahl der Anomalien in {log_file} (Isolation Forest): {len(isolation_anomalies)}")

    # Schritt 4: Autoencoder-Analyse
    scaler = MinMaxScaler()
    features_scaled = scaler.fit_transform(features)

    # Autoencoder definieren
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

    # Ergebnisse speichern (inklusive Zeilennummern)
    isolation_anomalies.to_csv(f"anomalies_isolation_forest_{os.path.basename(log_file)}.csv", index=False, columns=["line_num", "ip", "timestamp", "request", "status_code", "user_agent"])
    autoencoder_anomalies.to_csv(f"anomalies_autoencoder_{os.path.basename(log_file)}.csv", index=False, columns=["line_num", "ip", "timestamp", "request", "status_code", "user_agent"])

print("Analyse abgeschlossen.")
