"""Model de produtos."""
from database import get_db


def listar(busca=""):
    termo = f"%{busca.strip()}%"
    return get_db().execute(
        """SELECT * FROM produtos
           WHERE nome LIKE ? OR fabricante LIKE ?
           ORDER BY nome COLLATE NOCASE""",
        (termo, termo),
    ).fetchall()


def buscar(produto_id):
    return get_db().execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()


def criar(nome, fabricante, unidade, preco_centavos, estoque):
    db = get_db()
    db.execute(
        """INSERT INTO produtos (nome, fabricante, unidade, preco_centavos, estoque)
           VALUES (?, ?, ?, ?, ?)""",
        (nome, fabricante, unidade, preco_centavos, estoque),
    )
    db.commit()


def atualizar(produto_id, nome, fabricante, unidade, preco_centavos, estoque):
    db = get_db()
    db.execute(
        """UPDATE produtos SET nome=?, fabricante=?, unidade=?, preco_centavos=?, estoque=?
           WHERE id=?""",
        (nome, fabricante, unidade, preco_centavos, estoque, produto_id),
    )
    db.commit()


def excluir(produto_id):
    db = get_db()
    db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    db.commit()


def quantidade_total():
    return get_db().execute("SELECT COUNT(*) AS total FROM produtos").fetchone()["total"]

