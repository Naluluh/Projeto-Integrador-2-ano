"""Controller responsável pelo cadastro do perfil do cozinheiro."""

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from models import perfil_chef_model as perfil_model
from models.categorias_model import pegar_categorias
from utils import cozinheiro_required

perfil_bp = Blueprint(
    "perfil_chef",
    __name__,
    url_prefix="/perfil/chef"
)


@perfil_bp.route("/cadastrar", methods=("GET", "POST"))
@cozinheiro_required
def cadastrar():
    usuario_id = session["usuario_id"]

    # Evita criar dois perfis para o mesmo cozinheiro.
    if perfil_model.perfil_id(usuario_id) is not None:
        flash("Você já possui um perfil cadastrado.", "erro")
        return redirect(url_for("main.inicio"))

    if request.method == "POST":
        formacao = request.form.get("formacao", "").strip()
        biografia = request.form.get("biografia", "").strip()
        experiencia = request.form.get("experiencia", "").strip()

        # Lista de IDs das categorias selecionadas.
        categorias = request.form.getlist("categoria")

        if not biografia or not categorias:
            flash("Preencha todos os campos obrigatórios.", "erro")
            return render_template(
                "cadastrar_p_cozinheiro.html",
                categorias=pegar_categorias()
            )

        try:
            perfil_model.criar(
                usuario_id,
                formacao,
                biografia,
                categorias,
                experiencia
            )
        except Exception as erro:
            flash(f"Erro ao cadastrar perfil: {erro}", "erro")
            return render_template(
                "cadastrar_p_cozinheiro.html",
                categorias=pegar_categorias()
            )

        flash("Perfil cadastrado com sucesso.", "sucesso")
        return redirect(url_for("main.inicio"))

    return render_template(
        "cadastrar_p_cozinheiro.html",
        categorias=pegar_categorias()
    )