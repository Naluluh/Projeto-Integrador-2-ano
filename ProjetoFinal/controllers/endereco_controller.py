# Rotas do endereço do cliente
"""Controller responsável pelo cadastro de endereço."""

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from models import endereco_model as endereco_model
from utils import adm_cli_required

endereco_bp = Blueprint(
    "endereco",
    __name__,
    url_prefix="/endereco"
)


# Cadastra o endereço do cliente
@endereco_bp.route(
    "/cadastro",
    methods=("GET", "POST")
)
@adm_cli_required
def cadastrar():

    if request.method == "POST":

        cep = request.form.get(
            "cep",
            ""
        ).strip()

        logradouro = request.form.get(
            "logradouro",
            ""
        ).strip()

        numero = request.form.get(
            "numero",
            ""
        ).strip()

        complemento = request.form.get(
            "complemento",
            ""
        ).strip()

        bairro = request.form.get(
            "bairro",
            ""
        ).strip()

        cidade = request.form.get(
            "cidade",
            ""
        ).strip()

        estado = request.form.get(
            "estado",
            ""
        ).strip()

        pais = request.form.get(
            "pais",
            "Brasil"
        ).strip()

        if not all([
            cep,
            logradouro,
            numero,
            bairro,
            cidade,
            estado,
            pais
        ]):
            flash(
                "Preencha todos os campos obrigatórios.",
                "erro"
            )

            return render_template(
                "cadastrar_endereco.html"
            )

        endereco_model.criar(
            session["usuario_id"],
            cep,
            logradouro,
            numero,
            complemento,
            bairro,
            cidade,
            estado,
            pais
        )

        flash(
            "Endereço cadastrado com sucesso.",
            "sucesso"
        )

        return redirect(
            url_for("main.inicio")
        )

    return render_template(
        "cadastrar_endereco.html"
    )

# Edita o endereço do cliente
@endereco_bp.route("/editar", methods=("GET", "POST"))
@adm_cli_required
def editar():

    usuario_id = session["usuario_id"]

    endereco = endereco_model.ultimo_endereco(usuario_id)
    if endereco is None:

        flash("Você ainda não possui um endereço cadastrado.", "erro")
        return redirect(url_for("endereco.cadastrar"))

    if request.method == "POST":

        cep = request.form.get("cep", "").strip()
        logradouro = request.form.get("logradouro", "").strip()
        numero = request.form.get("numero", "").strip()
        complemento = request.form.get("complemento", "").strip()
        bairro = request.form.get("bairro", "").strip()
        cidade = request.form.get("cidade", "").strip()
        estado = request.form.get("estado", "").strip()
        pais = request.form.get("pais", "Brasil").strip()

        if not all([
            cep,
            logradouro,
            numero,
            bairro,
            cidade,
            estado,
            pais
        ]):
            flash("Preencha todos os campos obrigatórios.", "erro")

            return render_template(
                "editar_endereco.html",
                endereco=endereco
            )

        endereco_model.atualizar(
            endereco["id"],
            usuario_id,
            cep,
            logradouro,
            numero,
            complemento,
            bairro,
            cidade,
            estado,
            pais
        )

        flash("Endereço atualizado com sucesso.", "sucesso")

        return redirect(url_for("pedido.novo"))

    return render_template(
        "editar_endereco.html",
        endereco=endereco
    )