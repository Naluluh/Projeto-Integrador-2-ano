"""Página inicial da área autenticada."""

from flask import Blueprint, Response, abort, render_template, session

from models import imagem_model
from models import ingrediente_model
from models import pedido_model
from models import prato_model


# Blueprint da página inicial.
main_bp = Blueprint(
    "main",
    __name__
)


@main_bp.get("/")
def inicio():

    # Obtém as quantidades para o painel.
    total_ingredientes = ingrediente_model.quantidade_total()
    total_pratos = prato_model.quantidade_total()
    total_pedidos=pedido_model.quantidade_visivel(
    session.get("cargo"),
    session.get("usuario_id")
)

    # Obtém o cargo do usuário que está logado.
    cargo = session.get("cargo")

    # Cliente.
    if cargo == "cliente":
        return render_template(
            "menu_cliente.html",
            total_ingredientes=total_ingredientes,
            total_pratos=total_pratos,
            total_pedidos=total_pedidos
        )

    # Cozinheiro.
    elif cargo == "cozinheiro":
        return render_template(
            "menu_cozinheiro.html",
            total_ingredientes=total_ingredientes,
            total_pratos=total_pratos,
            total_pedidos=total_pedidos
        )

    # Administrador.
    elif cargo == "administrador":
        return render_template(
            "menu_adm.html",
            total_ingredientes=total_ingredientes,
            total_pratos=total_pratos,
            total_pedidos=total_pedidos
        )

    # Cargo desconhecido.
    return "Cargo de usuário inválido.", 403


@main_bp.get("/imagem/<int:imagem_id>")
def imagem(imagem_id):
    """Entrega uma foto enviada por usuário (guardada no banco)."""

    linha = imagem_model.buscar(imagem_id)

    if linha is None:
        abort(404)

    resposta = Response(
        bytes(linha["dados"]),
        mimetype=linha["tipo"]
    )

    resposta.headers["Cache-Control"] = "private, max-age=86400"
    resposta.headers["X-Content-Type-Options"] = "nosniff"

    return resposta


@main_bp.post("/sessao/ping")
def sessao_ping():
    """Chamada pelo JavaScript enquanto a pessoa usa a página.

    O app.py já renova o horário da última atividade em toda requisição;
    esta rota existe só para o navegador avisar "ainda estou aqui".
    """

    return "", 204
