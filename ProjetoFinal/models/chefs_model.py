
from database import get_db


def chefs_produto(id_p):
    """Lista os cozinheiros relacionados a um produto."""

    db = get_db()

    lista = db.execute(
        """
        SELECT
            u.id,
            u.nome,
            u.usuario,
            u.foto_url,
            p.biografia
        FROM usuarios AS u

        INNER JOIN produto_chefs AS pc
            ON u.id = pc.chef_id

        LEFT JOIN perfis AS p
            ON u.id = p.usuario_id

        WHERE pc.produto_id = ?
        AND u.cargo = 'cozinheiro'

        ORDER BY u.nome
        """,
        (id_p,)
    ).fetchall()

    return lista


def chefs_categoria(categoria_id):
    """Lista cozinheiros relacionados a uma categoria."""

    db = get_db()

    lista = db.execute(
        """
        SELECT
            u.id,
            u.nome,
            u.usuario,
            u.foto_url,
            p.biografia
        FROM usuarios AS u

        INNER JOIN perfis AS p
            ON u.id = p.usuario_id

        INNER JOIN perfis_categorias AS pc
            ON p.id = pc.perfil_id

        WHERE pc.categoria_id = ?
        AND u.cargo = 'cozinheiro'

        ORDER BY u.nome
        """,
        (categoria_id,)
    ).fetchall()

    return lista


def verificar_chef_categoria(chef_id, categoria_id):
    """Verifica se o cozinheiro atende determinada categoria."""

    db = get_db()

    resultado = db.execute(
        """
        SELECT 1
        FROM perfis AS p

        INNER JOIN perfis_categorias AS pc
            ON p.id = pc.perfil_id

        INNER JOIN usuarios AS u
            ON u.id = p.usuario_id

        WHERE u.id = ?
        AND pc.categoria_id = ?
        AND u.cargo = 'cozinheiro'
        """,
        (chef_id, categoria_id)
    ).fetchone()

    return resultado is not None


def verificar_chef_produto(chef_id, produto_id):
    """Verifica se o cozinheiro pode preparar o produto."""

    db = get_db()

    resultado = db.execute(
        """
        SELECT 1
        FROM produto_chefs AS pc

        INNER JOIN usuarios AS u
            ON u.id = pc.chef_id

        WHERE pc.chef_id = ?
        AND pc.produto_id = ?
        AND u.cargo = 'cozinheiro'
        """,
        (chef_id, produto_id)
    ).fetchone()

    return resultado is not None


def produtos_chef_categoria(chef_id, categoria_id):
    """Lista produtos da categoria preparados pelo cozinheiro."""

    db = get_db()

    produtos = db.execute(
        """
        SELECT
            p.*
        FROM produtos AS p

        INNER JOIN produto_chefs AS pc
            ON p.id = pc.produto_id

        WHERE pc.chef_id = ?
        AND p.categoria_id = ?

        ORDER BY p.nome
        """,
        (chef_id, categoria_id)
    ).fetchall()

    return produtos


def categoria_por_produto(produto_id):
    """Retorna a categoria de um produto."""

    db = get_db()

    resultado = db.execute(
        """
        SELECT categoria_id
        FROM produtos
        WHERE id = ?
        """,
        (produto_id,)
    ).fetchone()

    if resultado is None:
        return None

    return resultado["categoria_id"]
