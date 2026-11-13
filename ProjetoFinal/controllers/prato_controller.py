"""CRUD, cadastro de receitas e exportação de produtos."""

from io import BytesIO
import os

from werkzeug.utils import secure_filename
from flask import (
    Blueprint, abort, flash, redirect, render_template,
    request, send_file, url_for
)
from openpyxl import Workbook
from openpyxl.styles import Font

from database import get_db
from models import categorias_model, prato_model, usuario_model, pedido_model
from utils import moeda_para_centavos, administrador_required, gestor_required


prato_bp = Blueprint("prato", __name__, url_prefix="/cardapio")


def _carregar_formulario(prato=None):
    return render_template(
        "prato_form.html",
        prato=prato,
        categorias=prato_model.listar_categorias(),
        cozinheiros=usuario_model.listar_cozinheiros(),
        ingredientes=get_db().execute("""
            SELECT id, nome, unidade, estoque
            FROM ingredientes
            ORDER BY nome COLLATE NOCASE
        """).fetchall(),
        ingredientes_produto=(
            prato_model.listar_ingredientes(prato["id"])
            if prato else []
        ),
        chefs_produto=(
            prato_model.listar_chefs_produto(prato["id"])
            if prato else []
        )
    )


@prato_bp.route("/")
def categorias():
    return render_template(
        "cardapio.html",
        categorias=prato_model.listar_categorias(),
        pratos=[],
        categoria_atual=None
    )


@prato_bp.route("/categoria/<int:categoria_id>")
def catalogo_categoria(categoria_id):
    pratos = prato_model.listar_por_categoria(categoria_id)
    pratos = [
        {
            **dict(prato),
            "disponivel": pedido_model.disponivel(prato["id"])
        }
        for prato in pratos
    ]
    return render_template(
        "cardapio.html",
        categorias=prato_model.listar_categorias(),
        pratos=pratos,
        categoria_atual=categoria_id
    )


@prato_bp.route("/detalhes/<int:prato_id>")
def detalhes(prato_id):
    prato = prato_model.buscar(prato_id)
    if prato is None:
        abort(404)
    return render_template("prato_detalhes.html", prato=prato)


def _dados_formulario():
    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip()
    categoria = request.form.get("categoria", "").strip()
    modo_preparo = request.form.get("modo_preparo", "").strip()
    preco = moeda_para_centavos(request.form.get("preco", ""))

    if not nome or not descricao or not categoria or not modo_preparo or preco < 0:
        raise ValueError("Preencha todos os campos com valores válidos.")

    if categoria != "__nova__":
        try:
            categoria = int(categoria)
        except ValueError:
            raise ValueError("Selecione uma categoria válida.")

    return nome, descricao, categoria, preco, modo_preparo


def _dados_ingredientes():
    ids = request.form.getlist("ingrediente_id[]")
    quantidades = request.form.getlist("quantidade[]")
    nomes = request.form.getlist("novo_nome[]")
    unidades = request.form.getlist("nova_unidade[]")
    estoques = request.form.getlist("novo_estoque[]")
    alternativas = request.form.getlist("ingrediente_alternativo_id[]")
    quantidades_alternativas = request.form.getlist("quantidade_alternativa[]")

    if not ids:
        raise ValueError("Adicione pelo menos um ingrediente.")

    # Campos de novo ingrediente/alternativa são opcionais por linha.
    def valor_da_linha(lista, indice, padrao=""):
        return lista[indice] if indice < len(lista) else padrao

    ingredientes = []
    ids_utilizados = set()

    for i, ingrediente_id in enumerate(ids):
        try:
            quantidade = float(quantidades[i])
        except (ValueError, IndexError):
            raise ValueError("Informe uma quantidade válida para cada ingrediente.")

        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        alternativo_id = valor_da_linha(alternativas, i).strip()
        quantidade_alt_texto = valor_da_linha(quantidades_alternativas, i).strip()
        quantidade_alt = None

        if alternativo_id:
            try:
                quantidade_alt = float(quantidade_alt_texto) if quantidade_alt_texto else quantidade
            except ValueError:
                raise ValueError("Informe uma quantidade válida para o ingrediente alternativo.")
            if quantidade_alt <= 0:
                raise ValueError("A quantidade alternativa deve ser maior que zero.")

        if ingrediente_id == "__novo__":
            nome = valor_da_linha(nomes, i).strip()
            unidade = valor_da_linha(unidades, i).strip()
            estoque_texto = valor_da_linha(estoques, i).strip()
            try:
                estoque = float(estoque_texto)
            except ValueError:
                raise ValueError("Informe o estoque inicial do novo ingrediente.")

            if not nome or not unidade or estoque < 0:
                raise ValueError("Preencha nome, unidade e estoque do novo ingrediente.")

            if alternativo_id:
                raise ValueError("Cadastre primeiro o ingrediente principal antes de definir sua alternativa.")

            ingredientes.append({
                "ingrediente_id": None,
                "novo_nome": nome,
                "nova_unidade": unidade,
                "novo_estoque": estoque,
                "quantidade": quantidade
            })
            continue

        try:
            ingrediente_id = int(ingrediente_id)
        except ValueError:
            raise ValueError("Selecione um ingrediente válido.")

        if ingrediente_id in ids_utilizados:
            raise ValueError("Não selecione o mesmo ingrediente duas vezes.")
        ids_utilizados.add(ingrediente_id)

        ingredientes.append({
            "ingrediente_id": ingrediente_id,
            "quantidade": quantidade,
            "alternativo_id": alternativo_id or None,
            "quantidade_alternativa": quantidade_alt
        })

    return ingredientes


