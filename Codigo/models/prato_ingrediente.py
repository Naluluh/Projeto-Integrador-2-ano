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
        FROM prato_ingredientes pi
        JOIN ingredientes i
            ON i.id = pi.ingrediente_id
        WHERE pi.produto_id = ?
        ORDER BY i.nome COLLATE NOCASE
        """,
        (produto_id,)
    ).fetchall()


def adicionar(produto_id, ingrediente_id, quantidade):
    # Obtém a conexão com o banco.
    db = get_db()

    # Cria a relação entre prato e ingrediente.
    db.execute(
        """
        INSERT INTO prato_ingredientes
            (produto_id, ingrediente_id, quantidade)
        VALUES (?, ?, ?)
        """,
        (produto_id, ingrediente_id, quantidade)
    )

    # Confirma a alteração.
    db.commit()


def remover(produto_id, ingrediente_id):
    # Obtém a conexão com o banco.
    db = get_db()

    # Remove a relação entre o prato e o ingrediente.
    db.execute(
        """
        DELETE FROM prato_ingredientes
        WHERE produto_id = ? AND ingrediente_id = ?
        """,
        (produto_id, ingrediente_id)
    )

    # Confirma a alteração.
    db.commit()