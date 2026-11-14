"""Regras do carrinho e da escolha do cozinheiro.

Usadas pelo pedido_controller e pelo chefs_controller (ambos precisam
adicionar pratos ao carrinho e trocar o cozinheiro do pedido).
"""

from flask import flash, session

from models import chefs_model, pedido_model


def itens_do_carrinho():
    """Cópia do carrinho guardado na sessão."""

    return [dict(item) for item in session.get("carrinho", [])]


def definir_chef(chef_id, categoria_id=None, produto_id=None):
    """Guarda o cozinheiro escolhido para o pedido.

    Um pedido tem um único cozinheiro. Se a pessoa trocar de cozinheiro com
    itens já no carrinho, mantemos só os pratos que o novo cozinheiro faz.
    """

    anterior = session.get("chef_id")
    itens = itens_do_carrinho()

    if anterior and anterior != chef_id and itens:

        mantidos = []
        removidos = []

        for item in itens:
            if chefs_model.verificar_chef_produto(chef_id, item["produto_id"]):
                mantidos.append(item)
            else:
                removidos.append(item["nome"])

        if removidos:
            session["carrinho"] = mantidos

            flash(
                "O novo cozinheiro não prepara: "
                + ", ".join(removidos)
                + ". Esses itens saíram do pedido.",
                "aviso"
            )

    session["chef_id"] = chef_id

    if categoria_id is not None:
        session["categoria_id"] = categoria_id

    if produto_id is not None:
        session["produto_id"] = produto_id


def incluir_no_carrinho(produto, quantidade):
    """Adiciona o prato ao carrinho depois de checar o estoque.

    Se o ingrediente padrão não cobrir todas as porções, o sistema usa o
    alternativo (quando cadastrado) e avisa a pessoa por mensagens flash.
    Devolve True se o prato entrou no carrinho.
    """

    itens = itens_do_carrinho()

    existente = next(
        (i for i in itens if i["produto_id"] == produto["id"]),
        None
    )

    if existente:
        existente["quantidade"] += quantidade
    else:
        itens.append({
            "produto_id": produto["id"],
            "nome": produto["nome"],
            "preco_centavos": produto["preco_centavos"],
            "quantidade": quantidade
        })

    # Verifica o estoque do carrinho inteiro (pratos diferentes podem
    # disputar o mesmo ingrediente).
    try:
        plano, _consumos = pedido_model.planejar(itens)
    except ValueError as erro:
        flash(str(erro), "erro")
        return False

    session["carrinho"] = itens

    flash("Produto adicionado ao pedido.", "sucesso")

    for item_plano in plano:
        if item_plano["produto"]["id"] == produto["id"]:
            for mensagem in pedido_model.mensagens_substituicao(item_plano):
                flash(mensagem, "aviso")

    return True
