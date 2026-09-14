"""Conexão SQLite, ciclo de vida da conexão e criação das tabelas."""

import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


SCHEMA = """

-- Ativa o uso das chaves estrangeiras no SQLite.
PRAGMA foreign_keys = ON;


-- Usuários que acessam o sistema.
CREATE TABLE IF NOT EXISTS usuarios (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    nome TEXT NOT NULL,

    usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,

    senha_hash TEXT NOT NULL,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

);


-- Acervo de livros da biblioteca.
CREATE TABLE IF NOT EXISTS livros (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    titulo TEXT NOT NULL,

    autor TEXT NOT NULL,

    isbn TEXT NOT NULL UNIQUE,

    editora TEXT NOT NULL,

    ano INTEGER NOT NULL CHECK (ano > 0),

    assunto TEXT NOT NULL,

    -- 1 = disponível
    -- 0 = emprestado
    disponivel INTEGER NOT NULL DEFAULT 1,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

);


-- Pessoas cadastradas como leitores.
CREATE TABLE IF NOT EXISTS leitores (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    nome TEXT NOT NULL,

    email TEXT NOT NULL UNIQUE COLLATE NOCASE,

    telefone TEXT,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

);


-- Registro principal de cada empréstimo.
CREATE TABLE IF NOT EXISTS emprestimos (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Leitor que recebeu os livros.
    leitor_id INTEGER NOT NULL,

    -- Usuário do sistema que registrou o empréstimo.
    usuario_id INTEGER NOT NULL,

    data_emprestimo TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    data_devolucao TEXT,

    -- Pode ser "emprestado" ou "devolvido".
    status TEXT NOT NULL DEFAULT 'emprestado',

    FOREIGN KEY (leitor_id)
        REFERENCES leitores(id),

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)

);


-- Livros pertencentes a cada empréstimo.
CREATE TABLE IF NOT EXISTS itens_emprestimo (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    emprestimo_id INTEGER NOT NULL,

    livro_id INTEGER,

    -- Guarda o título para preservar o histórico.
    livro_titulo TEXT NOT NULL,

    FOREIGN KEY (emprestimo_id)
        REFERENCES emprestimos(id)
        ON DELETE CASCADE,

    FOREIGN KEY (livro_id)
        REFERENCES livros(id)
        ON DELETE SET NULL

);

"""


def get_db():
    """Abre uma conexão por requisição."""

    # Verifica se a conexão já foi criada nesta requisição.
    if "db" not in g:

        # Obtém o caminho do banco definido no Config.
        database_path = Path(
            current_app.config["DATABASE"]
        )

        # Cria a pasta instance caso ela não exista.
        database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Abre a conexão SQLite.
        g.db = sqlite3.connect(database_path)

        # Permite acessar as colunas pelo nome.
        g.db.row_factory = sqlite3.Row

        # Ativa as chaves estrangeiras nesta conexão.
        g.db.execute(
            "PRAGMA foreign_keys = ON"
        )

    return g.db


def close_db(_error=None):
    """Fecha a conexão ao terminar a requisição."""

    # Retira a conexão do contexto Flask.
    db = g.pop("db", None)

    # Fecha a conexão se ela existir.
    if db is not None:
        db.close()


def init_db():
    """Cria as tabelas e o usuário inicial."""

    # Obtém a conexão com o banco.
    db = get_db()

    # Executa todas as instruções SQL do SCHEMA.
    db.executescript(SCHEMA)

    # Verifica se existe algum usuário.
    existe = db.execute(
        "SELECT 1 FROM usuarios LIMIT 1"
    ).fetchone()

    # Cria o administrador inicial caso seja o primeiro acesso.
    if not existe:

        db.execute(
            """
            INSERT INTO usuarios
                (nome, usuario, senha_hash)
            VALUES (?, ?, ?)
            """,
            (
                "Administrador",
                "admin",
                generate_password_hash("admin123"),
            ),
        )

    # Confirma as alterações.
    db.commit()


def init_app(app):
    """Inicializa o banco junto com a aplicação."""

    # Define o fechamento automático da conexão.
    app.teardown_appcontext(close_db)

    # Cria o banco/tabelas quando a aplicação inicia.
    with app.app_context():
        init_db()