"""Página inicial da área autenticada."""

from flask import Blueprint, render_template, session

from models import ingrediente_model
from models import pedido_model


# Blueprint da página inicial.
main_bp = Blueprint(
    "main",
    __name__
)


@main_bp.get("/")
def inicio():

    # Obtém as quantidades para o painel.
    total_ingredientes = ingrediente_model.quantidade_total()
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
            total_pedidos=total_pedidos
        )

    # Cozinheiro.
    elif cargo == "cozinheiro":
        return render_template(
            "menu_cozinheiro.html",
            total_ingredientes=total_ingredientes,
            total_pedidos=total_pedidos
        )

    # Administrador.
    elif cargo == "administrador":
        return render_template(
            "menu_adm.html",
            total_ingredientes=total_ingredientes,
            total_pedidos=total_pedidos
        )

    # Cargo desconhecido.
    return "Cargo de usuário inválido.", 403