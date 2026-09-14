"""Model de pratos do restaurante."""

from database import get_db


def listar(busca=""):
    # Adiciona % para permitir encontrar o termo
    # em qualquer parte do nome ou categoria.
    termo = f"%{busca.strip()}%"

    # Busca pratos pelo nome ou categoria.
    return get_db().execute(
        """
        SELECT *
        FROM pratos
        WHERE nome LIKE ? OR categoria LIKE ?
        ORDER BY nome COLLATE NOCASE
        """,
        (termo, termo)
    ).fetchall()


def buscar(prato_id):
    # Busca um prato específico pelo ID.
    return get_db().execute(
        "SELECT * FROM pratos WHERE id = ?",
        (prato_id,)
    ).fetchone()


def criar(nome, descricao, categoria, preco_centavos, modo_preparo):
    # Obtém a conexão com o banco.
    db = get_db()

    # Insere o prato.
    db.execute(
        """
        INSERT INTO pratos
            (nome, descricao, categoria, preco_centavos, modo_preparo)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            nome,
            descricao,
            categoria,
            preco_centavos,
            modo_preparo
        )
    )

    # Confirma a alteração.
    db.commit()


def atualizar(
    prato_id,
    nome,
    descricao,
    categoria,
    preco_centavos,
    modo_preparo
):
    # Obtém a conexão com o banco.
    db = get_db()

    # Atualiza os dados do prato.
    db.execute(
        """
        UPDATE pratos
        SET nome = ?,
            descricao = ?,
            categoria = ?,
            preco_centavos = ?,
            modo_preparo = ?
        WHERE id = ?
        """,
        (
            nome,
            descricao,
            categoria,
            preco_centavos,
            modo_preparo,
            prato_id
        )
    )

    # Confirma a alteração.
    db.commit()


def excluir(prato_id):
    # Obtém a conexão com o banco.
    db = get_db()

    # Exclui o prato pelo ID.
    db.execute(
        "DELETE FROM pratos WHERE id = ?",
        (prato_id,)
    )

    # Confirma a exclusão.
    db.commit()


def quantidade_total():
    # Conta quantos pratos estão cadastrados.
    return get_db().execute(
        "SELECT COUNT(*) AS total FROM pratos"
    ).fetchone()["total"]