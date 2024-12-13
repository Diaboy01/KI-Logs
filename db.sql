-- MySQL-Dump für die Log-Generator-Datenbank
CREATE DATABASE IF NOT EXISTS log_generator;

USE log_generator;

-- Tabelle für User-Agent-Einträge
CREATE TABLE IF NOT EXISTS user_agents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entry TEXT NOT NULL UNIQUE
);

-- Tabelle für Pfad-Einträge
CREATE TABLE IF NOT EXISTS paths (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entry TEXT NOT NULL UNIQUE
);

-- Tabelle für Access-Logs
CREATE TABLE IF NOT EXISTS access_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(255),
    timestamp DATETIME,
    request VARCHAR(255),
    status_code INT,
    user_agent TEXT,
    referrer TEXT NULL
);

-- Tabelle für Error-Logs
CREATE TABLE IF NOT EXISTS error_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME,
    module VARCHAR(255),
    severity VARCHAR(50),
    pid INT,
    client VARCHAR(255),
    message TEXT
);

-- Tabelle für MyFiles-Access-Logs
CREATE TABLE IF NOT EXISTS myfiles_access_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(255),
    user VARCHAR(255),
    timestamp DATETIME,
    request VARCHAR(255),
    status_code INT,
    user_agent TEXT,
    referrer TEXT NULL
);
