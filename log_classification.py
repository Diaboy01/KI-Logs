# file: log_classification.py

import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib
import re

# Pfade zu den Dateien
normal_logs_path = "myfiles-access_anon.log"
bad_logs_path = "malicious_myfiles_20241214143634.log"

# Variablen zur Steuerung der Verarbeitung
lines_to_read = 100000  # Anzahl der Zeilen, die pro Datei gelesen werden

# Funktion zur Vorverarbeitung der Logs
def preprocess_logs(logs):
    logs["log"] = logs["log"].apply(lambda x: re.sub(r'\d+\.\d+\.\d+\.\d+', 'IP', x))  # IP-Adressen maskieren
    logs["log"] = logs["log"].apply(lambda x: re.sub(r'\[[^\]]+\]', 'TIMESTAMP', x))  # Zeitstempel maskieren
    logs["log"] = logs["log"].apply(lambda x: re.sub(r'"([^"]+)"', r'"\1"', x))  # Request unberührt lassen
    logs["log"] = logs["log"].apply(lambda x: re.sub(r'[^\w\s/?.=&]', '', x))  # Entferne irrelevante Sonderzeichen
    logs["log"] = logs["log"].apply(lambda x: x.lower())  # Normalisierung
    return logs

# Funktion zum Lesen einer Log-Datei
def read_logs(file_path, num_lines, label):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        lines = [line.strip() for _, line in zip(range(num_lines), file)]
    return pd.DataFrame({"log": lines, "label": label})

# Lesen der Logs
print("[INFO] Lesen der Log-Dateien...")
normal_logs = read_logs(normal_logs_path, lines_to_read, 0)
bad_logs = read_logs(bad_logs_path, lines_to_read, 1)

# Kombinieren der Daten
print("[INFO] Kombinieren der Daten...")
data = pd.concat([normal_logs, bad_logs]).sample(frac=1).reset_index(drop=True)

# Vorverarbeitung der Logs
print("[INFO] Vorverarbeitung der Logs...")
data = preprocess_logs(data)

# Feature-Extraktion mit TF-IDF
print("[INFO] Extrahieren der Merkmale mit TF-IDF...")
vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(2, 3), stop_words='english', max_df=0.95, min_df=5)
X = vectorizer.fit_transform(data["log"])
y = data["label"]

# Daten in Trainings- und Testdaten aufteilen
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Modelltraining
print("[INFO] Training des Modells...")
model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
model.fit(X_train, y_train)

# Modellbewertung
print("[INFO] Evaluierung des Modells...")
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")

# Cross-Validation
print("[INFO] Cross-Validation des Modells...")
scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
print(f"Cross-Validation Accuracy: {scores.mean():.4f} ± {scores.std():.4f}")

# Modell speichern
print("[INFO] Speichern des Modells und des Vektorisierers...")
joblib.dump(model, "log_classifier.pkl")
joblib.dump(vectorizer, "log_vectorizer.pkl")

print("[INFO] Fertig. Modell und Vektorisierer wurden gespeichert.")
