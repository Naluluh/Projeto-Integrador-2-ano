
from flask import (
    Blueprint,
    render_template,
    session,
    flash,
    redirect,
    url_for
)

from models import chefs_model
from models.categorias_model import nome_categoria


chefs_bp = Blueprint(
    "chefs",
    __name__,
    url_prefix="/chefs"
)


# Buscar cozinheiros relacionados a um produto.
@chefs_bp.route("/prato/<int:id_p>")
def por_prato(id_p):

    chefs = chefs_model.chefs_produto(id_p)

    return render_template(
        "chefs_esp.html",
        chefs=chefs,
        origem="prato",
        id_p=id_p
    )


# Buscar cozinheiros relacionados a uma categoria.
@chefs_bp.route("/categoria/<int:categoria_id>")
def por_categoria(categoria_id):

    chefs = chefs_model.chefs_categoria(categoria_id)

    return render_template(
        "chefs_esp.html",
        chefs=chefs,
        origem="categoria",
        categoria_id=categoria_id
    )


# Selecionar cozinheiro a partir de uma categoria.
@chefs_bp.route(
    "/selecionar/categoria/<int:categoria_id>/<int:chef_id>"
)
def selecionar_categoria(categoria_id, chef_id):

    if not chefs_model.verificar_chef_categoria(
        chef_id,
        categoria_id
    ):
        flash(
            "Esse cozinheiro não está relacionado à categoria.",
            "erro"
        )

        return redirect(
            url_for("chefs.por_categoria", categoria_id=categoria_id)
        )

    # Guarda o cozinheiro escolhido.
    session["chef_id"] = chef_id

    # Guarda a categoria escolhida.
    session["categoria_id"] = categoria_id

    # Busca os produtos que esse cozinheiro prepara.
    produtos = chefs_model.produtos_chef_categoria(
        chef_id,
        categoria_id
    )

    return render_template(
        "categoria_esp.html",
        produtos=produtos,
        categoria_id=categoria_id,
        nome=nome_categoria(categoria_id)
    )


# Selecionar cozinheiro a partir de um produto.
@chefs_bp.route(
    "/selecionar/prato/<int:id_p>/<int:chef_id>"
)
def selecionar_prato(id_p, chef_id):

    if not chefs_model.verificar_chef_produto(
        chef_id,
        id_p
    ):
        flash(
            "Esse cozinheiro não está relacionado ao produto.",
            "erro"
        )

        return redirect(
            url_for("chefs.por_prato", id_p=id_p)
        )

    categoria_id = chefs_model.categoria_por_produto(id_p)

    if categoria_id is None:
        flash(
            "Produto não encontrado.",
            "erro"
        )

        return redirect(
            url_for("categorias.main")
        )

    # Guarda o cozinheiro e o produto escolhidos.
    session["chef_id"] = chef_id
    session["categoria_id"] = categoria_id
    session["produto_id"] = id_p

    produtos = chefs_model.produtos_chef_categoria(
        chef_id,
        categoria_id
    )

    return render_template(
        "categoria_esp.html",
        produtos=produtos,
        categoria_id=categoria_id,
        nome=nome_categoria(categoria_id)
    )
