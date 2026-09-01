"""Página inicial da área autenticada."""

from flask import Blueprint, render_template

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

    # Exibe o painel principal.
    return render_template(
        "menu.html",
        total_pratos=total_pratos,
        total_ingredientes=total_ingredientes,
        total_pedidos=total_pedidos
    )