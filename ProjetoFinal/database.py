"""Banco de dados (Neon/PostgreSQL na Vercel, SQLite local) com SQLAlchemy.

Na Vercel usa o Neon (DATABASE_URL). Sem DATABASE_URL, usa o arquivo local
`instance/sabor_e_clic.db`. As tabelas são criadas automaticamente na primeira
execução (ver `orm_models.py`) e o usuário administrador inicial é cadastrado
se o banco estiver vazio.

Os models (pasta `models/`) continuam usando `get_db().execute(sql, params)`
com parâmetros `?`; por baixo, a consulta é executada por uma conexão do
SQLAlchemy, e as linhas voltam como dicionários (`linha["nome"]`).
No Postgres, `Conexao.execute` ajusta o SQL (ver `_para_postgres`).
"""

import os
import re
import unicodedata

from flask import current_app, g
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool
from werkzeug.security import generate_password_hash

from orm_models import Base, Usuario

# Tabelas com coluna id: no Postgres o id novo vem do RETURNING (não existe lastrowid)
_TABELAS_COM_ID = {
    nome for nome, tabela in Base.metadata.tables.items() if "id" in tabela.c
}

_AGORA_PG = "to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')"

# norm() do Postgres: minúsculas e sem acento (igual ao _normalizar do SQLite)
_FUNCAO_NORM = """
CREATE OR REPLACE FUNCTION norm(texto text) RETURNS text AS $$
    SELECT translate(
        lower(texto),
        'áàâãäéèêëíìîïóòôõöúùûüçñ',
        'aaaaaeeeeiiiiooooouuuucn'
    )
$$ LANGUAGE sql IMMUTABLE
"""


def _normalizar(texto):
    """Minúsculas e sem acentos (usada nas buscas por nome)."""
    if texto is None:
        return None

    decomposto = unicodedata.normalize("NFD", str(texto).casefold())

    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def _configurar_conexao(conexao_dbapi, _registro):
    # Roda em toda conexão nova:
    # 1) liga as chaves estrangeiras (o SQLite não liga sozinho)
    # 2) WAL deixa ler enquanto outra requisição grava
    # 3) norm() faz a busca ignorar acentos e maiúsculas
    cursor = conexao_dbapi.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()
    conexao_dbapi.create_function("norm", 1, _normalizar, deterministic=True)


def criar_engine(url):
    # Postgres (Neon): sem pool, porque na Vercel cada requisição pode cair numa instância nova
    if make_url(url).get_backend_name() == "postgresql":
        return create_engine(url, poolclass=NullPool)

    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 15},
    )
    event.listen(engine, "connect", _configurar_conexao)
    return engine


def _para_postgres(sql, com_parametros):
    """Ajusta o SQL escrito para SQLite (usado nos models) para o Postgres."""
    if com_parametros:
        sql = sql.replace("%", "%%").replace("?", "%s")

    sql = re.sub(r"\bGROUP_CONCAT\s*\(", "string_agg(", sql, flags=re.I)
    sql = re.sub(r"\bCURRENT_TIMESTAMP\b", _AGORA_PG, sql, flags=re.I)

    return sql


class Resultado:
    """Resultado de uma consulta: linhas como dicionários."""

    def __init__(self, resultado, lastrowid=None, rowcount=None, consumido=False):
        self._resultado = resultado
        self.rowcount = resultado.rowcount if rowcount is None else rowcount

        # ID do último INSERT (no Postgres vem do RETURNING)
        self.lastrowid = lastrowid or getattr(resultado, "lastrowid", None)

        if consumido or not resultado.returns_rows:
            self._linhas = None
        else:
            self._linhas = resultado.mappings()

    def fetchone(self):
        linha = self._linhas.fetchone()
        return dict(linha) if linha is not None else None

    def fetchall(self):
        return [dict(linha) for linha in self._linhas.all()]

    def __iter__(self):
        return iter(self.fetchall())


class Conexao:
    """Conexão da requisição atual (uma transação por requisição)."""

    def __init__(self, conexao_sqlalchemy):
        self.conn = conexao_sqlalchemy
        self.postgres = conexao_sqlalchemy.dialect.name == "postgresql"

    def execute(self, sql, params=()):
        params = tuple(params or ())
        sql = sql.strip()

        if not self.postgres:
            # Manda o SQL e os "?" direto pro SQLite
            return Resultado(self.conn.exec_driver_sql(sql, params))

        sql = _para_postgres(sql, bool(params))

        # INSERT em tabela com id: pega o id novo com RETURNING
        tabela = re.match(r"INSERT\s+INTO\s+(\w+)", sql, re.I)
        quer_id = (
            tabela is not None
            and tabela.group(1).lower() in _TABELAS_COM_ID
            and "RETURNING" not in sql.upper()
        )

        if quer_id:
            sql += " RETURNING id"

        resultado = self.conn.exec_driver_sql(sql, params)

        if not quer_id:
            return Resultado(resultado)

        linhas = resultado.rowcount
        linha = resultado.mappings().first()

        return Resultado(
            resultado,
            lastrowid=linha["id"] if linha else None,
            rowcount=linhas,
            consumido=True,
        )

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db():
    """Devolve a conexão da requisição (abre na primeira chamada)."""
    if "db" not in g:
        engine = current_app.extensions["db_engine"]
        g.db = Conexao(engine.connect())

    return g.db


def close_db(_erro=None):
    db = g.pop("db", None)

    if db is not None:
        # Descarta o que não foi salvo
        db.rollback()
        db.close()


def init_db(app):
    """Cria o arquivo do banco, as tabelas e o administrador inicial."""
    engine = app.extensions["db_engine"]

    Base.metadata.create_all(engine)

    if engine.dialect.name == "postgresql":
        with engine.begin() as conexao:
            # Só cria a função norm() se ainda não existir
            tem_norm = conexao.exec_driver_sql(
                "SELECT 1 FROM pg_proc WHERE proname = 'norm'"
            ).first()

            if tem_norm is None:
                conexao.exec_driver_sql(_FUNCAO_NORM)

    try:
        with engine.begin() as conexao:
            ja_existe_usuario = conexao.execute(
                select(Usuario.id).limit(1)
            ).first()

            if ja_existe_usuario is None:
                senha_inicial = os.environ.get("ADMIN_SENHA_INICIAL") or "admin123"

                # Admin inicial: escolhe a senha nova no primeiro login (senha_temporaria = True)
                conexao.execute(
                    Usuario.__table__.insert().values(
                        nome="Administrador",
                        usuario="admin",
                        senha_hash=generate_password_hash(senha_inicial),
                        cargo="administrador",
                        senha_temporaria=True,
                    )
                )
    except IntegrityError:
        # Outra instância criou o admin ao mesmo tempo
        pass


def init_app(app):
    url = app.config["DATABASE_URL"]

    app.extensions["db_engine"] = criar_engine(url)
    app.teardown_appcontext(close_db)

    init_db(app)
