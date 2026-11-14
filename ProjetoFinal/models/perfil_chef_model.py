# Consultas do perfil do cozinheiro
"""Model responsável pelo perfil dos cozinheiros."""

from database import get_db


# Lista os endereços de um usuário
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


# Troca as bancadas do perfil
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


# Liga o cozinheiro aos pratos da bancada
def _vincular_produtos(db, chef_id, categoria_id):
    """Torna o cozinheiro responsável pelos pratos da categoria (sem commit)."""
    db.execute(
        """
        INSERT INTO produto_chefs (produto_id, chef_id)
        SELECT id, ?
        FROM produtos
        WHERE categoria_id = ?
        ON CONFLICT DO NOTHING
        """,
        (chef_id, categoria_id)
    )


# Cadastra o perfil do cozinheiro
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

        # Ser responsável por uma categoria inclui os pratos dela.
        for categoria_id in categoria_ids:
            _vincular_produtos(db, usuario_id, int(categoria_id))

        db.commit()
        return id_perfil

    except Exception:
        db.rollback()
        raise


# Atualiza o perfil do cozinheiro
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


# Devolve o id do perfil do cozinheiro
def perfil_id(usuario_id):
    db = get_db()

    linha = db.execute(
        "SELECT id FROM perfis WHERE usuario_id = ?",
        (usuario_id,)
    ).fetchone()

    return linha["id"] if linha else None


# Lista as bancadas marcando as do cozinheiro
def categorias_com_status(usuario_id):
    """Todas as categorias, marcando as que o cozinheiro já atende."""

    return get_db().execute(
        """
        SELECT
            c.id,
            c.nome,
            c.foto_url,
            (pc.perfil_id IS NOT NULL) AS responsavel,
            (
                SELECT COUNT(*) FROM produtos AS pr
                WHERE pr.categoria_id = c.id
            ) AS total_produtos
        FROM categorias AS c
        LEFT JOIN (
            SELECT pcat.categoria_id, pcat.perfil_id
            FROM perfis_categorias AS pcat
            JOIN perfis AS p ON p.id = pcat.perfil_id
            WHERE p.usuario_id = ?
        ) AS pc ON pc.categoria_id = c.id
        ORDER BY c.nome
        """,
        (usuario_id,)
    ).fetchall()


# O cozinheiro passa a atender a bancada
def adicionar_categoria(usuario_id, categoria_id):
    """O cozinheiro passa a ser responsável pela categoria e por seus pratos."""

    db = get_db()
    perfil = perfil_id(usuario_id)

    if perfil is None:
        raise ValueError("Cadastre seu perfil antes de escolher categorias.")

    existe = db.execute(
        "SELECT 1 FROM categorias WHERE id = ?",
        (categoria_id,)
    ).fetchone()

    if existe is None:
        raise ValueError("Categoria não encontrada.")

    try:
        db.execute(
            """
            INSERT INTO perfis_categorias (perfil_id, categoria_id)
            VALUES (?, ?)
            ON CONFLICT DO NOTHING
            """,
            (perfil, categoria_id)
        )

        _vincular_produtos(db, usuario_id, categoria_id)
        db.commit()

    except Exception:
        db.rollback()
        raise


# O cozinheiro deixa de atender a bancada
def remover_categoria(usuario_id, categoria_id):
    """O cozinheiro deixa de ser responsável pela categoria e por seus pratos.

    Os pedidos já feitos continuam intactos: o histórico guarda o
    cozinheiro em pedidos.chef_id, que não é alterado aqui.
    """

    db = get_db()
    perfil = perfil_id(usuario_id)

    if perfil is None:
        raise ValueError("Cadastre seu perfil antes de escolher categorias.")

    try:
        db.execute(
            """
            DELETE FROM perfis_categorias
            WHERE perfil_id = ? AND categoria_id = ?
            """,
            (perfil, categoria_id)
        )

        db.execute(
            """
            DELETE FROM produto_chefs
            WHERE chef_id = ?
            AND produto_id IN (
                SELECT id FROM produtos WHERE categoria_id = ?
            )
            """,
            (usuario_id, categoria_id)
        )

        db.commit()

    except Exception:
        db.rollback()
        raise


# Atualiza formação, biografia e experiência
def atualizar_dados(usuario_id, formacao, biografia, experiencia):
    """Atualiza formação, biografia e experiência (sem mexer nas categorias)."""

    db = get_db()

    db.execute(
        """
        UPDATE perfis
        SET formacao = ?, biografia = ?, experiencia = ?
        WHERE usuario_id = ?
        """,
        (formacao, biografia, experiencia, usuario_id)
    )

    db.commit()


# Busca o perfil do cozinheiro
def buscar_perfil(usuario_id):
    return get_db().execute(
        "SELECT * FROM perfis WHERE usuario_id = ?",
        (usuario_id,)
    ).fetchone()
