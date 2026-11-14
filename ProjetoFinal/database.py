"""Conexão PostgreSQL/Neon e criação do esquema do Sabor & Clic."""
import os
import re
from flask import current_app, g
from psycopg import connect
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash

SCHEMA = r'''
CREATE TABLE IF NOT EXISTS usuarios (
 id BIGSERIAL PRIMARY KEY, nome TEXT NOT NULL,
 usuario TEXT NOT NULL UNIQUE, senha_hash TEXT NOT NULL,
 foto_url TEXT, cargo TEXT NOT NULL CHECK (cargo IN ('cliente','cozinheiro','administrador')),
 criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_usuario_lower ON usuarios (LOWER(usuario));
CREATE TABLE IF NOT EXISTS categorias (
 id BIGSERIAL PRIMARY KEY, nome TEXT NOT NULL UNIQUE, foto_url TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_categorias_nome_lower ON categorias (LOWER(nome));
CREATE TABLE IF NOT EXISTS produtos (
 id BIGSERIAL PRIMARY KEY, nome TEXT NOT NULL, descricao TEXT,
 categoria_id BIGINT NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
 foto_url TEXT, preco_centavos INTEGER NOT NULL CHECK(preco_centavos >= 0),
 modo_preparo TEXT, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS produto_chefs (
 produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
 chef_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 PRIMARY KEY(produto_id, chef_id)
);
CREATE TABLE IF NOT EXISTS enderecos (
 id BIGSERIAL PRIMARY KEY, usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 cep TEXT NOT NULL, logradouro TEXT NOT NULL, numero TEXT NOT NULL, complemento TEXT,
 bairro TEXT NOT NULL, cidade TEXT NOT NULL, estado TEXT NOT NULL, pais TEXT NOT NULL DEFAULT 'Brasil'
);
CREATE TABLE IF NOT EXISTS ingredientes (
 id BIGSERIAL PRIMARY KEY, nome TEXT NOT NULL, unidade TEXT NOT NULL,
 estoque DOUBLE PRECISION NOT NULL DEFAULT 0, armazenado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS produto_ingredientes (
 produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
 ingrediente_id BIGINT NOT NULL REFERENCES ingredientes(id) ON DELETE CASCADE,
 quantidade DOUBLE PRECISION NOT NULL CHECK(quantidade > 0), PRIMARY KEY(produto_id, ingrediente_id)
);
CREATE TABLE IF NOT EXISTS produto_ingrediente_alternativas (
 produto_id BIGINT NOT NULL, ingrediente_principal_id BIGINT NOT NULL,
 ingrediente_alternativo_id BIGINT NOT NULL, quantidade DOUBLE PRECISION NOT NULL CHECK(quantidade > 0),
 PRIMARY KEY(produto_id, ingrediente_principal_id, ingrediente_alternativo_id),
 CHECK(ingrediente_principal_id <> ingrediente_alternativo_id),
 FOREIGN KEY(produto_id, ingrediente_principal_id) REFERENCES produto_ingredientes(produto_id, ingrediente_id) ON DELETE CASCADE,
 FOREIGN KEY(ingrediente_alternativo_id) REFERENCES ingredientes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS pedidos (
 id BIGSERIAL PRIMARY KEY, usuario_id BIGINT NOT NULL REFERENCES usuarios(id),
 endereco_id BIGINT REFERENCES enderecos(id), status TEXT NOT NULL DEFAULT 'espera',
 total_centavos INTEGER NOT NULL DEFAULT 0 CHECK(total_centavos >= 0),
 chef_id BIGINT NOT NULL REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS itens_pedido (
 id BIGSERIAL PRIMARY KEY, pedido_id BIGINT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
 produto_id BIGINT NOT NULL REFERENCES produtos(id), produto_nome TEXT NOT NULL,
 preco_unitario_centavos INTEGER NOT NULL CHECK(preco_unitario_centavos >= 0),
 quantidade INTEGER NOT NULL CHECK(quantidade > 0), subtotal_centavos INTEGER NOT NULL CHECK(subtotal_centavos >= 0)
);
CREATE TABLE IF NOT EXISTS perfis (
 id BIGSERIAL PRIMARY KEY, formacao TEXT, biografia TEXT NOT NULL, experiencia TEXT,
 usuario_id BIGINT NOT NULL REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS perfis_categorias (
 categoria_id BIGINT NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
 perfil_id BIGINT NOT NULL REFERENCES perfis(id) ON DELETE CASCADE,
 PRIMARY KEY(categoria_id, perfil_id)
);
CREATE TABLE IF NOT EXISTS imagens (
 id BIGSERIAL PRIMARY KEY, tipo TEXT NOT NULL, dados BYTEA NOT NULL,
 criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
'''


