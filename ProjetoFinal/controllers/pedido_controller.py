
"""Controller responsável pelo carrinho, pedidos e histórico."""

from io import BytesIO

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for
)

from openpyxl import Workbook
from openpyxl.styles import Font

from models import pedido_model
from models import prato_model
from models import endereco_model
from controllers import categorias_controller

from utils import (
    formatar_datahora,
    administrador_required,
    cliente_required,
    gestor_required,
    adm_cli_required
)


pedido_bp = Blueprint(
    "pedido",
    __name__,
    url_prefix="/pedidos"
)


def _carrinho():
    """Obtém ou cria o carrinho da sessão."""

    return session.setdefault("carrinho", [])


def _verificar_login():
    """Verifica se existe usuário autenticado."""

    if not session.get("usuario_id"):
        return False

    if session.get("cargo") not in {
        "administrador",
        "cliente",
        "cozinheiro"
    }:
        return False

    return True


@pedido_bp.get("")
def listar():
    """Exibe o histórico conforme o cargo."""

    if not _verificar_login():
        return redirect(url_for("auth.login"))

    cargo = session.get("cargo")
    usuario_id = session.get("usuario_id")

    if cargo == "administrador":

        pedidos = pedido_model.listar()

    elif cargo == "cliente":

        pedidos = pedido_model.listar_por_cliente(
            usuario_id
        )

    elif cargo == "cozinheiro":

        pedidos = pedido_model.listar_por_chef(
            usuario_id
        )

    else:
        abort(403)

    return render_template(
        "pedidos.html",
        pedidos=pedidos
    )


@pedido_bp.get("/novo")
@adm_cli_required
def novo():
    """Exibe o carrinho e os produtos disponíveis."""

    carrinho = _carrinho()

    total = sum(
        item["preco_centavos"] * item["quantidade"]
        for item in carrinho
    )

    return render_template(
        "novo_pedido.html",
        pratos=prato_model.listar_para_pedido(),
        carrinho=carrinho,
        total=total,
        endereco_atual=endereco_model.ultimo_endereco(
            session["usuario_id"]
        )
    )


@pedido_bp.post("/carrinho/adicionar")
@adm_cli_required
def adicionar():
    """Adiciona um produto ao carrinho."""

    try:

        produto_id = int(
            request.form.get("produto_id", "")
        )

        quantidade = int(
            request.form.get("quantidade", "")
        )

    except (ValueError, TypeError):

        produto_id = 0
        quantidade = 0

    produto = prato_model.buscar(produto_id)

    if produto is None or quantidade <= 0:

        flash(
            "Selecione um produto e uma quantidade válida.",
            "erro"
        )

        return redirect(url_for("pedido.novo"))

    # Exige que um cozinheiro tenha sido selecionado.
    chef_id = session.get("chef_id")

    if not chef_id:

        flash(
            "Selecione um cozinheiro antes de adicionar produtos.",
            "erro"
        )

        return redirect(url_for("categorias.main"))

    # Verifica se o cozinheiro prepara o produto.
    from database import get_db

    relacionado = get_db().execute("""
        SELECT 1
        FROM produto_chefs
        WHERE produto_id = ?
        AND chef_id = ?
    """, (
        produto_id,
        chef_id
    )).fetchone()

    if relacionado is None:

        flash(
            "O cozinheiro selecionado não prepara este produto.",
            "erro"
        )

        return redirect(url_for("pedido.novo"))

    carrinho = _carrinho()

    existente = next(
        (
            item for item in carrinho
            if item["produto_id"] == produto_id
        ),
        None
    )

    if existente:

        existente["quantidade"] += quantidade

    else:

        carrinho.append({
            "produto_id": produto["id"],
            "nome": produto["nome"],
            "preco_centavos": produto["preco_centavos"],
            "quantidade": quantidade
        })

    session["carrinho"] = carrinho

    flash(
        "Produto adicionado ao pedido.",
        "sucesso"
    )

    return redirect(url_for("pedido.novo"))


@pedido_bp.post("/carrinho/<int:indice>/remover")
@adm_cli_required
def remover(indice):

    carrinho = _carrinho()

    if indice < 0 or indice >= len(carrinho):
        abort(404)

    carrinho.pop(indice)

    session["carrinho"] = carrinho

    return redirect(url_for("pedido.novo"))


@pedido_bp.post("/carrinho/limpar")
@adm_cli_required
def limpar():

    session.pop("carrinho", None)

    flash(
        "Pedido esvaziado.",
        "sucesso"
    )

    return redirect(url_for("pedido.novo"))


@pedido_bp.post("/finalizar")
@adm_cli_required
def finalizar():
    """Finaliza o pedido com o cozinheiro escolhido."""

    carrinho = _carrinho()

    if not carrinho:

        flash(
            "O pedido está vazio.",
            "erro"
        )

        return redirect(url_for("pedido.novo"))

    chef_id = session.get("chef_id")

    if not chef_id:

        flash(
            "Selecione um cozinheiro antes de finalizar.",
            "erro"
        )

        return redirect(url_for("categorias.main"))

    endereco = endereco_model.ultimo_endereco(session["usuario_id"])

    if endereco is None:
        flash("Cadastre um endereço antes de finalizar o pedido.", "erro")
        return redirect(url_for("endereco.cadastrar"))

    try:
        pedido_id = pedido_model.finalizar(
            session["usuario_id"],
            chef_id,
            carrinho,
            endereco["id"]
        )
    except ValueError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("pedido.novo"))

    # Limpa os dados do pedido finalizado.
    session.pop("carrinho", None)
    session.pop("chef_id", None)
    session.pop("categoria_id", None)
    session.pop("produto_id", None)

    flash(
        "Pedido registrado com sucesso.",
        "sucesso"
    )

    return redirect(
        url_for(
            "pedido.detalhes",
            pedido_id=pedido_id
        )
    )


