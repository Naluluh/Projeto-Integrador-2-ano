"""Consultas e operações de produtos e suas relações."""

from database import get_db


FOTO_PADRAO = "images/fotos_perfil/produtos/template_produtos.jpeg"


def listar(busca=""):
    db = get_db()
    termo = f"%{busca.strip()}%"
    return db.execute("""
        SELECT produtos.*, categorias.nome AS categoria_nome
        FROM produtos
        JOIN categorias ON produtos.categoria_id = categorias.id
        WHERE produtos.nome LIKE ? OR categorias.nome LIKE ?
        ORDER BY produtos.nome COLLATE NOCASE
    """, (termo, termo)).fetchall()


def criar(nome, descricao, categoria_id, preco_centavos,
          modo_preparo, foto_url=None):
    db = get_db()
    db.execute("""
        INSERT INTO produtos
            (nome, descricao, categoria_id, preco_centavos,
             modo_preparo, foto_url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        nome, descricao, categoria_id, preco_centavos,
        modo_preparo, foto_url or FOTO_PADRAO
    ))
    db.commit()


def atualizar(produto_id, nome, descricao, categoria_id,
              preco_centavos, modo_preparo, foto_url=None):
    db = get_db()
    if foto_url:
        db.execute("""
            UPDATE produtos
            SET nome=?, descricao=?, categoria_id=?,
                preco_centavos=?, modo_preparo=?, foto_url=?
            WHERE id=?
        """, (nome, descricao, categoria_id, preco_centavos,
              modo_preparo, foto_url, produto_id))
    else:
        db.execute("""
            UPDATE produtos
            SET nome=?, descricao=?, categoria_id=?,
                preco_centavos=?, modo_preparo=?
            WHERE id=?
        """, (nome, descricao, categoria_id, preco_centavos,
              modo_preparo, produto_id))
    db.commit()


def listar_para_pedido():
    return get_db().execute("""
        SELECT produtos.*,
               GROUP_CONCAT(usuarios.nome, ', ') AS chef_nome
        FROM produtos
        LEFT JOIN produto_chefs
            ON produtos.id = produto_chefs.produto_id
        LEFT JOIN usuarios
            ON produto_chefs.chef_id = usuarios.id
            AND usuarios.cargo = 'cozinheiro'
        GROUP BY produtos.id
        ORDER BY produtos.nome COLLATE NOCASE
    """).fetchall()


def listar_por_categoria(categoria_id):
    return get_db().execute("""
        SELECT produtos.*, categorias.nome AS categoria_nome
        FROM produtos
        JOIN categorias ON produtos.categoria_id = categorias.id
        WHERE produtos.categoria_id = ?
        ORDER BY produtos.nome COLLATE NOCASE
    """, (categoria_id,)).fetchall()


def listar_categorias():
    return get_db().execute("""
        SELECT id, nome, foto_url
        FROM categorias
        ORDER BY nome COLLATE NOCASE
    """).fetchall()


def buscar(id_prato):
    return get_db().execute("""
        SELECT produtos.*, categorias.nome AS categoria_nome
        FROM produtos
        JOIN categorias ON produtos.categoria_id = categorias.id
        WHERE produtos.id = ?
    """, (id_prato,)).fetchone()


def listar_ingredientes(produto_id):
    """Lista ingredientes da receita e suas alternativas cadastradas."""
    db = get_db()
    return db.execute("""
        SELECT
            pi.ingrediente_id,
            i.nome,
            i.unidade,
            pi.quantidade,
            GROUP_CONCAT(
                ia.id || ':' || ia.nome || ':' || pia.quantidade,
                '|'
            ) AS alternativas
        FROM produto_ingredientes AS pi
        JOIN ingredientes AS i ON i.id = pi.ingrediente_id
        LEFT JOIN produto_ingrediente_alternativas AS pia
            ON pia.produto_id = pi.produto_id
            AND pia.ingrediente_principal_id = pi.ingrediente_id
        LEFT JOIN ingredientes AS ia
            ON ia.id = pia.ingrediente_alternativo_id
        WHERE pi.produto_id = ?
        GROUP BY pi.produto_id, pi.ingrediente_id
        ORDER BY i.nome COLLATE NOCASE
    """, (produto_id,)).fetchall()


def listar_chefs_produto(produto_id):
    return get_db().execute("""
        SELECT chef_id
        FROM produto_chefs
        WHERE produto_id = ?
    """, (produto_id,)).fetchall()


def _salvar_relacoes(db, produto_id, ingredientes, chefs_ids):
    ids_principais = set()

    for item in ingredientes:
        ingrediente_id = item.get("ingrediente_id")

        if ingrediente_id is None:
            cursor = db.execute("""
                INSERT INTO ingredientes (nome, unidade, estoque)
                VALUES (?, ?, ?)
            """, (
                item["novo_nome"],
                item["nova_unidade"],
                item["novo_estoque"]
            ))
            ingrediente_id = cursor.lastrowid

        ingrediente_id = int(ingrediente_id)
        if ingrediente_id in ids_principais:
            raise ValueError("Um ingrediente não pode ser repetido na receita.")
        ids_principais.add(ingrediente_id)

        existe = db.execute(
            "SELECT 1 FROM ingredientes WHERE id = ?",
            (ingrediente_id,)
        ).fetchone()
        if existe is None:
            raise ValueError("Ingrediente selecionado não existe.")

        db.execute("""
            INSERT INTO produto_ingredientes
                (produto_id, ingrediente_id, quantidade)
            VALUES (?, ?, ?)
        """, (produto_id, ingrediente_id, item["quantidade"]))

        alternativo_id = item.get("alternativo_id")
        if alternativo_id:
            alternativo_id = int(alternativo_id)
            if alternativo_id == ingrediente_id:
                raise ValueError("O ingrediente alternativo deve ser diferente do principal.")

            alternativo = db.execute(
                "SELECT 1 FROM ingredientes WHERE id = ?",
                (alternativo_id,)
            ).fetchone()
            if alternativo is None:
                raise ValueError("Ingrediente alternativo não existe.")

            db.execute("""
                INSERT INTO produto_ingrediente_alternativas (
                    produto_id,
                    ingrediente_principal_id,
                    ingrediente_alternativo_id,
                    quantidade
                )
                VALUES (?, ?, ?, ?)
            """, (
                produto_id,
                ingrediente_id,
                alternativo_id,
                item.get("quantidade_alternativa") or item["quantidade"]
            ))

    db.execute(
        "DELETE FROM produto_chefs WHERE produto_id = ?",
        (produto_id,)
    )

    for chef_id in set(int(valor) for valor in chefs_ids):
        chef = db.execute("""
            SELECT id FROM usuarios
            WHERE id = ? AND cargo = 'cozinheiro'
        """, (chef_id,)).fetchone()
        if chef is None:
            raise ValueError("Cozinheiro inválido.")

        db.execute("""
            INSERT INTO produto_chefs (produto_id, chef_id)
            VALUES (?, ?)
        """, (produto_id, chef_id))


def criar_com_relacoes(nome, descricao, categoria_id, preco_centavos,
                       modo_preparo, ingredientes, chefs_ids, foto_url=None):
    db = get_db()
    try:
        cursor = db.execute("""
            INSERT INTO produtos
                (nome, descricao, categoria_id, preco_centavos,
                 modo_preparo, foto_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            nome, descricao, categoria_id, preco_centavos,
            modo_preparo, foto_url or FOTO_PADRAO
        ))
        produto_id = cursor.lastrowid
        _salvar_relacoes(db, produto_id, ingredientes, chefs_ids)
        db.commit()
        return produto_id
    except Exception:
        db.rollback()
        raise


