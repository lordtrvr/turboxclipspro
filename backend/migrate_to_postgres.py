"""Migra los usuarios de SQLite local a PostgreSQL (Neon).

Uso:
    set DATABASE_URL=postgresql://usuario:pass@host/db?sslmode=require
    python backend/migrate_to_postgres.py

El script crea las tablas si no existen y copia los usuarios respetando el id.
Es seguro ejecutarlo mas de una vez: omite emails que ya existan.
"""
import os
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = BASE_DIR / "turbox_web.db"

# Cargar .env sin dependencias extra
env_path = BASE_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL or "sqlite" in DATABASE_URL:
    print("ERROR: define DATABASE_URL con la cadena de PostgreSQL de Neon en el entorno o en .env")
    sys.exit(1)

sys.path.insert(0, str(BASE_DIR))
from backend.models import Base, User  # noqa: E402

pg_engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=pg_engine)
PgSession = sessionmaker(bind=pg_engine)

local = sqlite3.connect(str(SQLITE_PATH))
local.row_factory = sqlite3.Row
cols = [r[1] for r in local.execute("PRAGMA table_info(users)").fetchall()]
print("Columnas SQLite:", ", ".join(cols))

with PgSession() as db:
    for row in local.execute("SELECT * FROM users ORDER BY id"):
        data = dict(row)
        if db.query(User).filter(User.email == data["email"]).first():
            print("Omitido (ya existe):", data["email"])
            continue
        allowed = {c.name for c in User.__table__.columns}
        payload = {k: v for k, v in data.items() if k in allowed}
        db.add(User(**payload))
        db.commit()
        print("Migrado:", data["email"])

# Tras insertar IDs explicitos, la secuencia debe quedar en el maximo para
# que los nuevos registros no choquen con "duplicate key value violates unique constraint".
with pg_engine.begin() as _conn:
    _seq = _conn.exec_driver_sql("SELECT pg_get_serial_sequence('users', 'id')").scalar()
    if _seq:
        _max = _conn.exec_driver_sql("SELECT COALESCE(MAX(id), 1) FROM users").scalar()
        _last = _conn.exec_driver_sql(f"SELECT last_value FROM {_seq}").scalar()
        _conn.exec_driver_sql(f"SELECT setval('{_seq}', {max(int(_max or 1), int(_last or 1))})")
        print("Secuencia sincronizada:", _seq)

local.close()
print("LISTO: migracion terminada")
