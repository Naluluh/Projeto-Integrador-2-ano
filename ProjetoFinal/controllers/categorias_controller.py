#categorias_controller

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

from models import prato_model as prato_model
from models.categorias_model import *
from utils import gestor_required
import os
from werkzeug.utils import secure_filename


# Blueprint único para categorias e sua API
categorias_bp = Blueprint(
    "categorias",
    __name__,
    url_prefix="/categorias"
)


# Rota da API para cadastro assíncrono de categoria via JavaScript (Fetch)
@categorias_bp.route("/api/categorias", methods=["POST"])
@gestor_required 
def criar_categoria_api():
    # Recebe os dados enviados pelo JavaScript.
    dados = request.get_json(silent=True) or {}

    # Obtém o nome da categoria.
    nome = (
        dados.get("nome")
        or request.form.get("nome")
        or ""
    ).strip()

    # Obtém a imagem, caso tenha sido enviada.
    img = request.files.get("foto_categoria")

    # Valida o nome.
    if not nome:
        return jsonify({
            "mensagem": "Informe o nome da categoria."
        }), 400
    
    img_url = 'images/fotos_perfil/categorias/template_categorias.jpeg'
    
    if img and img.filename:
        nome_img = secure_filename(img.filename)

        pasta = os.path.join(
            "static",
            "images",
            "fotos_perfil",
            "categorias"
        )

        os.makedirs(pasta, exist_ok=True)

        img.save(os.path.join(pasta, nome_img))
        img_url = f'images/fotos_perfil/categorias/{nome_img}'

    try:
        categoria_id = criar_categoria(nome, img_url)
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
        categoria_id=int(categoria),
        produtos=produtos,
        nome=nome_categoria(categoria)
    )