def _dados_chefs():
    try:
        chefs_ids = [int(valor) for valor in request.form.getlist("chefs_ids")]
    except ValueError:
        raise ValueError("Selecione cozinheiros válidos.")
    if not chefs_ids:
        raise ValueError("Selecione pelo menos um chef responsável.")
    if len(chefs_ids) != len(set(chefs_ids)):
        raise ValueError("Não selecione o mesmo chef mais de uma vez.")
    return chefs_ids


def _salvar_foto():
    foto = request.files.get("foto_produto")
    if not foto or not foto.filename:
        return None

    nome_img = secure_filename(foto.filename)
    if not nome_img:
        raise ValueError("Nome de arquivo de imagem inválido.")

    pasta = os.path.join(
        "static", "images", "fotos_perfil", "produtos"
    )
    os.makedirs(pasta, exist_ok=True)
    foto.save(os.path.join(pasta, nome_img))
    return f"images/fotos_perfil/produtos/{nome_img}"


@prato_bp.get("/gerenciar")
@gestor_required
def listar():
    busca = request.args.get("busca", "")
    return render_template(
        "pratos.html",
        produtos=prato_model.listar(busca),
        busca=busca
    )


@prato_bp.route("/novo", methods=("GET", "POST"))
@gestor_required
def novo():
    if request.method == "POST":
        try:
            dados = list(_dados_formulario())
            if dados[2] == "__nova__":
                nova_categoria = request.form.get("nova_categoria", "").strip()
                if not nova_categoria:
                    raise ValueError("Informe o nome da nova categoria.")
                dados[2] = categorias_model.criar_categoria(nova_categoria)

            ingredientes = _dados_ingredientes()
            chefs_ids = _dados_chefs()
            foto_url = _salvar_foto()

            prato_model.criar_com_relacoes(
                *dados,
                ingredientes=ingredientes,
                chefs_ids=chefs_ids,
                foto_url=foto_url
            )
            flash("Produto cadastrado com sucesso.", "sucesso")
            return redirect(url_for("prato.listar"))

        except (ValueError, TypeError) as erro:
            flash(str(erro), "erro")
        except Exception:
            # A transação do model desfaz o cadastro se uma relação falhar.
            flash("Não foi possível cadastrar o produto. Verifique os dados e tente novamente.", "erro")

    return _carregar_formulario()


@prato_bp.route("/<int:prato_id>/editar", methods=("GET", "POST"))
@gestor_required
def editar(prato_id):
    prato = prato_model.buscar(prato_id)
    if prato is None:
        abort(404)

    if request.method == "POST":
        try:
            dados = list(_dados_formulario())
            if dados[2] == "__nova__":
                nova_categoria = request.form.get("nova_categoria", "").strip()
                if not nova_categoria:
                    raise ValueError("Informe o nome da nova categoria.")
                dados[2] = categorias_model.criar_categoria(nova_categoria)

            ingredientes = _dados_ingredientes()
            chefs_ids = _dados_chefs()
            foto_url = _salvar_foto()

            prato_model.atualizar_com_relacoes(
                prato_id,
                *dados,
                ingredientes=ingredientes,
                chefs_ids=chefs_ids,
                foto_url=foto_url
            )
            flash("Produto e receita atualizados com sucesso.", "sucesso")
            return redirect(url_for("prato.listar"))

        except (ValueError, TypeError) as erro:
            flash(str(erro), "erro")
        except Exception:
            flash("Não foi possível atualizar o produto. Verifique os dados e tente novamente.", "erro")

    return _carregar_formulario(prato)


@prato_bp.post("/<int:prato_id>/excluir")
@administrador_required
def excluir(prato_id):
    if prato_model.buscar(prato_id) is None:
        abort(404)
    prato_model.excluir(prato_id)
    flash("Produto excluído.", "sucesso")
    return redirect(url_for("prato.listar"))


@prato_bp.get("/exportar")
@gestor_required
def exportar():
    wb = Workbook()
    ws = wb.active
    ws.title = "produtos"
    ws.append([
        "Código", "Nome", "Descrição", "Categoria",
        "Preço (R$)", "Modo de preparo"
    ])

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for produto in prato_model.listar():
        ws.append([
            produto["id"],
            produto["nome"],
            produto["descricao"],
            produto["categoria_nome"],
            produto["preco_centavos"] / 100,
            produto["modo_preparo"]
        ])

    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 35
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["F"].width = 45
    for cell in ws["E"][1:]:
        cell.number_format = "R$ #,##0.00"

    arquivo = BytesIO()
    wb.save(arquivo)
    arquivo.seek(0)
    return send_file(
        arquivo,
        as_attachment=True,
        download_name="produtos.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
