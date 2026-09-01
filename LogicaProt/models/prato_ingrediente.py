"""Model do relacionamento entre pratos e ingredientes."""

from database import get_db


def listar_por_prato(prato_id):
    # Retorna todos os ingredientes utilizados em um prato.
    return get_db().execute(
        """
        SELECT
            pi.prato_id,
            pi.ingrediente_id,
            pi.quantidade,
            i.nome,
            i.unidade,
            i.estoque
        FROM prato_ingredientes pi
        JOIN ingredientes i
            ON i.id = pi.ingrediente_id
        WHERE pi.prato_id = ?
        ORDER BY i.nome COLLATE NOCASE
        """,
        (prato_id,)
    ).fetchall()


def adicionar(prato_id, ingrediente_id, quantidade):
    # Obtém a conexão com o banco.
    db = get_db()

    # Cria a relação entre prato e ingrediente.
    db.execute(
        """
        INSERT INTO prato_ingredientes
            (prato_id, ingrediente_id, quantidade)
        VALUES (?, ?, ?)
        """,
        (prato_id, ingrediente_id, quantidade)
    )

    # Confirma a alteração.
    db.commit()


def remover(prato_id, ingrediente_id):
    # Obtém a conexão com o banco.
    db = get_db()

    # Remove a relação entre o prato e o ingrediente.
    db.execute(
        """
        DELETE FROM prato_ingredientes
        WHERE prato_id = ? AND ingrediente_id = ?
        """,
        (prato_id, ingrediente_id)
    )

    # Confirma a alteração.
    db.commit()