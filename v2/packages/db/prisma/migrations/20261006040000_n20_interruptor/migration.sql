-- N-20: los interruptores de ClickUp real y de envíos reales viven en la base, con quién y cuándo. Solo se añaden filas:
-- manda la última de cada nombre. El fichero data/*/interruptor.json queda de respaldo (en la nube se reemplaza con cada versión).
CREATE TABLE IF NOT EXISTS interruptor (
  id     SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  valor  TEXT NOT NULL,
  quien  TEXT NOT NULL,
  motivo TEXT,
  cuando TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);
CREATE INDEX IF NOT EXISTS i_interruptor ON interruptor (nombre, id);
