CREATE TABLE IF NOT EXISTS apartamentos (
    numero TEXT PRIMARY KEY,
    morador TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS areas (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    taxa REAL NOT NULL CHECK (taxa >= 0)
);

CREATE TABLE IF NOT EXISTS reservas (
    codigo TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL REFERENCES apartamentos (numero),
    area TEXT NOT NULL REFERENCES areas (id),
    data TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ativa', 'cancelada'))
);

CREATE UNIQUE INDEX IF NOT EXISTS reserva_ativa_por_area_e_data
    ON reservas (area, data)
    WHERE status = 'ativa';

CREATE TABLE IF NOT EXISTS visitantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartamento TEXT NOT NULL REFERENCES apartamentos (numero),
    nome TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessoes (
    session_id TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL REFERENCES apartamentos (numero)
);
