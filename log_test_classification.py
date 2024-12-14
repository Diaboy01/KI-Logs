# File: log_test_classification.py

import joblib

# Funktion zur Vorhersage für neue Logs
def classify_logs(new_logs_path, model_path="log_classifier.pkl", vectorizer_path="log_vectorizer.pkl", num_lines=100):
    # Modell und Vektorisierer laden
    model = joblib.load(model_path)
    vectorizer = joblib.load(vectorizer_path)

    # Neue Logs lesen
    print("[INFO] Lesen der neuen Logs...")
    with open(new_logs_path, "r", encoding="utf-8", errors="ignore") as file:
        new_logs = [line.strip() for _, line in zip(range(num_lines), file)]

    # Vorhersage durchführen
    print("[INFO] Vorhersage...")
    new_logs_tfidf = vectorizer.transform(new_logs)
    predictions = model.predict_proba(new_logs_tfidf)

    # Ergebnisse ausgeben
    for log, probs in zip(new_logs, predictions):
        print(f"Log: {log}\nBöse: {probs[1]:.2f}, Normal: {probs[0]:.2f}\n")

# Beispiel zur Vorhersage für neue Logs
classify_logs("test.log", num_lines=50)
