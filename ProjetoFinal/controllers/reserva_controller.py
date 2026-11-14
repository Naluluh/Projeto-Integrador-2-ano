# Rotas das reservas de bancada
import re
from datetime import date, timedelta

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from controllers import carrinho as carrinho_service
from models import categorias_model, chefs_model, prato_model, reserva_model
from utils import cliente_required, hoje_brasilia, login_required


reservas_bp = Blueprint(
    "reservas",
    __name__,
    url_prefix="/reservas"
)

MAX_DIAS_POR_RESERVA = 30
MAX_DIAS_DE_ANTECEDENCIA = 365


# Confere se a pessoa logada pode ver a reserva (dono, admin ou o cozinheiro escolhido)
def _pode_ver(reserva):
    cargo = session.get("cargo")
    usuario_id = session.get("usuario_id")

    if cargo == "administrador":
        return True

    if cargo == "cliente":
        return reserva["cliente_id"] == usuario_id

    return cargo == "cozinheiro" and reserva["chef_id"] == usuario_id


# Dá a cada reserva o status que aparece na tela
def _com_status(reservas):
    return [
        {**dict(r), "status_exibido": reserva_model.status_exibido(r)}
        for r in reservas
    ]


# Lista as reservas conforme o cargo
@reservas_bp.get("/")
@login_required
def listar():
    cargo = session.get("cargo")
    usuario_id = session.get("usuario_id")

    filtros = {
        "data": request.args.get("data", "").strip(),
        "status": request.args.get("status", "").strip(),
        "busca": request.args.get("busca", "").strip()[:60],
    }

    if cargo == "administrador":
        # Data inválida no filtro é ignorada
        try:
            date.fromisoformat(filtros["data"])
        except ValueError:
            filtros["data"] = ""

        reservas = reserva_model.listar_todas(
            filtros["data"] or None,
            filtros["status"] or None,
            filtros["busca"] or None
        )
    elif cargo == "cozinheiro":
        reservas = reserva_model.listar_do_chef(usuario_id)
    else:
        reservas = reserva_model.listar_do_cliente(usuario_id)

    return render_template(
        "reservas.html",
        reservas=_com_status(reservas),
        filtros=filtros
    )


# Bancadas com os cozinheiros de cada uma e os dias já ocupados
def _bancadas_para_o_formulario():
    hoje = hoje_brasilia().isoformat()
    bancadas = []

    for b in categorias_model.pegar_categorias():
        bancadas.append({
            "id": b["id"],
            "nome": b["nome"],
            "chefs": [
                {"id": c["id"], "nome": c["nome"]}
                for c in chefs_model.chefs_categoria(b["id"])
            ],
            "ocupados": reserva_model.dias_reservados_a_partir(b["id"], hoje)
        })

    return bancadas


# Valida o formulário. Devolve (dados, erro)
def _validar_formulario(form):
    hoje = hoje_brasilia()

    try:
        categoria_id = int(form.get("categoria_id", ""))
        chef_id = int(form.get("chef_id", ""))
    except ValueError:
        return None, "Escolha a bancada e o cozinheiro."

    if categorias_model.id_categoria(categoria_id) is None:
        return None, "Bancada inválida."

    if not chefs_model.verificar_chef_categoria(chef_id, categoria_id):
        return None, "Esse cozinheiro não atende essa bancada."

    try:
        inicio = date.fromisoformat(form.get("data_inicio", ""))
        fim = date.fromisoformat(form.get("data_fim", "") or form.get("data_inicio", ""))
    except ValueError:
        return None, "Informe uma data válida."

    if inicio < hoje:
        return None, "A data inicial não pode ser no passado."

    if fim < inicio:
        return None, "A data final não pode ser antes da inicial."

    if (fim - inicio).days + 1 > MAX_DIAS_POR_RESERVA:
        return None, f"A reserva pode ter no máximo {MAX_DIAS_POR_RESERVA} dias."

    if inicio > hoje + timedelta(days=MAX_DIAS_DE_ANTECEDENCIA):
        return None, "Só é possível reservar com até 1 ano de antecedência."

    try:
        pessoas = int(form.get("pessoas", ""))
    except ValueError:
        pessoas = 0

    if not 1 <= pessoas <= 50:
        return None, "Informe de 1 a 50 pessoas."

    telefone = form.get("telefone", "").strip()

    if not 8 <= len(re.sub(r"\D", "", telefone)) <= 15:
        return None, "Informe um telefone válido."

    email = form.get("email", "").strip()

    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return None, "Informe um e-mail válido."

    return {
        "categoria_id": categoria_id,
        "chef_id": chef_id,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "pessoas": pessoas,
        "telefone": telefone[:30],
        "email": email[:120] or None,
        "observacoes": form.get("observacoes", "").strip()[:500] or None,
    }, None


