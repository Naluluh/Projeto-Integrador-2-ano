"""Model de compras e seus itens."""
from database import get_db


def listar():
    return get_db().execute(
        """SELECT c.*, u.nome AS usuario_nome
           FROM compras c JOIN usuarios u ON u.id = c.usuario_id
           ORDER BY c.criada_em DESC, c.id DESC"""
    ).fetchall()


def buscar(compra_id):
    return get_db().execute(
        """SELECT c.*, u.nome AS usuario_nome
           FROM compras c JOIN usuarios u ON u.id = c.usuario_id WHERE c.id = ?""",
        (compra_id,),
    ).fetchone()


def listar_itens(compra_id):
    return get_db().execute(
        "SELECT * FROM itens_compra WHERE compra_id = ? ORDER BY id", (compra_id,)
    ).fetchall()


def finalizar(usuario_id, carrinho):
    """Grava a compra e baixa o estoque em uma única transação."""
    db = get_db()
    try:
        itens = []
        for item in carrinho:
            produto = db.execute(
                "SELECT * FROM produtos WHERE id = ?", (item["produto_id"],)
            ).fetchone()
            if produto is None:
                raise ValueError(f"O produto {item['nome']} não existe mais.")
            if produto["estoque"] < item["quantidade"]:
                raise ValueError(f"Estoque insuficiente para {produto['nome']}.")
            itens.append((produto, item["quantidade"]))

        total = sum(p["preco_centavos"] * qtd for p, qtd in itens)
        cursor = db.execute(
            "INSERT INTO compras (usuario_id, total_centavos) VALUES (?, ?)",
            (usuario_id, total),
        )
        compra_id = cursor.lastrowid
        for produto, quantidade in itens:
            subtotal = produto["preco_centavos"] * quantidade
            db.execute(
                """INSERT INTO itens_compra
                   (compra_id, produto_id, produto_nome, preco_unitario_centavos,
                    quantidade, subtotal_centavos) VALUES (?, ?, ?, ?, ?, ?)""",
                (compra_id, produto["id"], produto["nome"],
                 produto["preco_centavos"], quantidade, subtotal),
            )
            db.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
                (quantidade, produto["id"]),
            )
        db.commit()
        return compra_id
    except Exception:
        db.rollback()
        raise


def quantidade_total():
    return get_db().execute("SELECT COUNT(*) AS total FROM compras").fetchone()["total"]

