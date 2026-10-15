"""Página inicial da área autenticada."""

from flask import Blueprint, render_template, session

from models import ingrediente
from models import pedido
from models import prato


# Blueprint da página inicial.
main_bp = Blueprint(
    "main",
    __name__
)


@main_bp.get("/")
def inicio():

    # Obtém as quantidades para o painel.
    total_pratos = prato.quantidade_total()
    total_ingredientes = ingrediente.quantidade_total()
    total_pedidos = pedido.quantidade_total()

    # Obtém o cargo do usuário que está logado.
    cargo = session.get("cargo")

    # Cliente.
    if cargo == "cliente":
        return render_template(
            "menu_cliente.html",
            total_pratos=total_pratos,
            total_ingredientes=total_ingredientes,
            total_pedidos=total_pedidos
        )

    # Cozinheiro.
    elif cargo == "cozinheiro":
        return render_template(
            "menu_cozinheiro.html",
            total_pratos=total_pratos,
            total_ingredientes=total_ingredientes,
            total_pedidos=total_pedidos
        )

    # Administrador.
    elif cargo == "administrador":
        return render_template(
            "menu_adm.html",
            total_pratos=total_pratos,
            total_ingredientes=total_ingredientes,
            total_pedidos=total_pedidos
        )

    # Cargo desconhecido.
    return "Cargo de usuário inválido.", 403