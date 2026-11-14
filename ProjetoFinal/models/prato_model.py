# Consultas dos pratos
"""Consultas e operações de produtos e suas relações."""

from database import get_db


FOTO_PADRAO = "images/fotos_perfil/produtos/template_produtos.jpeg"


# Lista os pratos, com busca opcional
def listar(busca="", incluir_inativos=True):
    db = get_db()
    termo = f"%{busca.strip()}%"
    return db.execute("""
        SELECT produtos.*, categorias.nome AS categoria_nome,
               (
                   SELECT COUNT(*) FROM produto_chefs
                   WHERE produto_chefs.produto_id = produtos.id
               ) AS qtd_chefs
        FROM produtos
        JOIN categorias ON produtos.categoria_id = categorias.id
        WHERE (norm(produtos.nome) LIKE norm(?) OR norm(categorias.nome) LIKE norm(?))
          AND (produtos.ativo OR ?)
        ORDER BY produtos.nome
    """, (termo, termo, bool(incluir_inativos))).fetchall()


# Deixa o prato visível ou oculto
def definir_ativo(produto_id, ativo):
    """Deixa o prato disponível (visível) ou indisponível (oculto).

    Não apaga nada: pedidos antigos continuam mostrando o prato.
    """
    db = get_db()
    db.execute(
        "UPDATE produtos SET ativo = ? WHERE id = ?",
        (bool(ativo), produto_id)
    )
    db.commit()


# Cadastra um prato
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


# Atualiza um prato
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


# Lista os pratos disponíveis para pedir
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
        WHERE produtos.ativo
        GROUP BY produtos.id
        ORDER BY produtos.nome
    """).fetchall()


# Lista os pratos de uma categoria
def listar_por_categoria(categoria_id, incluir_inativos=False):
    return get_db().execute("""
        SELECT produtos.*, categorias.nome AS categoria_nome
        FROM produtos
        JOIN categorias ON produtos.categoria_id = categorias.id
        WHERE produtos.categoria_id = ?
          AND (produtos.ativo OR ?)
        ORDER BY produtos.nome
    """, (categoria_id, bool(incluir_inativos))).fetchall()


# Conta os pratos
def quantidade_total():
    # Conta quantos pratos estão cadastrados (painel inicial).
    return get_db().execute(
        "SELECT COUNT(*) AS total FROM produtos"
    ).fetchone()["total"]


# Lista as categorias
def listar_categorias():
    return get_db().execute("""
        SELECT id, nome, foto_url
        FROM categorias
        ORDER BY nome
    """).fetchall()


# Busca um prato
def buscar(id_prato):
    return get_db().execute("""
        SELECT produtos.*, categorias.nome AS categoria_nome
        FROM produtos
        JOIN categorias ON produtos.categoria_id = categorias.id
        WHERE produtos.id = ?
    """, (id_prato,)).fetchone()


# Lista os ingredientes do prato e as alternativas
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
                CAST(ia.id AS TEXT) || ':' || ia.nome || ':'
                || CAST(pia.quantidade AS TEXT),
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
        GROUP BY pi.produto_id, pi.ingrediente_id, pi.quantidade,
                 i.nome, i.unidade
        ORDER BY i.nome
    """, (produto_id,)).fetchall()


# Monta a receita para preencher o formulário
def listar_receita(produto_id):
    """Ingredientes da receita (com a 1ª alternativa) para preencher o formulário."""
    return get_db().execute("""
        SELECT
            pi.ingrediente_id,
            pi.quantidade,
            pia.ingrediente_alternativo_id AS alternativo_id,
            pia.quantidade AS quantidade_alternativa
        FROM produto_ingredientes AS pi
        JOIN ingredientes AS i ON i.id = pi.ingrediente_id
        LEFT JOIN produto_ingrediente_alternativas AS pia
            ON pia.produto_id = pi.produto_id
            AND pia.ingrediente_principal_id = pi.ingrediente_id
        WHERE pi.produto_id = ?
        ORDER BY i.nome
    """, (produto_id,)).fetchall()


# Lista as alternativas de cada ingrediente
def listar_alternativas(produto_id):
    """Alternativas de cada ingrediente (para a página de detalhes)."""
    return get_db().execute("""
        SELECT
            pia.ingrediente_principal_id,
            ia.nome,
            ia.unidade,
            pia.quantidade
        FROM produto_ingrediente_alternativas AS pia
        JOIN ingredientes AS ia ON ia.id = pia.ingrediente_alternativo_id
        WHERE pia.produto_id = ?
        ORDER BY ia.nome
    """, (produto_id,)).fetchall()


# Lista os cozinheiros do prato
def listar_chefs_produto(produto_id):
    return get_db().execute("""
        SELECT chef_id
        FROM produto_chefs
        WHERE produto_id = ?
    """, (produto_id,)).fetchall()


# Salva ingredientes, alternativas e cozinheiros do prato
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

    categoria = db.execute(
        "SELECT categoria_id FROM produtos WHERE id = ?",
        (produto_id,)
    ).fetchone()

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

        # Quem faz o prato passa a constar como responsável pela categoria
        # (se já tiver perfil), mantendo as duas listas coerentes.
        db.execute("""
            INSERT INTO perfis_categorias (perfil_id, categoria_id)
            SELECT id, ? FROM perfis WHERE usuario_id = ?
            ON CONFLICT DO NOTHING
        """, (categoria["categoria_id"], chef_id))


# Cadastra o prato com seus ingredientes e cozinheiros
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


# Atualiza o prato com seus ingredientes e cozinheiros
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


# Exclui um prato
def excluir(produto_id):
    db = get_db()
    try:
        db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