# Alterações do esquema aplicadas a bancos que já existem (Neon). Todas são
# idempotentes (IF NOT EXISTS): rodam sem problema quantas vezes forem
# necessárias e também em bancos novos.
MIGRACOES = [
    # Produto visível (disponível) ou oculto para clientes e cozinheiros.
    "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE",

    # Senha temporária (gerada pelo administrador) obriga a trocar no login.
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS senha_temporaria BOOLEAN NOT NULL DEFAULT FALSE",

    # Quando a pessoa clicou em "esqueci minha senha" (segundos desde 1970).
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS reset_solicitado_em BIGINT",

    # Controle de tentativas de login (guardado no banco porque na Vercel
    # cada requisição pode cair em uma instância diferente).
    """CREATE TABLE IF NOT EXISTS login_tentativas (
        chave TEXT PRIMARY KEY,
        tentativas INTEGER NOT NULL DEFAULT 0,
        atualizado_em BIGINT NOT NULL DEFAULT 0,
        bloqueado_ate BIGINT NOT NULL DEFAULT 0
    )""",

    # Registro de quais porções do item foram feitas com ingrediente alternativo.
    """CREATE TABLE IF NOT EXISTS itens_pedido_substituicoes (
        id BIGSERIAL PRIMARY KEY,
        item_pedido_id BIGINT NOT NULL REFERENCES itens_pedido(id) ON DELETE CASCADE,
        ingrediente_original TEXT NOT NULL,
        ingrediente_alternativo TEXT NOT NULL,
        unidade TEXT NOT NULL DEFAULT '',
        porcoes INTEGER NOT NULL CHECK(porcoes > 0),
        quantidade DOUBLE PRECISION NOT NULL CHECK(quantidade >= 0)
    )""",
]

_ID_TABLES = {'usuarios','categorias','produtos','enderecos','ingredientes','pedidos','itens_pedido','perfis','imagens'}

class CursorCompat:
    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self.lastrowid = lastrowid
    def fetchone(self): return self._cursor.fetchone()
    def fetchall(self): return self._cursor.fetchall()
    @property
    def rowcount(self): return self._cursor.rowcount
    def __iter__(self): return iter(self._cursor)

class ConnectionCompat:
    def __init__(self, conn): self.conn = conn
    def execute(self, sql, params=()):
        statement = sql.strip()
        statement = re.sub(r'\?', '%s', statement)
        statement = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT INTO', statement, flags=re.I)
        if re.search(r'INSERT\s+INTO\s+perfis_categorias', statement, re.I) and 'ON CONFLICT' not in statement.upper():
            statement += ' ON CONFLICT DO NOTHING'
        match = re.match(r'INSERT\s+INTO\s+(\w+)', statement, re.I)
        wants_id = bool(match and match.group(1).lower() in _ID_TABLES and 'RETURNING' not in statement.upper())
        if wants_id: statement += ' RETURNING id'
        cur = self.conn.execute(statement, params or ())
        new_id = None
        if wants_id:
            row = cur.fetchone()
            new_id = row['id'] if row else None
        return CursorCompat(cur, new_id)
    def executescript(self, script):
        for statement in script.split(';'):
            if statement.strip(): self.conn.execute(statement)
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self): self.conn.close()


# Tabela usada como "marcador": se ela existe, o esquema já foi criado.
# Ao adicionar tabelas novas no futuro, mantenha a mais recente no fim do
# SCHEMA e atualize este marcador.
_TABELA_MARCADOR = 'imagens'

# Na Vercel cada instância é um processo novo (cold start). Esta flag evita
# repetir a verificação do esquema a cada requisição da mesma instância.
_esquema_pronto = False


def get_db():
    global _esquema_pronto
    if 'db' not in g:
        url = current_app.config.get('DATABASE_URL')
        if not url:
            raise RuntimeError('DATABASE_URL não foi configurada. Cadastre a connection string do Neon nas variáveis de ambiente.')
        # Neon fornece URLs postgres:// ou postgresql://; psycopg aceita ambas.
        # prepare_threshold=None desliga prepared statements, evitando
        # problemas com o pooler (PgBouncer) do Neon.
        conexao = ConnectionCompat(connect(
            url, row_factory=dict_row, connect_timeout=10,
            prepare_threshold=None
        ))
        try:
            if not _esquema_pronto:
                _garantir_esquema(conexao)
                _esquema_pronto = True
        except Exception:
            conexao.close()
            raise
        g.db = conexao
    return g.db


def close_db(_error=None):
    db = g.pop('db', None)
    if db is not None: db.close()


def _garantir_esquema(db):
    """Cria as tabelas somente se ainda não existirem.

    Roda uma única vez por instância, na primeira consulta ao banco, e não
    mais ao importar o app: assim a tela de login não depende do banco e um
    Neon "dormindo" não derruba o carregamento da função.
    """
    # Lock de transação: se duas instâncias subirem juntas, uma espera a outra
    # terminar (evita erro de "tabela já existe" em criações simultâneas).
    db.conn.execute('SELECT pg_advisory_xact_lock(727001)')
    existe = db.conn.execute(
        'SELECT to_regclass(%s::text) IS NOT NULL AS existe', (_TABELA_MARCADOR,)
    ).fetchone()['existe']
    if not existe:
        db.executescript(SCHEMA)

    # Alterações para bancos já existentes (ver MIGRACOES).
    for comando in MIGRACOES:
        db.conn.execute(comando)

    usuario = db.execute('SELECT 1 FROM usuarios LIMIT 1').fetchone()
    if not usuario:
        senha_inicial = os.environ.get('ADMIN_SENHA_INICIAL') or 'admin123'
        # senha_temporaria = TRUE: o admin escolhe uma senha forte no 1º login.
        db.execute('''INSERT INTO usuarios (nome, usuario, senha_hash, cargo, senha_temporaria)
                      VALUES (?, ?, ?, ?, TRUE)''',
                   ('Administrador', 'admin', generate_password_hash(senha_inicial), 'administrador'))
    db.commit()


def init_db():
    """Força a criação do esquema (uso manual, por exemplo em scripts)."""
    global _esquema_pronto
    _esquema_pronto = False
    get_db()


def init_app(app):
    app.teardown_appcontext(close_db)
