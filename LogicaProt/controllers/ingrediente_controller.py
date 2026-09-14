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

from models import ingrediente as ingrediente_model


# Blueprint dos ingredientes.
ingrediente_bp = Blueprint(
    "ingrediente",
    __name__,
    url_prefix="/ingredientes"
)


def _dados_formulario():

    # Obtém o nome.
    nome = request.form.get(
        "nome",
        ""
    ).strip()

    # Obtém a unidade.
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

    # Valida os dados.
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

    # Obtém o termo da pesquisa.
    busca = request.args.get(
        "busca",
        ""
    )

    # Busca os ingredientes.
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
def novo():

    if request.method == "POST":

        try:

            # Obtém os dados.
            dados = _dados_formulario()

            # Cria o ingrediente.
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
def editar(ingrediente_id):

    # Busca o ingrediente.
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
def excluir(ingrediente_id):

    # Verifica se o ingrediente existe.
    if ingrediente_model.buscar(
        ingrediente_id
    ) is None:
        abort(404)

    # Exclui o ingrediente.
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