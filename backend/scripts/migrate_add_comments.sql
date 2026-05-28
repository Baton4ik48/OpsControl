-- Миграция: добавление поля comment к таблицам servers и ports
-- Запускать один раз на живой БД. IF NOT EXISTS — безопасно повторять.

ALTER TABLE servers
    ADD COLUMN IF NOT EXISTS comment            TEXT,
    ADD COLUMN IF NOT EXISTS comment_updated_at TIMESTAMP;

ALTER TABLE ports
    ADD COLUMN IF NOT EXISTS comment            TEXT,
    ADD COLUMN IF NOT EXISTS comment_updated_at TIMESTAMP;
