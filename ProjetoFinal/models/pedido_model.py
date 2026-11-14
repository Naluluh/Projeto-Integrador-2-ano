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


def inserir_endereco(pedido_id, endereco_id):
    # Insere o endereço no pedido.
    db = get_db()
    db.execute(
        """
        UPDATE pedidos
        SET endereco_id = ?
        WHERE id = ?
        """,
        (endereco_id, pedido_id)
    )
    db.commit()


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

    db.commit()


def _planejar_consumo(db, carrinho):
    """
    Verifica os ingredientes necessários e escolhe
    alternativas quando o estoque principal é insuficiente.

    Não altera o estoque. Apenas monta um plano de consumo.
    """

    itens = []
    estoques = {}
    consumos = {}

    for item in carrinho:

        produto_id = int(item["produto_id"])
        quantidade_pratos = int(item["quantidade"])

        if quantidade_pratos <= 0:
            raise ValueError("Quantidade de pratos inválida.")

        produto = db.execute("""
            SELECT *
            FROM produtos
            WHERE id = ?
        """, (produto_id,)).fetchone()

        if produto is None:
            raise ValueError("Um prato do pedido não existe mais.")

        ingredientes = db.execute("""
            SELECT
                pi.ingrediente_id,
                pi.quantidade,
                i.nome,
                i.estoque
            FROM produto_ingredientes pi
            JOIN ingredientes i
                ON i.id = pi.ingrediente_id
            WHERE pi.produto_id = ?
        """, (produto_id,)).fetchall()

        if not ingredientes:
            raise ValueError(
                f"O prato {produto['nome']} não possui ingredientes cadastrados."
            )

        for ingrediente in ingredientes:

            principal_id = ingrediente["ingrediente_id"]

            necessario = (
                ingrediente["quantidade"] * quantidade_pratos
            )

            # Estoque virtual: considera o consumo
            # dos outros pratos do mesmo pedido.
            estoque_atual = estoques.setdefault(
                principal_id,
                float(ingrediente["estoque"])
            )

            ingrediente_escolhido = None
            quantidade_consumida = necessario

            # Primeiro tenta utilizar o ingrediente principal.
            if estoque_atual >= necessario:

                ingrediente_escolhido = {
                    "id": principal_id,
                    "nome": ingrediente["nome"]
                }

            else:

                # Se não houver estoque, procura alternativas.
                alternativas = db.execute("""
                    SELECT
                        pa.ingrediente_alternativo_id,
                        pa.quantidade,
                        i.nome,
                        i.estoque
                    FROM produto_ingrediente_alternativas pa
                    JOIN ingredientes i
                        ON i.id = pa.ingrediente_alternativo_id
                    WHERE pa.produto_id = ?
                      AND pa.ingrediente_principal_id = ?
                    ORDER BY i.nome
                """, (
                    produto_id,
                    principal_id
                )).fetchall()

                for alternativa in alternativas:

                    alternativa_id = (
                        alternativa["ingrediente_alternativo_id"]
                    )

                    necessario_alternativo = (
                        alternativa["quantidade"] * quantidade_pratos
                    )

                    estoque_alternativo = estoques.setdefault(
                        alternativa_id,
                        float(alternativa["estoque"])
                    )

                    if estoque_alternativo >= necessario_alternativo:

                        ingrediente_escolhido = {
                            "id": alternativa_id,
                            "nome": alternativa["nome"]
                        }

                        quantidade_consumida = necessario_alternativo
                        break

            # Nenhuma opção disponível.
            if ingrediente_escolhido is None:

                raise ValueError(
                    f"{produto['nome']} está indisponível: "
                    f"faltam {ingrediente['nome']} "
                    "e não há alternativa suficiente."
                )

            ingrediente_id = ingrediente_escolhido["id"]

            # Atualiza o estoque virtual.
            estoques[ingrediente_id] -= quantidade_consumida

            # Agrupa o consumo por ingrediente.
            if ingrediente_id not in consumos:
                consumos[ingrediente_id] = {
                    "nome": ingrediente_escolhido["nome"],
                    "quantidade": 0
                }

            consumos[ingrediente_id]["quantidade"] += (
                quantidade_consumida
            )

        itens.append((produto, quantidade_pratos))

    return itens, consumos


def disponivel(produto_id, quantidade=1):
    """
    Verifica se é possível preparar determinada
    quantidade de um prato, considerando alternativas.
    """

    db = get_db()

    try:
        _planejar_consumo(db, [{
            "produto_id": produto_id,
            "quantidade": quantidade
        }])

        return True

    except ValueError:
        return False


def finalizar(usuario_id, carrinho):
    """
    Registra o pedido e desconta os ingredientes
    em uma única transação.
    """

    db = get_db()

    try:

        # Inicia uma transação compatível com PostgreSQL.
        db.execute("BEGIN")

        # Verifica todo o carrinho antes de alterar o estoque.
        itens, consumos = _planejar_consumo(db, carrinho)

        # Calcula o valor total.
        total = sum(
            produto["preco_centavos"] * quantidade
            for produto, quantidade in itens
        )

        # Cria o pedido.
        cursor = db.execute("""
            INSERT INTO pedidos (
                usuario_id,
                status,
                total_centavos
            )
            VALUES (?, ?, ?)
        """, (
            usuario_id,
            "espera",
            total
        ))

        pedido_id = cursor.lastrowid

        # Registra os pratos do pedido.
        for produto, quantidade in itens:

            subtotal = (
                produto["preco_centavos"] * quantidade
            )

            db.execute("""
                INSERT INTO itens_pedido (
                    pedido_id,
                    produto_id,
                    produto_nome,
                    preco_unitario_centavos,
                    quantidade,
                    subtotal_centavos
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pedido_id,
                produto["id"],
                produto["nome"],
                produto["preco_centavos"],
                quantidade,
                subtotal
            ))

        # Desconta os ingredientes utilizados.
        for ingrediente_id, dados in consumos.items():

            cursor = db.execute("""
                UPDATE ingredientes
                SET estoque = estoque - ?
                WHERE id = ?
                  AND estoque >= ?
            """, (
                dados["quantidade"],
                ingrediente_id,
                dados["quantidade"]
            ))

            # Proteção adicional contra estoque insuficiente.
            if cursor.rowcount != 1:
                raise ValueError(
                    f"Estoque insuficiente para {dados['nome']}."
                )

        # Confirma todas as operações.
        db.commit()

        return pedido_id

    except Exception:
        db.rollback()
        raise


def quantidade_total():
    # Conta quantos pedidos foram registrados.
    return get_db().execute(
        "SELECT COUNT(*) AS total FROM pedidos"
    ).fetchone()["total"]
