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

