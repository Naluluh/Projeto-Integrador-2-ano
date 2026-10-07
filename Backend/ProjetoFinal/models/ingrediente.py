"""Model de ingredientes."""

from database import get_db


def listar(busca=""):
    # Permite pesquisar ingredientes pelo nome.
    termo = f"%{busca.strip()}%"

    return get_db().execute(
        """
        SELECT *
        FROM ingredientes
        WHERE nome LIKE ?
        ORDER BY nome COLLATE NOCASE
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
    # Obtém a conexão com o banco.
    db = get_db()

    # Cadastra o ingrediente.
    db.execute(
        """
        INSERT INTO ingredientes (nome, unidade, estoque)
        VALUES (?, ?, ?)
        """,
        (nome, unidade, estoque)
    )

    # Confirma a alteração.
    db.commit()


def atualizar(ingrediente_id, nome, unidade, estoque):
    # Obtém a conexão com o banco.
    db = get_db()

    # Atualiza os dados do ingrediente.
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

    # Confirma a alteração.
    db.commit()


def excluir(ingrediente_id):
    # Obtém a conexão com o banco.
    db = get_db()

    # Exclui o ingrediente.
    db.execute(
        "DELETE FROM ingredientes WHERE id = ?",
        (ingrediente_id,)
    )

    # Confirma a alteração.
    db.commit()


def quantidade_total():
    # Conta o número de ingredientes cadastrados.
    return get_db().execute(
        "SELECT COUNT(*) AS total FROM ingredientes"
    ).fetchone()["total"]