"""CRUD de ingredientes."""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for
)

from models import ingrediente_model as ingrediente_model
from utils import administrador_required
from utils import cozinheiro_required
from utils import cliente_required


# Blueprint dos ingredientes.
ingrediente_bp = Blueprint(
    "ingrediente",
    __name__,
    url_prefix="/ingredientes"
)

@administrador_required
def _dados_formulario():

    nome = request.form.get(
        "nome",
        ""
    ).strip()

    unidade = request.form.get(
        "unidade",
        ""
    ).strip()

    # Converte o estoque para número.
    try:
        estoque = float(
            request.form.get(
                "estoque",
                "0"
            )
        )
    except ValueError:
        estoque = -1

    if (
        not nome
        or not unidade
        or estoque < 0
    ):
        raise ValueError(
            "Dados inválidos."
        )

    return nome, unidade, estoque


@ingrediente_bp.get("")
def listar():

    busca = request.args.get(
        "busca",
        ""
    )

    ingredientes = ingrediente_model.listar(
        busca
    )

    return render_template(
        "ingredientes.html",
        ingredientes=ingredientes,
        busca=busca
    )

@ingrediente_bp.route(
    "/novo",
    methods=("GET", "POST")
)

@administrador_required
def novo():

    if request.method == "POST":

        try:

            dados = _dados_formulario()

            ingrediente_model.criar(
                *dados
            )

            flash(
                "Ingrediente cadastrado.",
                "sucesso"
            )

            return redirect(
                url_for("ingrediente.listar")
            )

        except (ValueError, TypeError):

            flash(
                "Preencha os dados corretamente.",
                "erro"
            )

    return render_template(
        "ingrediente_form.html",
        ingrediente=None
    )


@ingrediente_bp.route(
    "/<int:ingrediente_id>/editar",
    methods=("GET", "POST")
)

@administrador_required
def editar(ingrediente_id):

    ingrediente = ingrediente_model.buscar(
        ingrediente_id
    )

    if ingrediente is None:
        abort(404)

    if request.method == "POST":

        try:

            dados = _dados_formulario()

            ingrediente_model.atualizar(
                ingrediente_id,
                *dados
            )

            flash(
                "Ingrediente atualizado.",
                "sucesso"
            )

            return redirect(
                url_for("ingrediente.listar")
            )

        except (ValueError, TypeError):

            flash(
                "Preencha os dados corretamente.",
                "erro"
            )

    return render_template(
        "ingrediente_form.html",
        ingrediente=ingrediente
    )


@ingrediente_bp.post(
    "/<int:ingrediente_id>/excluir"
)

@administrador_required
def excluir(ingrediente_id):

    if ingrediente_model.buscar(
        ingrediente_id
    ) is None:
        abort(404)

    ingrediente_model.excluir(
        ingrediente_id
    )

    flash(
        "Ingrediente excluído.",
        "sucesso"
    )

    return redirect(
        url_for("ingrediente.listar")
    )