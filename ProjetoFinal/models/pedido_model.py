
"""Model responsável pelos pedidos e seus itens."""

from database import get_db


def listar():
    """Lista todos os pedidos, com cliente e cozinheiro."""

    db = get_db()

    return db.execute("""
        SELECT
            p.*,
            cliente.nome AS usuario_nome,
            chef.nome AS chef_nome
        FROM pedidos AS p

        INNER JOIN usuarios AS cliente
            ON cliente.id = p.usuario_id

        LEFT JOIN usuarios AS chef
            ON chef.id = p.chef_id

        ORDER BY p.criado_em DESC, p.id DESC
    """).fetchall()


def listar_por_cliente(usuario_id):
    """Lista somente os pedidos de determinado cliente."""

    db = get_db()

    return db.execute("""
        SELECT
            p.*,
            cliente.nome AS usuario_nome,
            chef.nome AS chef_nome
        FROM pedidos AS p

        INNER JOIN usuarios AS cliente
            ON cliente.id = p.usuario_id

        LEFT JOIN usuarios AS chef
            ON chef.id = p.chef_id

        WHERE p.usuario_id = ?

        ORDER BY p.criado_em DESC, p.id DESC
    """, (usuario_id,)).fetchall()


def listar_por_chef(chef_id):
    """Lista somente os pedidos destinados ao cozinheiro."""

    db = get_db()

    return db.execute("""
        SELECT
            p.*,
            cliente.nome AS usuario_nome,
            chef.nome AS chef_nome
        FROM pedidos AS p

        INNER JOIN usuarios AS cliente
            ON cliente.id = p.usuario_id

        LEFT JOIN usuarios AS chef
            ON chef.id = p.chef_id

        WHERE p.chef_id = ?

        ORDER BY p.criado_em DESC, p.id DESC
    """, (chef_id,)).fetchall()


def buscar(pedido_id):
    """Busca um pedido com os dados do cliente e cozinheiro."""

    db = get_db()

    return db.execute("""
        SELECT
            p.*,
            cliente.nome AS usuario_nome,
            chef.nome AS chef_nome
        FROM pedidos AS p

        INNER JOIN usuarios AS cliente
            ON cliente.id = p.usuario_id

        LEFT JOIN usuarios AS chef
            ON chef.id = p.chef_id

        WHERE p.id = ?
    """, (pedido_id,)).fetchone()


def inserir_endereco(pedido_id, endereco_id):
    """Associa um endereço ao pedido."""

    db = get_db()

    db.execute("""
        UPDATE pedidos
        SET endereco_id = ?
        WHERE id = ?
    """, (endereco_id, pedido_id))

    db.commit()


def listar_itens(pedido_id):
    """Lista os produtos pertencentes ao pedido."""

    db = get_db()

    return db.execute("""
        SELECT *
        FROM itens_pedido
        WHERE pedido_id = ?
        ORDER BY id
    """, (pedido_id,)).fetchall()


