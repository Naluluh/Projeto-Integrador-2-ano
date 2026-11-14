"""Model de ingredientes."""

from database import get_db


def listar(busca=""):
    # Permite pesquisar ingredientes pelo nome.
    termo = f"%{busca.strip()}%"

    return get_db().execute(
        """
        SELECT *
        FROM ingredientes
        WHERE norm(nome) LIKE norm(?)
        ORDER BY nome
        """,
        (termo,)
    ).fetchall()


def buscar(ingrediente_id):
    # Busca um ingrediente específico.
    return get_db().execute(
        "SELECT * FROM ingredientes WHERE id = ?",
        (ingrediente_id,)
    ).fetchone()


def criar(nome, unidade, estoque):
    db = get_db()

    db.execute(
        """
        INSERT INTO ingredientes (nome, unidade, estoque)
        VALUES (?, ?, ?)
        """,
        (nome, unidade, estoque)
    )

    db.commit()


def atualizar(ingrediente_id, nome, unidade, estoque):
    db = get_db()

    db.execute(
        """
        UPDATE ingredientes
        SET nome = ?,
            unidade = ?,
            estoque = ?
        WHERE id = ?
        """,
        (nome, unidade, estoque, ingrediente_id)
    )

    db.commit()


def excluir(ingrediente_id):
    db = get_db()

    db.execute(
        "DELETE FROM ingredientes WHERE id = ?",
        (ingrediente_id,)
    )

    db.commit()


def quantidade_total():
    # Conta o número de ingredientes cadastrados.
    return get_db().execute(
        "SELECT COUNT(*) AS total FROM ingredientes"
    ).fetchone()["total"]