# Rotas dos cozinheiros
"""Cozinheiros: lista, perfil público e escolha do cozinheiro do pedido."""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    session,
    url_for
)

from controllers import carrinho as carrinho_service
from models import chefs_model
from models import prato_model
from models.categorias_model import nome_categoria


chefs_bp = Blueprint(
    "chefs",
    __name__,
    url_prefix="/chefs"
)


# Diz se quem está logado é administrador
def _e_administrador():
    return session.get("cargo") == "administrador"


# Lista de cozinheiros
@chefs_bp.get("/")
def listar():

    chefs = chefs_model.listar_cozinheiros(
        incluir_inativos=_e_administrador()
    )

    return render_template("chefs_lista.html", chefs=chefs)


# Perfil do cozinheiro: cadastro, categorias e pratos
@chefs_bp.get("/<int:chef_id>")
def perfil(chef_id):

    chef = chefs_model.buscar_cozinheiro(chef_id)

    if chef is None:
        abort(404)

    return render_template(
        "chef_perfil.html",
        chef=chef,
        categorias=chefs_model.categorias_do_chef(chef_id),
        produtos=chefs_model.produtos_do_chef(
            chef_id,
            incluir_inativos=_e_administrador()
        ),
        e_proprio=(session.get("usuario_id") == chef_id)
    )


# Cozinheiros de um produto
@chefs_bp.route("/prato/<int:id_p>")
def por_prato(id_p):

    produto = prato_model.buscar(id_p)

    # Prato oculto só o admin vê
    if produto is None or (
        not produto["ativo"] and not _e_administrador()
    ):
        abort(404)

    chefs = chefs_model.chefs_produto(id_p)

    return render_template(
        "chefs_esp.html",
        chefs=chefs,
        origem="prato",
        id_p=id_p,
        produto=produto,
        pedido_pendente=session.get("pedido_pendente")
    )


# Cozinheiros de uma categoria
@chefs_bp.route("/categoria/<int:categoria_id>")
def por_categoria(categoria_id):

    chefs = chefs_model.chefs_categoria(categoria_id)

    return render_template(
        "chefs_esp.html",
        chefs=chefs,
        origem="categoria",
        categoria_id=categoria_id
    )


# Escolher cozinheiro pela categoria
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

    # Guarda cozinheiro e categoria
    carrinho_service.definir_chef(chef_id, categoria_id=categoria_id)

    # Produtos que ele prepara
    produtos = chefs_model.produtos_chef_categoria(
        chef_id,
        categoria_id,
        incluir_inativos=_e_administrador()
    )

    return render_template(
        "categoria_esp.html",
        produtos=produtos,
        categoria_id=categoria_id,
        nome=nome_categoria(categoria_id)
    )


# Escolher cozinheiro pelo produto
@chefs_bp.route(
    "/selecionar/prato/<int:id_p>/<int:chef_id>"
)
def selecionar_prato(id_p, chef_id):

    produto = prato_model.buscar(id_p)

    if produto is None or (
        not produto["ativo"] and not _e_administrador()
    ):
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("categorias.main"))

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

    categoria_id = produto["categoria_id"]

    # Guarda cozinheiro, categoria e produto
    carrinho_service.definir_chef(
        chef_id,
        categoria_id=categoria_id,
        produto_id=id_p
    )

    # Tentou adicionar o prato antes de escolher o cozinheiro:
    # agora o prato entra no carrinho e segue pro pedido
    pendente = session.pop("pedido_pendente", None)

    if (
        pendente
        and pendente.get("produto_id") == id_p
        and session.get("cargo") in {"cliente", "administrador"}
    ):
        carrinho_service.incluir_no_carrinho(
            produto,
            int(pendente["quantidade"])
        )

        return redirect(url_for("pedido.novo"))

    produtos = chefs_model.produtos_chef_categoria(
        chef_id,
        categoria_id,
        incluir_inativos=_e_administrador()
    )

    return render_template(
        "categoria_esp.html",
        produtos=produtos,
        categoria_id=categoria_id,
        nome=nome_categoria(categoria_id)
    )
