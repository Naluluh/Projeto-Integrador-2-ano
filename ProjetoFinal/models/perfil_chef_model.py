"""Model responsável pelo perfil dos cozinheiros."""

from database import get_db


def endereco_por_usuario(usuario_id):
    db = get_db()

    return db.execute(
        """
        SELECT *
        FROM enderecos
        WHERE usuario_id = ?
        """,
        (usuario_id,)
    ).fetchall()


def _salvar_categorias(db, perfil_id, categoria_ids):
    """Substitui as categorias do perfil (sem commit)."""
    db.execute(
        "DELETE FROM perfis_categorias WHERE perfil_id = ?",
        (perfil_id,)
    )

    for categoria_id in categoria_ids:
        db.execute(
            """
            INSERT INTO perfis_categorias (
                perfil_id,
                categoria_id
            )
            VALUES (?, ?)
            ON CONFLICT DO NOTHING
            """,
            (perfil_id, int(categoria_id))
        )


def criar(usuario_id, formacao, biografia, categoria_ids, experiencia):
    """Cadastra o perfil de um cozinheiro e suas categorias."""

    db = get_db()

    try:
        cursor = db.execute(
            """
            INSERT INTO perfis (
                formacao,
                biografia,
                experiencia,
                usuario_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (formacao, biografia, experiencia, usuario_id)
        )

        id_perfil = cursor.lastrowid

        _salvar_categorias(db, id_perfil, categoria_ids)

        db.commit()
        return id_perfil

    except Exception:
        db.rollback()
        raise


def atualizar(id, usuario_id, formacao, biografia, categoria_ids, experiencia):
    """Atualiza o perfil de um cozinheiro e suas categorias."""

    db = get_db()

    try:
        db.execute(
            """
            UPDATE perfis
            SET
                formacao = ?,
                biografia = ?,
                experiencia = ?
            WHERE id = ? AND usuario_id = ?
            """,
            (formacao, biografia, experiencia, id, usuario_id)
        )

        _salvar_categorias(db, id, categoria_ids)

        db.commit()

    except Exception:
        db.rollback()
        raise


def perfil_id(usuario_id):
    db = get_db()

    linha = db.execute(
        "SELECT id FROM perfis WHERE usuario_id = ?",
        (usuario_id,)
    ).fetchone()

    return linha["id"] if linha else None