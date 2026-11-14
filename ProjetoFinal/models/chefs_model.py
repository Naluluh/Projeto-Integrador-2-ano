# Consultas dos cozinheiros e do que eles preparam

from database import get_db


# Lista os cozinheiros que fazem um prato
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


# Lista os cozinheiros de uma bancada
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


# Confere se o cozinheiro atende a bancada
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


# Confere se o cozinheiro faz o prato
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


# Lista os pratos da bancada que o cozinheiro faz
def produtos_chef_categoria(chef_id, categoria_id, incluir_inativos=False):
    """Lista produtos da categoria preparados pelo cozinheiro.

    Pratos marcados como indisponíveis só aparecem para quem pode gerenciá-los.
    """

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
        AND (p.ativo OR ?)

        ORDER BY p.nome
        """,
        (chef_id, categoria_id, bool(incluir_inativos))
    ).fetchall()

    return produtos


# Devolve a categoria de um prato
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


# Lista os cozinheiros com um resumo do perfil
def listar_cozinheiros(incluir_inativos=False):
    """Lista todos os cozinheiros, com um resumo do perfil."""

    return get_db().execute(
        """
        SELECT
            u.id,
            u.nome,
            u.usuario,
            u.foto_url,
            p.id AS perfil_id,
            p.formacao,
            p.biografia,
            (
                SELECT COUNT(*) FROM perfis_categorias AS pc
                WHERE pc.perfil_id = p.id
            ) AS total_categorias,
            (
                SELECT COUNT(*)
                FROM produto_chefs AS pch
                JOIN produtos AS pr ON pr.id = pch.produto_id
                WHERE pch.chef_id = u.id AND (pr.ativo OR ?)
            ) AS total_produtos
        FROM usuarios AS u
        LEFT JOIN perfis AS p ON p.usuario_id = u.id
        WHERE u.cargo = 'cozinheiro'
        ORDER BY u.nome
        """,
        (bool(incluir_inativos),)
    ).fetchall()


# Busca um cozinheiro com o perfil
def buscar_cozinheiro(chef_id):
    """Dados do cadastro do cozinheiro + perfil (sem a senha)."""

    return get_db().execute(
        """
        SELECT
            u.id,
            u.nome,
            u.usuario,
            u.foto_url,
            u.criado_em,
            p.id AS perfil_id,
            p.formacao,
            p.biografia,
            p.experiencia
        FROM usuarios AS u
        LEFT JOIN perfis AS p ON p.usuario_id = u.id
        WHERE u.id = ? AND u.cargo = 'cozinheiro'
        """,
        (chef_id,)
    ).fetchone()


# Lista as bancadas do cozinheiro
def categorias_do_chef(chef_id):
    """Categorias pelas quais o cozinheiro é responsável."""

    return get_db().execute(
        """
        SELECT c.id, c.nome, c.foto_url
        FROM categorias AS c
        JOIN perfis_categorias AS pc ON pc.categoria_id = c.id
        JOIN perfis AS p ON p.id = pc.perfil_id
        WHERE p.usuario_id = ?
        ORDER BY c.nome
        """,
        (chef_id,)
    ).fetchall()


# Lista os pratos do cozinheiro
def produtos_do_chef(chef_id, incluir_inativos=False):
    """Pratos pelos quais o cozinheiro é responsável."""

    return get_db().execute(
        """
        SELECT
            pr.*,
            c.nome AS categoria_nome
        FROM produto_chefs AS pc
        JOIN produtos AS pr ON pr.id = pc.produto_id
        JOIN categorias AS c ON c.id = pr.categoria_id
        WHERE pc.chef_id = ? AND (pr.ativo OR ?)
        ORDER BY c.nome, pr.nome
        """,
        (chef_id, bool(incluir_inativos))
    ).fetchall()