def atualizar_status(pedido_id, status):
    """Atualiza o status e a data de atualização."""

    db = get_db()

    db.execute("""
        UPDATE pedidos
        SET
            status = ?,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, pedido_id))

    db.commit()


def cancelar(pedido_id):
    """
    Cancela um pedido sem devolver ingredientes ao estoque.
    """

    db = get_db()

    pedido = db.execute("""
        SELECT status
        FROM pedidos
        WHERE id = ?
    """, (pedido_id,)).fetchone()

    if pedido is None:
        raise ValueError("Pedido não encontrado.")

    if pedido["status"] == "entregue":
        raise ValueError("Não é possível cancelar um pedido entregue.")

    if pedido["status"] == "cancelado":
        raise ValueError("Este pedido já foi cancelado.")

    db.execute("""
        UPDATE pedidos
        SET
            status = 'cancelado',
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (pedido_id,))

    # Não devolve os ingredientes ao estoque.
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
            FROM produto_ingredientes AS pi

            INNER JOIN ingredientes AS i
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

            estoque_atual = estoques.setdefault(
                principal_id,
                float(ingrediente["estoque"])
            )

            ingrediente_escolhido = None
            quantidade_consumida = necessario

            # Tenta utilizar primeiro o ingrediente principal.
            if estoque_atual >= necessario:

                ingrediente_escolhido = {
                    "id": principal_id,
                    "nome": ingrediente["nome"]
                }

            else:

                # Procura ingredientes alternativos.
                alternativas = db.execute("""
                    SELECT
                        pa.ingrediente_alternativo_id,
                        pa.quantidade,
                        i.nome,
                        i.estoque
                    FROM produto_ingrediente_alternativas AS pa

                    INNER JOIN ingredientes AS i
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
    """Verifica se existe estoque para preparar um produto."""

    db = get_db()

    try:

        _planejar_consumo(db, [{
            "produto_id": produto_id,
            "quantidade": quantidade
        }])

        return True

    except ValueError:
        return False


def finalizar(usuario_id, chef_id, carrinho, endereco_id):
    """
    Registra o pedido com o cozinheiro e o endereço selecionados
    e desconta os ingredientes em uma única transação.
    """

    db = get_db()

    try:
        db.execute("BEGIN IMMEDIATE")

        # 1. Valida o cozinheiro.
        chef = db.execute("""
            SELECT id FROM usuarios
            WHERE id = ? AND cargo = 'cozinheiro'
        """, (chef_id,)).fetchone()

        if chef is None:
            raise ValueError("Cozinheiro selecionado inválido.")

        # 2. Valida o cliente.
        cliente = db.execute(
            "SELECT id FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()

        if cliente is None:
            raise ValueError("Usuário não encontrado.")

        # 3. Valida o endereço (precisa ser do próprio cliente).
        endereco = db.execute("""
            SELECT id FROM enderecos
            WHERE id = ? AND usuario_id = ?
        """, (endereco_id, usuario_id)).fetchone()

        if endereco is None:
            raise ValueError("Endereço inválido.")

        # 4. Valida se o cozinheiro prepara todos os produtos.
        for item in carrinho:
            relacionado = db.execute("""
                SELECT 1 FROM produto_chefs
                WHERE produto_id = ? AND chef_id = ?
            """, (int(item["produto_id"]), chef_id)).fetchone()

            if relacionado is None:
                raise ValueError(
                    f"O cozinheiro selecionado não prepara "
                    f"o produto {item['nome']}."
                )

        # 5. Planeja o consumo (não altera o estoque ainda).
        itens, consumos = _planejar_consumo(db, carrinho)

        # 6. Calcula o total ANTES de usá-lo no INSERT.
        total = sum(
            produto["preco_centavos"] * quantidade
            for produto, quantidade in itens
        )

        # 7. Registra o pedido.
        cursor = db.execute("""
            INSERT INTO pedidos (
                usuario_id,
                endereco_id,
                chef_id,
                status,
                total_centavos
            )
            VALUES (?, ?, ?, ?, ?)
        """, (usuario_id, endereco_id, chef_id, "em preparo", total))

        pedido_id = cursor.lastrowid

        # 8. Registra os itens.
        for produto, quantidade in itens:
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
                produto["preco_centavos"] * quantidade
            ))

        # 9. Desconta os ingredientes.
        for ingrediente_id, dados in consumos.items():
            cursor = db.execute("""
                UPDATE ingredientes
                SET estoque = estoque - ?
                WHERE id = ? AND estoque >= ?
            """, (
                dados["quantidade"],
                ingrediente_id,
                dados["quantidade"]
            ))

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Estoque insuficiente para {dados['nome']}."
                )

        db.commit()
        return pedido_id

    except Exception:
        db.rollback()
        raise


def quantidade_total():
    """Conta quantos pedidos foram registrados."""

    return get_db().execute("""
        SELECT COUNT(*) AS total
        FROM pedidos
    """).fetchone()["total"]

def quantidade_visivel(cargo, usuario_id):
    """
    Conta os pedidos que a pessoa pode ver:
    - administrador: todos
    - cliente: somente os próprios
    - cozinheiro: somente os destinados a ele
    Usa as mesmas regras de listar(), listar_por_cliente() e listar_por_chef().
    """

    db = get_db()

    if cargo == "administrador":
        consulta = "SELECT COUNT(*) AS total FROM pedidos"
        parametros = ()

    elif cargo == "cliente":
        consulta = "SELECT COUNT(*) AS total FROM pedidos WHERE usuario_id = ?"
        parametros = (usuario_id,)

    elif cargo == "cozinheiro":
        consulta = "SELECT COUNT(*) AS total FROM pedidos WHERE chef_id = ?"
        parametros = (usuario_id,)

        # "SELECT COUNT(*) AS total FROM pedidos "
        # "WHERE chef_id = ? AND status NOT IN ('entregue', 'cancelado')"

    else:
        return 0

    return db.execute(consulta, parametros).fetchone()["total"]
