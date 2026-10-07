"""
Gerenciamento do banco de dados do Sabor & Clic.

Responsabilidades:
- Criar e fechar a conexão SQLite.
- Criar as tabelas do sistema.
- Criar o administrador inicial.
"""

import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


# ============================================================
# ESTRUTURA DO BANCO
# ============================================================

SCHEMA = """

PRAGMA foreign_keys = ON;


-- ============================================================
-- USUÁRIOS
-- ============================================================

CREATE TABLE IF NOT EXISTS usuarios (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    nome TEXT NOT NULL,

    usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,

    senha_hash TEXT NOT NULL,

    cargo TEXT NOT NULL CHECK (
        cargo IN (
            'cliente',
            'cozinheiro',
            'administrador'
        )
    ),

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- INGREDIENTES
-- ============================================================

CREATE TABLE IF NOT EXISTS ingredientes (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    nome TEXT NOT NULL,

    unidade TEXT NOT NULL,

    estoque REAL NOT NULL DEFAULT 0,

    armazenado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- PRODUTOS
-- ============================================================

CREATE TABLE IF NOT EXISTS produtos (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    nome TEXT NOT NULL,

    descricao TEXT,

    categoria TEXT NOT NULL,

    preco_centavos INTEGER NOT NULL CHECK (
        preco_centavos >= 0
    ),

    modo_preparo TEXT,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- RELAÇÃO ENTRE produtoS E INGREDIENTES
-- ============================================================

CREATE TABLE IF NOT EXISTS produto_ingredientes (

    produto_id INTEGER NOT NULL,

    ingrediente_id INTEGER NOT NULL,

    quantidade REAL NOT NULL CHECK (
        quantidade > 0
    ),

    PRIMARY KEY (
        produto_id,
        ingrediente_id
    ),

    FOREIGN KEY (produto_id)
        REFERENCES produtos(id)
        ON DELETE CASCADE,

    FOREIGN KEY (ingrediente_id)
        REFERENCES ingredientes(id)
        ON DELETE CASCADE
);


-- ============================================================
-- PEDIDOS
-- ============================================================

CREATE TABLE IF NOT EXISTS pedidos (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    usuario_id INTEGER NOT NULL,

    status TEXT NOT NULL DEFAULT 'espera',

    total_centavos INTEGER NOT NULL DEFAULT 0 CHECK (
        total_centavos >= 0
    ),

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
);

-- ============================================================
-- ITENS DOS PEDIDOS
-- ============================================================

CREATE TABLE IF NOT EXISTS itens_pedido (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    pedido_id INTEGER NOT NULL,

    produto_id INTEGER NOT NULL,

    produto_nome TEXT NOT NULL,

    preco_unitario_centavos INTEGER NOT NULL CHECK (
        preco_unitario_centavos >= 0
    ),

    quantidade INTEGER NOT NULL CHECK (
        quantidade > 0
    ),

    subtotal_centavos INTEGER NOT NULL CHECK (
        subtotal_centavos >= 0
    ),

    FOREIGN KEY (pedido_id)
        REFERENCES pedidos(id)
        ON DELETE CASCADE,

    FOREIGN KEY (produto_id)
        REFERENCES produtos(id)
);


"""


# ============================================================
# CONEXÃO
# ============================================================

def get_db():
    """
    Retorna a conexão com o banco da requisição atual.
    """

    if "db" not in g:

        database_path = Path(
            current_app.config["DATABASE"]
        )

        database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        g.db = sqlite3.connect(
            database_path
        )

        g.db.row_factory = sqlite3.Row

        g.db.execute(
            "PRAGMA foreign_keys = ON"
        )

    return g.db


# ============================================================
# FECHAMENTO DA CONEXÃO
# ============================================================

def close_db(_error=None):
    """
    Fecha a conexão com o banco.
    """

    db = g.pop(
        "db",
        None
    )

    if db is not None:
        db.close()


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def init_db():

    
    """
    Cria as tabelas e o administrador inicial.
    """

    db = get_db()

   # print("====================================")
   # print("BANCO USADO:")
   # print(current_app.config["DATABASE"])
   # print("====================================")

   # db.executescript(SCHEMA)

   # tabelas = db.execute("""
    #    SELECT name
    #    FROM sqlite_master
    #    WHERE type = 'table'
    #    ORDER BY name
    # """).fetchall() """

    # print("TABELAS EXISTENTES:")

    #for tabela in tabelas:
     #   print("-", tabela["name"])

    # Cria todas as tabelas.
    db.executescript(
        SCHEMA
    )

    # Verifica se já existe algum usuário.
    usuario_existe = db.execute(
        """
        SELECT 1
        FROM usuarios
        LIMIT 1
        """
    ).fetchone()

    # Cria o administrador inicial.
    if not usuario_existe:

        senha_hash = generate_password_hash(
            "admin123"
        )

        db.execute(
            """
            INSERT INTO usuarios (
                nome,
                usuario,
                senha_hash,
                cargo
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "Administrador",
                "admin",
                senha_hash,
                "administrador"
            )
        )

    db.commit()


# ============================================================
# INTEGRAÇÃO COM O FLASK
# ============================================================

def init_app(app):
    """
    Inicializa o banco junto com a aplicação Flask.
    """

    app.teardown_appcontext(
        close_db
    )

    with app.app_context():
        init_db()

    