def atualizar_com_relacoes(produto_id, nome, descricao, categoria_id,
                           preco_centavos, modo_preparo, ingredientes,
                           chefs_ids, foto_url=None):
    db = get_db()
    try:
        if foto_url:
            db.execute("""
                UPDATE produtos
                SET nome=?, descricao=?, categoria_id=?,
                    preco_centavos=?, modo_preparo=?, foto_url=?
                WHERE id=?
            """, (nome, descricao, categoria_id, preco_centavos,
                  modo_preparo, foto_url, produto_id))
        else:
            db.execute("""
                UPDATE produtos
                SET nome=?, descricao=?, categoria_id=?,
                    preco_centavos=?, modo_preparo=?
                WHERE id=?
            """, (nome, descricao, categoria_id, preco_centavos,
                  modo_preparo, produto_id))

        # As alternativas dependem da relação principal; removemos primeiro.
        db.execute(
            "DELETE FROM produto_ingrediente_alternativas WHERE produto_id=?",
            (produto_id,)
        )
        db.execute(
            "DELETE FROM produto_ingredientes WHERE produto_id=?",
            (produto_id,)
        )
        _salvar_relacoes(db, produto_id, ingredientes, chefs_ids)
        db.commit()
    except Exception:
        db.rollback()
        raise


def excluir(produto_id):
    db = get_db()
    try:
        db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
