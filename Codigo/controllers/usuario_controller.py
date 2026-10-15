"""Controller responsável pelo gerenciamento de funcionários."""

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

from werkzeug.security import generate_password_hash

from models import usuario as usuario_model
from utils import administrador_required


# Cria o Blueprint responsável pelas rotas de funcionários.
usuario_bp = Blueprint(
    "usuario",
    __name__,
    url_prefix="/usuarios"
)

@usuario_bp.get("")
@administrador_required
def listar():

    usuarios = usuario_model.listar()

    return render_template(
        "usuario.html",
        usuarios=usuarios
    )

@usuario_bp.route(
    "/novo",
    methods=("GET", "POST")
)
@administrador_required
def novo():

    # Se o formulário foi enviado.
    if request.method == "POST":

        # Obtém os dados enviados pelo formulário.
        nome = request.form.get(
            "nome",
            ""
        ).strip()

        nome_usuario = request.form.get(
            "usuario",
            ""
        ).strip()

        senha = request.form.get(
            "senha",
            ""
        )

        cargo = request.form.get(
            "cargo",
            ""
        ).strip()

        # Cargos que podem ser criados
        # pelo administrador.
        cargos_permitidos = {
            "cliente",
            "cozinheiro",
            "administrador"
        }

        # Validação dos campos.
        if (
            len(nome) < 2
            or len(nome_usuario) < 3
            or len(senha) < 6
            or cargo not in cargos_permitidos
        ):
            flash(
                "Preencha todos os campos corretamente.",
                "erro"
            )

        else:

            try:

                # Transforma a senha em hash
                # antes de armazená-la.
                senha_hash = generate_password_hash(
                    senha
                )

                # Cria o funcionário no banco.
                usuario_model.criar(
                    nome,
                    nome_usuario,
                    senha_hash,
                    cargo
                )

                flash(
                    "Funcionário cadastrado com sucesso.",
                    "sucesso"
                )

                return redirect(
                    url_for("usuario.listar")
                )

            except ValueError as erro:

                # Mostra erros de validação
                # retornados pelo Model.
                flash(
                    str(erro),
                    "erro"
                )

    # Exibe o formulário.
    return render_template(
        "usuario_form.html",
        usuario=None
    )


@usuario_bp.route(
    "/<int:usuario_id>/editar",
    methods=("GET", "POST")
)
@administrador_required
def editar(usuario_id):

    # Busca o funcionário pelo ID.
    usuario = usuario_model.buscar(
        usuario_id
    )

    # Se o funcionário não existir,
    # retorna 404.
    if usuario is None:
        abort(404)

    # Se o formulário foi enviado.
    if request.method == "POST":

        # Obtém os dados enviados.
        nome = request.form.get(
            "nome",
            ""
        ).strip()

        nome_usuario = request.form.get(
            "usuario",
            ""
        ).strip()

        senha = request.form.get(
            "senha",
            ""
        )

        cargo = request.form.get(
            "cargo",
            ""
        ).strip()

        # Cargos permitidos.
        cargos_permitidos = {
            "cliente",
            "cozinheiro",
            "administrador"
        }

        # Valida os campos obrigatórios.
        if (
            len(nome) < 2
            or len(nome_usuario) < 3
            or cargo not in cargos_permitidos
        ):
            flash(
                "Preencha nome, usuário e cargo corretamente.",
                "erro"
            )

        else:

            try:

                # Se uma nova senha foi informada,
                # cria um novo hash.
                if senha:

                    if len(senha) < 6:
                        raise ValueError(
                            "A senha deve possuir pelo menos 6 caracteres."
                        )

                    senha_hash = generate_password_hash(
                        senha
                    )

                else:

                    # Mantém a senha antiga.
                    senha_hash = usuario[
                        "senha_hash"
                    ]

                # Atualiza os dados.
                usuario_model.atualizar(
                    usuario_id,
                    nome,
                    nome_usuario,
                    senha_hash,
                    cargo
                )

                flash(
                    "Funcionário atualizado com sucesso.",
                    "sucesso"
                )

                return redirect(
                    url_for("usuario.listar")
                )

            except ValueError as erro:

                flash(
                    str(erro),
                    "erro"
                )

        # Exibe novamente o formulário.
        return render_template(
            "usuario_form.html",
            usuario=usuario
        )

    # Exibe o formulário preenchido.
    return render_template(
        "usuario_form.html",
        usuario=usuario
    )


@usuario_bp.post(
    "/<int:usuario_id>/excluir"
)
@administrador_required
def excluir(usuario_id):

    # Verifica se o funcionário existe.
    usuario = usuario_model.buscar(
        usuario_id
    )

    if usuario is None:
        abort(404)

    # Impede que o administrador exclua
    # a própria conta.
    if usuario_id == session.get(
        "usuario_id"
    ):

        flash(
            "Você não pode excluir o funcionário atualmente logado.",
            "erro"
        )

        return redirect(
            url_for("usuario.listar")
        )

    # Remove o funcionário do banco.
    usuario_model.excluir(
        usuario_id
    )

    flash(
        "Funcionário excluído com sucesso.",
        "sucesso"
    )

    return redirect(
        url_for("usuario.listar")
    )