-- Миграция: добавление типа устройства к серверам
-- Запустить один раз на существующей базе данных:
--   psql -U <user> -d <db> -f migrate_add_device_type.sql

ALTER TABLE servers
    ADD COLUMN IF NOT EXISTS device_type VARCHAR(32) NOT NULL DEFAULT 'linux';