# Mostra o formulário e cria a reserva
@reservas_bp.route("/nova", methods=["GET", "POST"])
@cliente_required
def nova():
    bancadas = _bancadas_para_o_formulario()
    dados = {"categoria_id": request.args.get("bancada", "")}

    if request.method == "POST":
        dados = request.form.to_dict()
        validados, erro = _validar_formulario(request.form)

        if erro:
            flash(erro, "erro")
        else:
            try:
                reserva_id = reserva_model.criar(
                    session["usuario_id"],
                    validados["categoria_id"],
                    validados["chef_id"],
                    validados["inicio"],
                    validados["fim"],
                    validados["pessoas"],
                    validados["telefone"],
                    validados["email"],
                    validados["observacoes"]
                )

                flash("Reserva confirmada.", "sucesso")

                return redirect(url_for("reservas.detalhes", reserva_id=reserva_id))

            except reserva_model.BancadaOcupada as e:
                dias = ", ".join(
                    date.fromisoformat(d).strftime("%d/%m/%Y") for d in e.dias
                )

                flash(
                    f"Essa bancada já está reservada em: {dias}. "
                    "Escolha outros dias ou outra bancada.",
                    "erro"
                )

    return render_template(
        "reserva_form.html",
        bancadas=bancadas,
        dados=dados,
        hoje=hoje_brasilia().isoformat(),
        max_dias=MAX_DIAS_POR_RESERVA
    )


# Página da reserva: cardápio da bancada com o cozinheiro e os pedidos dela
@reservas_bp.get("/<int:reserva_id>")
@login_required
def detalhes(reserva_id):
    reserva = reserva_model.buscar(reserva_id)

    if reserva is None or not _pode_ver(reserva):
        abort(404)

    aceita = reserva_model.aceita_pedidos(reserva)
    do_cliente = session.get("cargo") == "cliente"

    carrinho = []

    if do_cliente and session.get("reserva_id") == reserva_id:
        carrinho = carrinho_service.itens_do_carrinho()

    return render_template(
        "reserva_detalhes.html",
        reserva={**dict(reserva), "status_exibido": reserva_model.status_exibido(reserva)},
        aceita=aceita,
        produtos=reserva_model.produtos_da_reserva(reserva) if aceita else [],
        pedidos=reserva_model.pedidos_da_reserva(reserva_id),
        carrinho=carrinho,
        total=sum(i["preco_centavos"] * i["quantidade"] for i in carrinho)
    )


# Cancela a reserva (o dono ou o admin) e libera a bancada
@reservas_bp.post("/<int:reserva_id>/cancelar")
@login_required
def cancelar(reserva_id):
    reserva = reserva_model.buscar(reserva_id)
    cargo = session.get("cargo")

    pode = reserva is not None and (
        cargo == "administrador"
        or (cargo == "cliente" and reserva["cliente_id"] == session["usuario_id"])
    )

    if not pode:
        abort(404)

    if not reserva_model.aceita_pedidos(reserva):
        flash("Essa reserva não pode mais ser cancelada.", "erro")
        return redirect(url_for("reservas.detalhes", reserva_id=reserva_id))

    reserva_model.cancelar(reserva_id)

    if session.get("reserva_id") == reserva_id:
        session.pop("reserva_id", None)

    flash("Reserva cancelada. A bancada foi liberada.", "sucesso")

    return redirect(url_for("reservas.listar"))


# Põe um prato da reserva no carrinho (só pratos da bancada e do cozinheiro dela)
@reservas_bp.post("/<int:reserva_id>/pedido")
@cliente_required
def adicionar_prato(reserva_id):
    reserva = reserva_model.buscar(reserva_id)

    if reserva is None or reserva["cliente_id"] != session["usuario_id"]:
        abort(404)

    destino = redirect(url_for("reservas.detalhes", reserva_id=reserva_id))

    if not reserva_model.aceita_pedidos(reserva):
        flash("Essa reserva não aceita mais pedidos.", "erro")
        return destino

    try:
        produto_id = int(request.form.get("produto_id", ""))
        quantidade = int(request.form.get("quantidade", ""))
    except ValueError:
        produto_id = quantidade = 0

    produto = prato_model.buscar(produto_id)

    valido = (
        produto is not None
        and produto["ativo"]
        and quantidade > 0
        and produto["categoria_id"] == reserva["categoria_id"]
        and chefs_model.verificar_chef_produto(reserva["chef_id"], produto_id)
    )

    if not valido:
        flash("Esse prato não faz parte desta reserva.", "erro")
        return destino

    # Carrinho de outra reserva ou de outra bancada começa do zero
    if session.get("reserva_id") != reserva_id:
        session.pop("carrinho", None)

    carrinho_service.definir_chef(
        reserva["chef_id"],
        categoria_id=reserva["categoria_id"]
    )
    session["reserva_id"] = reserva_id

    carrinho_service.incluir_no_carrinho(produto, quantidade)

    return destino
