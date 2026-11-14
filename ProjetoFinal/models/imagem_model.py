"""Model das imagens enviadas pelos usuários (guardadas no banco)."""

from database import get_db


def criar(tipo, dados):
    # Guarda a imagem. O commit é feito pela operação que a utiliza,
    # para que a foto e o registro dono dela sejam salvos juntos.
    cursor = get_db().execute(
        "INSERT INTO imagens (tipo, dados) VALUES (?, ?)",
        (tipo, dados)
    )

    return cursor.lastrowid


def buscar(imagem_id):
    return get_db().execute(
        "SELECT tipo, dados FROM imagens WHERE id = ?",
        (imagem_id,)
    ).fetchone()