@pedido_bp.get("/<int:pedido_id>")
def detalhes(pedido_id):
    """Exibe os detalhes somente para quem tem permissão."""

    if not _verificar_login():
        return redirect(url_for("auth.login"))

    pedido = pedido_model.buscar(pedido_id)

    if pedido is None:
        abort(404)

    cargo = session.get("cargo")
    usuario_id = session.get("usuario_id")

    # Administrador pode consultar qualquer pedido.
    if cargo == "administrador":

        pode_alterar_status = True
        pode_cancelar = False

    # Cliente consulta somente os próprios pedidos.
    elif cargo == "cliente":

        if pedido["usuario_id"] != usuario_id:
            abort(403)

        pode_alterar_status = False

        pode_cancelar = (
            pedido["status"] not in {"entregue", "cancelado"}
        )

    # Cozinheiro consulta somente os pedidos destinados a ele.
    elif cargo == "cozinheiro":

        if pedido["chef_id"] != usuario_id:
            abort(403)

        pode_alterar_status = True
        pode_cancelar = False

    else:
        abort(403)

    itens = pedido_model.listar_itens(pedido_id)

    return render_template(
        "detalhes_pedido.html",
        pedido=pedido,
        itens=itens,
        pode_alterar_status=pode_alterar_status,
        pode_cancelar=pode_cancelar
    )


@pedido_bp.post("/<int:pedido_id>/status")
@gestor_required
def alterar_status(pedido_id):
    """Permite ao administrador ou cozinheiro atualizar status."""

    pedido = pedido_model.buscar(pedido_id)

    if pedido is None:
        abort(404)

    cargo = session.get("cargo")
    usuario_id = session.get("usuario_id")

    status = request.form.get("status", "").strip()

    status_permitidos = {
        "espera",
        "preparado",
        "atrasado",
        "entregue"
    }

    # Administrador também pode cancelar.
    if cargo == "administrador":
        status_permitidos.add("cancelado")

    if status not in status_permitidos:

        flash(
            "Status inválido.",
            "erro"
        )

        return redirect(
            url_for("pedido.detalhes", pedido_id=pedido_id)
        )

    # Cozinheiro só altera os próprios pedidos.
    if cargo == "cozinheiro":

        if pedido["chef_id"] != usuario_id:
            abort(403)

        if status == "cancelado":
            abort(403)

    if pedido["status"] == "entregue":

        flash(
            "Um pedido entregue não pode ser alterado.",
            "erro"
        )

        return redirect(
            url_for("pedido.detalhes", pedido_id=pedido_id)
        )

    if pedido["status"] == "cancelado":

        flash(
            "Um pedido cancelado não pode ser alterado.",
            "erro"
        )

        return redirect(
            url_for("pedido.detalhes", pedido_id=pedido_id)
        )

    pedido_model.atualizar_status(
        pedido_id,
        status
    )

    flash(
        "Status do pedido atualizado.",
        "sucesso"
    )

    return redirect(
        url_for("pedido.detalhes", pedido_id=pedido_id)
    )


@pedido_bp.post("/<int:pedido_id>/cancelar")
@cliente_required
def cancelar(pedido_id):
    """Permite ao cliente cancelar seu próprio pedido."""

    pedido = pedido_model.buscar(pedido_id)

    if pedido is None:
        abort(404)

    # Impede o cancelamento de pedidos de outras pessoas.
    if pedido["usuario_id"] != session.get("usuario_id"):
        abort(403)

    try:

        pedido_model.cancelar(pedido_id)

    except ValueError as erro:

        flash(str(erro), "erro")

        return redirect(
            url_for("pedido.detalhes", pedido_id=pedido_id)
        )

    flash(
        "Pedido cancelado.",
        "sucesso"
    )

    return redirect(url_for("pedido.listar"))


@pedido_bp.get("/exportar")
@administrador_required
def exportar():
    """Exporta todos os pedidos para Excel."""

    wb = Workbook()
    ws = wb.active

    ws.title = "Pedidos"

    ws.append([
        "Código",
        "Data e hora",
        "Cliente",
        "Cozinheiro",
        "Status",
        "Total (R$)"
    ])

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for pedido in pedido_model.listar():

        ws.append([
            pedido["id"],
            formatar_datahora(pedido["criado_em"]),
            pedido["usuario_nome"],
            pedido["chef_nome"] or "Não informado",
            pedido["status"],
            pedido["total_centavos"] / 100
        ])

    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 25
    ws.column_dimensions["D"].width = 25
    ws.column_dimensions["E"].width = 15

    for cell in ws["F"][1:]:
        cell.number_format = "R$ #,##0.00"

    arquivo = BytesIO()

    wb.save(arquivo)
    arquivo.seek(0)

    return send_file(
        arquivo,
        as_attachment=True,
        download_name="pedidos.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )
