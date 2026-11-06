"""Controller para gerenciar categorias e suas exibições."""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    jsonify,
    url_for
)

from models import prato as prato_model
from models.categorias_model import *

# Blueprint único para categorias e sua API
categorias_bp = Blueprint(
    "categorias",
    __name__,
    url_prefix="/categorias"
)


# Rota da API para cadastro assíncrono de categoria via JavaScript (Fetch)
@categorias_bp.route("/api/categorias", methods=["POST"])
def criar_categoria_api():
    dados = request.get_json()
    nome = dados.get("nome")
    
    try:
        categoria_id = prato_model.criar_categoria(nome)
        return jsonify({"id": categoria_id, "nome": nome}), 201
    except Exception as e:
        return jsonify({"mensagem": str(e)}), 400


# Página principal de listagem de categorias
@categorias_bp.get('/')
def main():
    return render_template('menu_categorias.html', categorias=pegar_categorias())


# Exibe os chefs vinculados a uma categoria específica
@categorias_bp.get('/<categoria>')
def exibir(categoria):
    print("CATEGORIA RECEBIDA:", repr(categoria))

    produtos = mostrar_produtos(categoria)

    print("PRODUTOS ENCONTRADOS:", produtos)

    return render_template(
        'categoria_esp.html',
        categoria=categoria,
        produtos=produtos,
        nome = nome_categoria(categoria)
    )