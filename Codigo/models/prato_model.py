from database import get_db

def listar(busca=""):
    db = get_db()
    termo = f"%{busca.strip()}%"

    return db.execute("""
        SELECT
            produtos.*,
            categorias.nome AS categoria_nome
        FROM produtos
        JOIN categorias
            ON produtos.categoria_id = categorias.id
        WHERE produtos.nome LIKE ?
           OR categorias.nome LIKE ?
        ORDER BY produtos.nome COLLATE NOCASE
    """, (termo, termo)).fetchall()


def criar(nome, descricao, categoria_id, preco_centavos, modo_preparo):
    db = get_db()

    db.execute("""
        INSERT INTO produtos (
            nome,
            descricao,
            categoria_id,
            preco_centavos,
            modo_preparo
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        nome,
        descricao,
        categoria_id,
        preco_centavos,
        modo_preparo
    ))

    db.commit()


def atualizar(
    produto_id,
    nome,
    descricao,
    categoria_id,
    preco_centavos,
    modo_preparo
):
    db = get_db()

    db.execute("""
        UPDATE produtos
        SET nome = ?,
            descricao = ?,
            categoria_id = ?,
            preco_centavos = ?,
            modo_preparo = ?
        WHERE id = ?
    """, (
        nome,
        descricao,
        categoria_id,
        preco_centavos,
        modo_preparo,
        produto_id
    ))

    db.commit()


def listar_por_categoria(categoria_id):
    db = get_db()

    return db.execute("""
        SELECT
            produtos.*,
            categorias.nome AS categoria_nome
        FROM produtos
        JOIN categorias
            ON produtos.categoria_id = categorias.id
        WHERE produtos.categoria_id = ?
        ORDER BY produtos.nome
    """, (categoria_id,)).fetchall()


def listar_categorias():
    db = get_db()

    return db.execute("""
        SELECT id, nome
        FROM categorias
        ORDER BY nome
    """).fetchall()

def criar_categoria(nome):
    db = get_db()
    nome = nome.strip()

    if not nome:
        raise ValueError("Informe o nome da categoria.")

    db.execute("""
        INSERT INTO categorias (nome)
        VALUES (?)
        ON CONFLICT(nome) DO NOTHING
    """, (nome,))

    db.commit()

    categoria = db.execute("""
        SELECT id
        FROM categorias
        WHERE nome = ?
    """, (nome,)).fetchone()

    return categoria["id"]


def buscar(id_prato):
    """Busca um produto pelo seu ID."""

    return get_db().execute("""
        SELECT
            produtos.*,
            categorias.nome AS categoria_nome
        FROM produtos
        JOIN categorias
            ON produtos.categoria_id = categorias.id
        WHERE produtos.id = ?
    """, (id_prato,)).fetchone()

