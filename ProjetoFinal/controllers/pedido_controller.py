
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

from models import chefs_model
from models import pedido_model
from models import prato_model
from models import endereco_model
from controllers import carrinho as carrinho_service

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

    # Pratos que o administrador tornou indisponíveis saem do carrinho.
    ativos = pedido_model.ids_ativos(
        [item["produto_id"] for item in carrinho]
    )

    removidos = [
        item["nome"] for item in carrinho
        if item["produto_id"] not in ativos
    ]

    if removidos:
        carrinho = [
            item for item in carrinho
            if item["produto_id"] in ativos
        ]
        session["carrinho"] = carrinho

        flash(
            "Saíram do pedido por estarem indisponíveis: "
            + ", ".join(removidos) + ".",
            "aviso"
        )

    # Mostra as porções que vão usar ingrediente alternativo (se tiver)
    substituicoes = {}

    if carrinho:
        try:
            plano, _ = pedido_model.planejar(carrinho)

            for item_plano in plano:
                mensagens = pedido_model.mensagens_substituicao(item_plano)

                if mensagens:
                    substituicoes[item_plano["produto"]["id"]] = mensagens

        except ValueError as erro:
            # O estoque mudou desde que o prato foi adicionado.
            flash(str(erro), "erro")

    total = sum(
        item["preco_centavos"] * item["quantidade"]
        for item in carrinho
    )

    return render_template(
        "novo_pedido.html",
        pratos=prato_model.listar_para_pedido(),
        carrinho=carrinho,
        total=total,
        substituicoes=substituicoes,
        endereco_atual=endereco_model.ultimo_endereco(
            session["usuario_id"]
        )
    )


@pedido_bp.post("/carrinho/adicionar")
@adm_cli_required
def adicionar():
    """Adiciona um produto ao carrinho."""

    try:
        produto_id = int(request.form.get("produto_id", ""))
        quantidade = int(request.form.get("quantidade", ""))

    except (ValueError, TypeError):
        produto_id = 0
        quantidade = 0

    produto = prato_model.buscar(produto_id)

    if produto is None or quantidade <= 0:
        flash("Selecione um produto e uma quantidade válida.", "erro")
        return redirect(url_for("pedido.novo"))

    if not produto["ativo"]:
        flash("Este prato está indisponível no momento.", "erro")
        return redirect(url_for("pedido.novo"))

    chef_id = session.get("chef_id")

    # Sem cozinheiro (ou com um que não faz o prato), vai pra lista de cozinheiros
    # do prato. O pedido fica guardado e termina quando ela escolher
    if not chef_id or not chefs_model.verificar_chef_produto(
        chef_id, produto_id
    ):
        session["pedido_pendente"] = {
            "produto_id": produto_id,
            "quantidade": quantidade
        }

        if chef_id:
            flash(
                "O cozinheiro selecionado não prepara este prato. "
                "Escolha outro cozinheiro.",
                "aviso"
            )
        else:
            flash(
                "Escolha o cozinheiro que vai preparar este prato.",
                "aviso"
            )

        return redirect(url_for("chefs.por_prato", id_p=produto_id))

    carrinho_service.incluir_no_carrinho(produto, quantidade)

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
    session.pop("pedido_pendente", None)

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
        pedido_id, avisos = pedido_model.finalizar(
            session["usuario_id"],
            chef_id,
            carrinho,
            endereco["id"]
        )
    except ValueError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("pedido.novo"))

    # Limpa o pedido finalizado
    session.pop("carrinho", None)
    session.pop("chef_id", None)
    session.pop("categoria_id", None)
    session.pop("produto_id", None)
    session.pop("pedido_pendente", None)

    flash(
        "Pedido registrado com sucesso.",
        "sucesso"
    )

    # Avisa quais porções usaram ingrediente alternativo
    for aviso in avisos:
        flash(aviso, "aviso")

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

    # Admin vê qualquer pedido
    if cargo == "administrador":

        pode_alterar_status = True
        pode_cancelar = False

    # Cliente só vê os próprios
    elif cargo == "cliente":

        if pedido["usuario_id"] != usuario_id:
            abort(403)

        pode_alterar_status = False

        pode_cancelar = (
            pedido["status"] not in {"entregue", "cancelado"}
        )

    # Cozinheiro só vê os dele
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
        substituicoes=pedido_model.substituicoes_por_item(pedido_id),
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

    # Admin também pode cancelar
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

    # Cozinheiro só altera os próprios pedidos
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

    # Não deixa cancelar pedido de outra pessoa
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
