"""Model de pedidos e seus itens."""

from database import get_db


def listar():
    # Lista todos os pedidos.
    # Também obtém o nome do funcionário responsável.
    return get_db().execute(
        """
        SELECT
            p.*,
            f.nome AS funcionario_nome
        FROM pedidos p
        JOIN funcionarios f
            ON f.id = p.funcionario_id
        ORDER BY p.criado_em DESC, p.id DESC
        """
    ).fetchall()


def buscar(pedido_id):
    # Busca um pedido específico.
    return get_db().execute(
        """
        SELECT
            p.*,
            f.nome AS funcionario_nome
        FROM pedidos p
        JOIN funcionarios f
            ON f.id = p.funcionario_id
        WHERE p.id = ?
        """,
        (pedido_id,)
    ).fetchone()


def listar_itens(pedido_id):
    # Lista todos os pratos pertencentes ao pedido.
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


def finalizar(funcionario_id, carrinho):
    """Grava o pedido e atualiza os ingredientes em uma transação."""

    # Obtém a conexão.
    db = get_db()

    try:
        itens = []

        # Verifica todos os pratos do carrinho.
        for item in carrinho:

            prato = db.execute(
                "SELECT * FROM pratos WHERE id = ?",
                (item["prato_id"],)
            ).fetchone()

            if prato is None:
                raise ValueError(
                    f"O prato {item['nome']} não existe mais."
                )

            # Busca os ingredientes necessários.
            ingredientes = db.execute(
                """
                SELECT
                    pi.ingrediente_id,
                    pi.quantidade,
                    i.nome,
                    i.estoque
                FROM prato_ingredientes pi
                JOIN ingredientes i
                    ON i.id = pi.ingrediente_id
                WHERE pi.prato_id = ?
                """,
                (item["prato_id"],)
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

            itens.append((prato, item["quantidade"], ingredientes))

        # Calcula o total do pedido.
        total = sum(
            prato["preco_centavos"] * quantidade
            for prato, quantidade, _ in itens
        )

        # Cria o pedido inicialmente aguardando preparo.
        cursor = db.execute(
            """
            INSERT INTO pedidos
                (funcionario_id, status, total_centavos)
            VALUES (?, ?, ?)
            """,
            (funcionario_id, "espera", total)
        )

        pedido_id = cursor.lastrowid

        # Insere cada item do pedido.
        for prato, quantidade, ingredientes in itens:

            subtotal = (
                prato["preco_centavos"]
                * quantidade
            )

            db.execute(
                """
                INSERT INTO itens_pedido
                    (
                        pedido_id,
                        prato_id,
                        prato_nome,
                        preco_unitario_centavos,
                        quantidade,
                        subtotal_centavos
                    )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    pedido_id,
                    prato["id"],
                    prato["nome"],
                    prato["preco_centavos"],
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