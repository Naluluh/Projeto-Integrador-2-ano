"""Conexão SQLite, ciclo de vida da conexão e criação das tabelas."""
import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
    senha_hash TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    fabricante TEXT NOT NULL,
    unidade TEXT NOT NULL,
    preco_centavos INTEGER NOT NULL CHECK (preco_centavos >= 0),
    estoque INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0),
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    total_centavos INTEGER NOT NULL CHECK (total_centavos >= 0),
    criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS itens_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compra_id INTEGER NOT NULL,
    produto_id INTEGER,
    produto_nome TEXT NOT NULL,
    preco_unitario_centavos INTEGER NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    subtotal_centavos INTEGER NOT NULL,
    FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE SET NULL
);
"""


def get_db():
    """Abre uma conexão por requisição e devolve linhas acessíveis por nome."""
    if "db" not in g:
        database_path = Path(current_app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(database_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Cria o esquema e o usuário inicial apenas quando necessário."""
    db = get_db()
    db.executescript(SCHEMA)
    existe = db.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone()
    if not existe:
        db.execute(
            "INSERT INTO usuarios (nome, usuario, senha_hash) VALUES (?, ?, ?)",
            ("Administrador", "admin", generate_password_hash("admin123")),
        )
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()

