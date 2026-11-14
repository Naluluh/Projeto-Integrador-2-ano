
"""Model responsável pelos pedidos e seus itens."""

from database import get_db


def listar():
    """Lista todos os pedidos, com cliente e cozinheiro."""

    db = get_db()

    return db.execute("""
        SELECT
            p.*,
            EXISTS (
                SELECT 1
                FROM itens_pedido_substituicoes AS s
                INNER JOIN itens_pedido AS ip ON ip.id = s.item_pedido_id
                WHERE ip.pedido_id = p.id
            ) AS usou_alternativo,
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
            EXISTS (
                SELECT 1
                FROM itens_pedido_substituicoes AS s
                INNER JOIN itens_pedido AS ip ON ip.id = s.item_pedido_id
                WHERE ip.pedido_id = p.id
            ) AS usou_alternativo,
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
            EXISTS (
                SELECT 1
                FROM itens_pedido_substituicoes AS s
                INNER JOIN itens_pedido AS ip ON ip.id = s.item_pedido_id
                WHERE ip.pedido_id = p.id
            ) AS usou_alternativo,
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
            EXISTS (
                SELECT 1
                FROM itens_pedido_substituicoes AS s
                INNER JOIN itens_pedido AS ip ON ip.id = s.item_pedido_id
                WHERE ip.pedido_id = p.id
            ) AS usou_alternativo,
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


# Tolerância para comparar decimais (ex.: 0,1 + 0,2)
_EPS = 1e-9


def _quantos_cabem(estoque, por_porcao):
    """Quantas porções inteiras o estoque permite preparar."""
    return int((estoque + _EPS) // por_porcao)


def _porcoes(n):
    return f"{n} porção" if n == 1 else f"{n} porções"


def _planejar_consumo(db, carrinho):
    """
    Verifica o estoque de cada ingrediente do carrinho e decide, porção por
    porção, se usa o ingrediente padrão ou o alternativo.

    Exemplo: 5 pratos pedidos, estoque padrão para 3 e alternativo para 2
    -> 3 porções com o padrão e 2 com o alternativo, no mesmo pedido.

    Não altera o estoque: apenas devolve o plano.

    Retorna (itens, consumos):
      itens     -> lista de {"produto", "quantidade", "substituicoes"}
      consumos  -> {ingrediente_id: {"nome", "unidade", "quantidade"}}
    """

    itens = []
    estoques = {}
    consumos = {}

    def estoque_virtual(ingrediente_id, valor_inicial):
        # O estoque é gasto só na conta, porque o carrinho pode ter
        # vários pratos com o mesmo ingrediente
        return estoques.setdefault(ingrediente_id, float(valor_inicial))

    def consumir(ingrediente_id, nome, unidade, quantidade):
        estoques[ingrediente_id] -= quantidade
        registro = consumos.setdefault(ingrediente_id, {
            "nome": nome, "unidade": unidade, "quantidade": 0.0
        })
        registro["quantidade"] += quantidade

    for item in carrinho:

        produto_id = int(item["produto_id"])
        quantidade_pratos = int(item["quantidade"])

        if quantidade_pratos <= 0:
            raise ValueError("Quantidade de pratos inválida.")

        produto = db.execute("""
            SELECT * FROM produtos WHERE id = ?
        """, (produto_id,)).fetchone()

        if produto is None:
            raise ValueError("Um prato do pedido não existe mais.")

        if not produto["ativo"]:
            raise ValueError(
                f"{produto['nome']} está indisponível no momento."
            )

        ingredientes = db.execute("""
            SELECT
                pi.ingrediente_id,
                pi.quantidade,
                i.nome,
                i.unidade,
                i.estoque
            FROM produto_ingredientes AS pi
            INNER JOIN ingredientes AS i ON i.id = pi.ingrediente_id
            WHERE pi.produto_id = ?
            ORDER BY i.nome
        """, (produto_id,)).fetchall()

        if not ingredientes:
            raise ValueError(
                f"O prato {produto['nome']} não possui ingredientes cadastrados."
            )

        # Alternativas do prato, agrupadas pelo ingrediente principal.
        alternativas = {}

        for alt in db.execute("""
            SELECT
                pa.ingrediente_principal_id,
                pa.ingrediente_alternativo_id,
                pa.quantidade,
                i.nome,
                i.unidade,
                i.estoque
            FROM produto_ingrediente_alternativas AS pa
            INNER JOIN ingredientes AS i ON i.id = pa.ingrediente_alternativo_id
            WHERE pa.produto_id = ?
            ORDER BY i.nome
        """, (produto_id,)).fetchall():
            alternativas.setdefault(
                alt["ingrediente_principal_id"], []
            ).append(alt)

        substituicoes = []

        for ing in ingredientes:

            principal_id = ing["ingrediente_id"]
            restantes = quantidade_pratos

            # 1) Usa o ingrediente padrão enquanto o estoque permitir.
            disponivel_padrao = estoque_virtual(principal_id, ing["estoque"])
            com_padrao = min(
                restantes,
                _quantos_cabem(disponivel_padrao, ing["quantidade"])
            )

            if com_padrao > 0:
                consumir(
                    principal_id, ing["nome"], ing["unidade"],
                    com_padrao * ing["quantidade"]
                )
                restantes -= com_padrao

            # 2) O que faltou é feito com o(s) ingrediente(s) alternativo(s).
            for alt in alternativas.get(principal_id, []):

                if restantes == 0:
                    break

                alt_id = alt["ingrediente_alternativo_id"]
                disponivel_alt = estoque_virtual(alt_id, alt["estoque"])
                com_alt = min(
                    restantes,
                    _quantos_cabem(disponivel_alt, alt["quantidade"])
                )

                if com_alt > 0:
                    quantidade_alt = com_alt * alt["quantidade"]
                    consumir(alt_id, alt["nome"], alt["unidade"], quantidade_alt)
                    restantes -= com_alt

                    substituicoes.append({
                        "original": ing["nome"],
                        "alternativo": alt["nome"],
                        "unidade": alt["unidade"],
                        "porcoes": com_alt,
                        "quantidade": quantidade_alt
                    })

            # 3) Se ainda sobrou porção sem ingrediente, o prato não sai.
            if restantes > 0:
                possiveis = quantidade_pratos - restantes

                if possiveis == 0:
                    raise ValueError(
                        f"{produto['nome']} está indisponível: faltam "
                        f"{ing['nome']} e não há alternativa suficiente."
                    )

                raise ValueError(
                    f"Estoque insuficiente para {_porcoes(quantidade_pratos)} "
                    f"de {produto['nome']}: faltam {ing['nome']} e não há "
                    f"alternativa suficiente. No momento só é possível "
                    f"preparar {_porcoes(possiveis)}."
                )

        itens.append({
            "produto": produto,
            "quantidade": quantidade_pratos,
            "substituicoes": substituicoes
        })

    return itens, consumos


def planejar(carrinho):
    """Planeja o consumo do carrinho (sem alterar o estoque)."""

    return _planejar_consumo(get_db(), carrinho)


def mensagens_substituicao(item_plano):
    """Textos explicando quais porções usarão ingrediente alternativo."""

    total = item_plano["quantidade"]
    nome = item_plano["produto"]["nome"]
    por_original = {}

    for sub in item_plano["substituicoes"]:
        por_original.setdefault(sub["original"], []).append(sub)

    mensagens = []

    for original, subs in por_original.items():
        com_alt = sum(sub["porcoes"] for sub in subs)
        padrao = total - com_alt
        nomes = " e ".join(sub["alternativo"] for sub in subs)

        if padrao == 0:
            mensagens.append(
                f"{nome}: sem estoque de {original}, as {_porcoes(com_alt)} "
                f"serão feitas com {nomes} (ingrediente alternativo)."
            )
        else:
            mensagens.append(
                f"{nome}: {_porcoes(padrao)} com {original} (padrão) e "
                f"{_porcoes(com_alt)} com {nomes} no lugar de {original}, "
                f"pois o estoque do ingrediente padrão não cobre todas."
            )

    return mensagens


def ids_ativos(ids):
    """Dos ids informados, devolve os pratos que ainda estão disponíveis."""

    ids = [int(i) for i in ids]

    if not ids:
        return set()

    marcadores = ",".join("?" for _ in ids)

    linhas = get_db().execute(
        f"SELECT id FROM produtos WHERE ativo AND id IN ({marcadores})",
        tuple(ids)
    ).fetchall()

    return {linha["id"] for linha in linhas}


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

    Devolve (pedido_id, avisos), onde avisos explica o uso de
    ingredientes alternativos (lista de textos).
    """

    db = get_db()

    try:
        # A transação abre na primeira consulta e termina no commit/rollback

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

        # 5. Planeja o consumo (sem mexer no estoque) e vê se algum prato ficou indisponível
        itens, consumos = _planejar_consumo(db, carrinho)

        # 6. Calcula o total ANTES de usá-lo no INSERT.
        total = sum(
            i["produto"]["preco_centavos"] * i["quantidade"]
            for i in itens
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
        """, (usuario_id, endereco_id, chef_id, "espera", total))

        pedido_id = cursor.lastrowid

        # 8. Registra os itens e as porções feitas com ingrediente alternativo.
        avisos = []

        for i in itens:
            produto = i["produto"]

            cursor = db.execute("""
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
                i["quantidade"],
                produto["preco_centavos"] * i["quantidade"]
            ))

            item_id = cursor.lastrowid

            for sub in i["substituicoes"]:
                db.execute("""
                    INSERT INTO itens_pedido_substituicoes (
                        item_pedido_id,
                        ingrediente_original,
                        ingrediente_alternativo,
                        unidade,
                        porcoes,
                        quantidade
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    item_id,
                    sub["original"],
                    sub["alternativo"],
                    sub["unidade"],
                    sub["porcoes"],
                    sub["quantidade"]
                ))

            avisos.extend(mensagens_substituicao(i))

        # 9. Desconta os ingredientes.
        for ingrediente_id, dados in consumos.items():
            cursor = db.execute("""
                UPDATE ingredientes
                SET estoque = CASE
                    WHEN estoque - ? < 0 THEN 0
                    ELSE estoque - ?
                END
                WHERE id = ? AND estoque + 0.000001 >= ?
            """, (
                dados["quantidade"],
                dados["quantidade"],
                ingrediente_id,
                dados["quantidade"]
            ))

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Estoque insuficiente para {dados['nome']}."
                )

        db.commit()
        return pedido_id, avisos

    except Exception:
        db.rollback()
        raise


def substituicoes_por_item(pedido_id):
    """Ingredientes alternativos usados em cada item do pedido.

    Devolve {item_id: [ {original, alternativas, com_alternativo,
    com_padrao, quantidade_total} ]} para exibir nos detalhes.
    """

    linhas = get_db().execute("""
        SELECT s.*, ip.quantidade AS quantidade_item
        FROM itens_pedido_substituicoes AS s
        INNER JOIN itens_pedido AS ip ON ip.id = s.item_pedido_id
        WHERE ip.pedido_id = ?
        ORDER BY s.id
    """, (pedido_id,)).fetchall()

    resultado = {}

    for linha in linhas:
        grupos = resultado.setdefault(linha["item_pedido_id"], {})
        grupo = grupos.setdefault(linha["ingrediente_original"], {
            "original": linha["ingrediente_original"],
            "alternativas": [],
            "com_alternativo": 0,
            "quantidade_item": linha["quantidade_item"]
        })

        grupo["alternativas"].append({
            "nome": linha["ingrediente_alternativo"],
            "porcoes": linha["porcoes"],
            "quantidade": linha["quantidade"],
            "unidade": linha["unidade"]
        })
        grupo["com_alternativo"] += linha["porcoes"]

    final = {}

    for item_id, grupos in resultado.items():
        final[item_id] = []

        for grupo in grupos.values():
            grupo["com_padrao"] = (
                grupo["quantidade_item"] - grupo["com_alternativo"]
            )
            final[item_id].append(grupo)

    return final


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

    else:
        return 0

    return db.execute(consulta, parametros).fetchone()["total"]
