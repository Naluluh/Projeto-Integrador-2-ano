
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    jsonify,
    session,
    url_for
)

from models import prato_model as prato_model
from models.categorias_model import *
from utils import gestor_required, salvar_imagem


# Blueprint de categorias e da API
categorias_bp = Blueprint(
    "categorias",
    __name__,
    url_prefix="/categorias"
)


# API para cadastrar categoria por JavaScript (Fetch)
@categorias_bp.route("/api/categorias", methods=["POST"])
@gestor_required 
def criar_categoria_api():
    dados = request.get_json(silent=True) or {}

    nome = (
        dados.get("nome")
        or request.form.get("nome")
        or ""
    ).strip()

    img = request.files.get("foto_categoria")

    if not nome:
        return jsonify({
            "mensagem": "Informe o nome da categoria."
        }), 400
    
    img_url = 'images/fotos_perfil/categorias/template_categorias.jpeg'

    try:
        # Foto vai pro banco
        img_url = salvar_imagem(img) or img_url
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400

    try:
        categoria_id = criar_categoria(nome, img_url)
        return jsonify({"id": categoria_id, "nome": nome}), 201
    except Exception as e:
        return jsonify({"mensagem": str(e)}), 400


# Lista de categorias
@categorias_bp.get('/')
def main():
    return render_template('menu_categorias.html', categorias=pegar_categorias())

# Produtos de uma categoria
@categorias_bp.get('/<int:categoria>')
def exibir(categoria):
    # Prato indisponível só aparece para o admin
    produtos = mostrar_produtos(
        categoria,
        incluir_inativos=(session.get("cargo") == "administrador")
    )

    return render_template(
        'categoria_esp.html',
        categoria=categoria,
        categoria_id=categoria,
        produtos=produtos,
        nome=nome_categoria(categoria)
    )
