
"""Model de funcionários."""

from database import get_db


def buscar_por_usuario(usuario):
    # Procura um funcionário pelo nome de usuário.
    # permite ignorar maiúsculas e minúsculas.
    return get_db().execute(
        "SELECT * FROM usuarios WHERE usuario = ?",
        (usuario,)
    ).fetchone()


def criar(nome, usuario, senha_hash, cargo, foto_url=None):
    # Obtém a conexão com o banco.
    db = get_db()

    if not foto_url:
        foto_url = "images/fotos_perfil/usuarios/template_usuarios.jpeg"

    # Insere um novo funcionário.
    cursor = db.execute(
        """
        INSERT INTO usuarios (
            nome,
            usuario,
            senha_hash,
            cargo,
            foto_url
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (nome, usuario, senha_hash, cargo, foto_url)
    )

    # Confirma a alteração.
    db.commit()

    # Retorna o ID criado.
    return cursor.lastrowid


def listar():
    """
    Retorna todos os usuários cadastrados.
    """
    return get_db().execute(
        """
        SELECT
            id,
            nome,
            usuario,
            cargo,
            criado_em,
            foto_url
        FROM usuarios
        ORDER BY nome
        """
    ).fetchall()


def listar_cozinheiros():
    db = get_db()
    return db.execute("""
        SELECT id, nome
        FROM usuarios
        WHERE cargo = 'cozinheiro'
        ORDER BY nome ASC
    """).fetchall()


def buscar(usuario_id):
    # Procura um funcionário pelo ID.
    return get_db().execute(
        """
        SELECT *
        FROM usuarios
        WHERE id = ?
        """,
        (usuario_id,)
    ).fetchone()


def atualizar(
    usuario_id,
    nome,
    usuario,
    senha_hash,
    cargo,
    foto_url=None
):
    # Obtém a conexão com o banco.
    db = get_db()

    # Se uma nova foto foi enviada,
    # atualiza também o caminho da imagem.
    if foto_url:
        db.execute(
            """
            UPDATE usuarios
            SET nome = ?,
                usuario = ?,
                senha_hash = ?,
                cargo = ?,
                foto_url = ?
            WHERE id = ?
            """,
            (
                nome,
                usuario,
                senha_hash,
                cargo,
                foto_url,
                usuario_id
            )
        )

    else:
        # Mantém a foto que já estava cadastrada.
        db.execute(
            """
            UPDATE usuarios
            SET nome = ?,
                usuario = ?,
                senha_hash = ?,
                cargo = ?
            WHERE id = ?
            """,
            (
                nome,
                usuario,
                senha_hash,
                cargo,
                usuario_id
            )
        )

    # Confirma a alteração.
    db.commit()


def excluir(usuario_id):
    db = get_db()

    # perfis_categorias é apagada em cascata junto com o perfil.
    db.execute("DELETE FROM perfis WHERE usuario_id = ?", (usuario_id,))
    db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))

    db.commit()