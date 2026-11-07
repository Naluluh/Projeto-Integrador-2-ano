"""Model de produtos do restaurante."""

from database import get_db


def listar(busca=""):
    # Adiciona % para permitir encontrar o termo
    # em qualquer parte do nome ou categoria.
    termo = f"%{busca.strip()}%"

    # Busca produtos pelo nome ou categoria.
    return get_db().execute(
        """
        SELECT *
        FROM produtos
        WHERE nome LIKE ? OR categoria LIKE ?
        ORDER BY nome COLLATE NOCASE
        """,
        (termo, termo)
    ).fetchall()


def buscar(produto_id):
    # Busca um produto específico pelo ID.
    return get_db().execute(
        "SELECT * FROM produtos WHERE id = ?",
        (produto_id,)
    ).fetchone()


def criar(nome, descricao, categoria, preco_centavos, modo_preparo):
    # Obtém a conexão com o banco.
    db = get_db()

    # Insere o produto.
    db.execute(
        """
        INSERT INTO produtos
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
    produto_id,
    nome,
    descricao,
    categoria,
    preco_centavos,
    modo_preparo
):
    # Obtém a conexão com o banco.
    db = get_db()

    # Atualiza os dados do produto.
    db.execute(
        """
        UPDATE produtos
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
            produto_id
        )
    )

    # Confirma a alteração.
    db.commit()


def excluir(produto_id):
    # Obtém a conexão com o banco.
    db = get_db()

    # Exclui o produto pelo ID.
    db.execute(
        "DELETE FROM produtos WHERE id = ?",
        (produto_id,)
    )

    # Confirma a exclusão.
    db.commit()


def quantidade_total():
    # Conta quantos produtos estão cadastrados.
    return get_db().execute(
        "SELECT COUNT(*) AS total FROM produtos"
    ).fetchone()["total"]