# Rotas do perfil do cozinheiro
"""Controller responsável pelo cadastro do perfil do cozinheiro."""

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

from models import perfil_chef_model as perfil_model
from models.categorias_model import pegar_categorias
from utils import cozinheiro_required

perfil_bp = Blueprint(
    "perfil_chef",
    __name__,
    url_prefix="/perfil/chef"
)


# Cadastra o perfil do cozinheiro
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


# Edita o perfil do cozinheiro
@perfil_bp.route("/editar", methods=("GET", "POST"))
@cozinheiro_required
def editar():
    """O cozinheiro edita formação, biografia e experiência."""

    usuario_id = session["usuario_id"]
    perfil = perfil_model.buscar_perfil(usuario_id)

    if perfil is None:
        return redirect(url_for("perfil_chef.cadastrar"))

    if request.method == "POST":
        formacao = request.form.get("formacao", "").strip()
        biografia = request.form.get("biografia", "").strip()
        experiencia = request.form.get("experiencia", "").strip()

        if not biografia:
            flash("A biografia é obrigatória.", "erro")
            return render_template("perfil_chef_editar.html", perfil=perfil)

        perfil_model.atualizar_dados(
            usuario_id, formacao, biografia, experiencia
        )

        flash("Perfil atualizado.", "sucesso")

        return redirect(url_for("chefs.perfil", chef_id=usuario_id))

    return render_template("perfil_chef_editar.html", perfil=perfil)


# Mostra as bancadas e quais o cozinheiro atende
@perfil_bp.get("/categorias")
@cozinheiro_required
def categorias():
    """Todas as categorias, com a opção de assumir ou deixar cada uma."""

    usuario_id = session["usuario_id"]

    if perfil_model.perfil_id(usuario_id) is None:
        flash("Cadastre seu perfil antes de escolher categorias.", "erro")
        return redirect(url_for("perfil_chef.cadastrar"))

    return render_template(
        "perfil_chef_categorias.html",
        categorias=perfil_model.categorias_com_status(usuario_id)
    )


# O cozinheiro passa a atender a bancada
@perfil_bp.post("/categorias/<int:categoria_id>/adicionar")
@cozinheiro_required
def adicionar_categoria(categoria_id):

    try:
        perfil_model.adicionar_categoria(session["usuario_id"], categoria_id)
    except ValueError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("perfil_chef.categorias"))

    flash(
        "Agora você é responsável por esta categoria e por seus pratos.",
        "sucesso"
    )

    return redirect(url_for("perfil_chef.categorias"))


# O cozinheiro deixa de atender a bancada
@perfil_bp.post("/categorias/<int:categoria_id>/remover")
@cozinheiro_required
def remover_categoria(categoria_id):

    try:
        perfil_model.remover_categoria(session["usuario_id"], categoria_id)
    except ValueError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("perfil_chef.categorias"))

    flash(
        "Você deixou de ser responsável por esta categoria. "
        "Os pedidos que você já preparou continuam no histórico.",
        "sucesso"
    )

    return redirect(url_for("perfil_chef.categorias"))
