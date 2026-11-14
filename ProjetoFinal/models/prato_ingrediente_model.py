"""Model do relacionamento entre pratos e ingredientes."""

from database import get_db


def listar_por_prato(produto_id):
    # Retorna todos os ingredientes utilizados em um prato.
    return get_db().execute(
        """
        SELECT
            pi.produto_id,
            pi.ingrediente_id,
            pi.quantidade,
            i.nome,
            i.unidade,
            i.estoque
        FROM produto_ingredientes pi
        JOIN ingredientes i
            ON i.id = pi.ingrediente_id
        WHERE pi.produto_id = ?
        ORDER BY i.nome
        """,
        (produto_id,)
    ).fetchall()


def adicionar(produto_id, ingrediente_id, quantidade):
    db = get_db()

    db.execute(
        """
        INSERT INTO produto_ingredientes
            (produto_id, ingrediente_id, quantidade)
        VALUES (?, ?, ?)
        """,
        (produto_id, ingrediente_id, quantidade)
    )

    db.commit()


def remover(produto_id, ingrediente_id):
    db = get_db()

    db.execute(
        """
        DELETE FROM produto_ingredientes
        WHERE produto_id = ? AND ingrediente_id = ?
        """,
        (produto_id, ingrediente_id)
    )

    db.commit()