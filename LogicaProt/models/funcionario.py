"""Model de funcionários."""

from database import get_db


def buscar_por_usuario(usuario):
    # Procura um funcionário pelo nome de usuário.
    # COLLATE NOCASE permite ignorar maiúsculas e minúsculas.
    return get_db().execute(
        "SELECT * FROM funcionarios WHERE usuario = ? COLLATE NOCASE",
        (usuario,)
    ).fetchone()


def criar(nome, usuario, senha_hash, cargo):
    # Obtém a conexão com o banco.
    db = get_db()

    # Insere um novo funcionário.
    cursor = db.execute(
        """
        INSERT INTO funcionarios (nome, usuario, senha_hash, cargo)
        VALUES (?, ?, ?, ?)
        """,
        (nome, usuario, senha_hash, cargo)
    )

    # Confirma a alteração.
    db.commit()

    # Retorna o ID criado.
    return cursor.lastrowid