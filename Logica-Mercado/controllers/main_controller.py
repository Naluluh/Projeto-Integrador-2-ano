"""Página inicial da área autenticada."""
from flask import Blueprint, render_template

from models import compra, produto


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def inicio():
    return render_template(
        "menu.html", total_produtos=produto.quantidade_total(), total_compras=compra.quantidade_total()
    )

