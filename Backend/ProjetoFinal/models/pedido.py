"""Model de pedidos e seus itens."""

from database import get_db


def listar():
    # Lista todos os pedidos.
    # Também obtém o nome do funcionário responsável.
    return get_db().execute(
        """
        SELECT
            p.*,
            f.nome AS usuario_nome
        FROM pedidos p
        JOIN usuarios f
            ON f.id = p.usuario_id
        ORDER BY p.criado_em DESC, p.id DESC
        """
    ).fetchall()


def buscar(pedido_id):
    # Busca um pedido específico.
    return get_db().execute(
        """
        SELECT
            p.*,
            f.nome AS usuario_nome
        FROM pedidos p
        JOIN usuarios f
            ON f.id = p.usuario_id
        WHERE p.id = ?
        """,
        (pedido_id,)
    ).fetchone()


def listar_itens(pedido_id):
    # Lista todos os produtos pertencentes ao pedido.
    return get_db().execute(
        """
        SELECT *
        FROM itens_pedido
        WHERE pedido_id = ?
        ORDER BY id
        """,
        (pedido_id,)
    ).fetchall()


def atualizar_status(pedido_id, status):
    # Obtém a conexão.
    db = get_db()

    # Altera o estado do pedido.
    db.execute(
        """
        UPDATE pedidos
        SET status = ?
        WHERE id = ?
        """,
        (status, pedido_id)
    )

    # Confirma a alteração.
    db.commit()


def finalizar(usuario_id, carrinho):
    """Grava o pedido e atualiza os ingredientes em uma transação."""

    # Obtém a conexão.
    db = get_db()

    try:
        itens = []

        # Verifica todos os produtos do carrinho.
        for item in carrinho:

            produto = db.execute(
                "SELECT * FROM produtos WHERE id = ?",
                (item["produto_id"],)
            ).fetchone()

            if produto is None:
                raise ValueError(
                    f"O produto {item['nome']} não existe mais."
                )

            # Busca os ingredientes necessários.
            ingredientes = db.execute(
                """
                SELECT
                    pi.ingrediente_id,
                    pi.quantidade,
                    i.nome,
                    i.estoque
                FROM produto_ingredientes pi
                JOIN ingredientes i
                    ON i.id = pi.ingrediente_id
                WHERE pi.produto_id = ?
                """,
                (item["produto_id"],)
            ).fetchall()

            # Verifica se há ingredientes suficientes.
            for ingrediente in ingredientes:
                necessario = (
                    ingrediente["quantidade"]
                    * item["quantidade"]
                )

                if ingrediente["estoque"] < necessario:
                    raise ValueError(
                        f"Estoque insuficiente para "
                        f"{ingrediente['nome']}."
                    )

            itens.append((produto, item["quantidade"], ingredientes))

        # Calcula o total do pedido.
        total = sum(
            produto["preco_centavos"] * quantidade
            for produto, quantidade, _ in itens
        )

        # Cria o pedido inicialmente aguardando preparo.
        cursor = db.execute(
            """
            INSERT INTO pedidos
                (usuario_id, status, total_centavos)
            VALUES (?, ?, ?)
            """,
            (usuario_id, "espera", total)
        )

        pedido_id = cursor.lastrowid

        # Insere cada item do pedido.
        for produto, quantidade, ingredientes in itens:

            subtotal = (
                produto["preco_centavos"]
                * quantidade
            )

            db.execute(
                """
                INSERT INTO itens_pedido
                    (
                        pedido_id,
                        produto_id,
                        produto_nome,
                        preco_unitario_centavos,
                        quantidade,
                        subtotal_centavos
                    )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    pedido_id,
                    produto["id"],
                    produto["nome"],
                    produto["preco_centavos"],
                    quantidade,
                    subtotal
                )
            )

            # Baixa os ingredientes utilizados.
            for ingrediente in ingredientes:

                quantidade_usada = (
                    ingrediente["quantidade"]
                    * quantidade
                )

                db.execute(
                    """
                    UPDATE ingredientes
                    SET estoque = estoque - ?
                    WHERE id = ?
                    """,
                    (
                        quantidade_usada,
                        ingrediente["ingrediente_id"]
                    )
                )

        # Confirma todas as operações.
        db.commit()

        return pedido_id

    except Exception:
        # Se alguma operação falhar,
        # desfaz todas as alterações da transação.
        db.rollback()
        raise


def quantidade_total():
    # Conta quantos pedidos foram registrados.
    return get_db().execute(
        "SELECT COUNT(*) AS total FROM pedidos"
    ).fetchone()["total"]