"""Controller responsável pelo gerenciamento de funcionários."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from models import funcionario as funcionario_model


# Cria o Blueprint responsável pelas rotas de funcionários.
funcionario_bp = Blueprint(
    "funcionario",
    __name__,
    url_prefix="/funcionarios"
)


@funcionario_bp.get("")
def listar():
    # Busca todos os funcionários cadastrados.
    funcionarios = funcionario_model.listar()

    # Envia os funcionários para a página HTML.
    return render_template(
        "funcionarios.html",
        funcionarios=funcionarios
    )


@funcionario_bp.route("/novo", methods=("GET", "POST"))
def novo():
    # Se o formulário foi enviado.
    if request.method == "POST":

        # Obtém os dados enviados pelo formulário.
        nome = request.form.get("nome", "").strip()
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        cargo = request.form.get("cargo", "").strip()

        # Verifica se os dados possuem valores válidos.
        if (
            len(nome) < 2
            or len(usuario) < 3
            or len(senha) < 6
            or not cargo
        ):
            flash(
                "Preencha todos os campos corretamente.",
                "erro"
            )

        else:
            try:
                # Transforma a senha em um hash antes de armazená-la.
                senha_hash = generate_password_hash(senha)

                # Cria o funcionário no banco.
                funcionario_model.criar(
                    nome,
                    usuario,
                    senha_hash,
                    cargo
                )

                flash(
                    "Funcionário cadastrado com sucesso.",
                    "sucesso"
                )

                return redirect(
                    url_for("funcionario.listar")
                )

            except ValueError as erro:
                # Mostra erros de validação retornados pelo Model.
                flash(str(erro), "erro")

        # Permite que o formulário seja exibido novamente
        # com os dados digitados.
        return render_template(
            "funcionario_form.html",
            funcionario=None
        )

    # Exibe o formulário vazio para um novo funcionário.
    return render_template(
        "funcionario_form.html",
        funcionario=None
    )


@funcionario_bp.route(
    "/<int:funcionario_id>/editar",
    methods=("GET", "POST")
)
def editar(funcionario_id):
    # Busca o funcionário pelo ID.
    funcionario = funcionario_model.buscar(funcionario_id)

    # Se o funcionário não existir, retorna 404.
    if funcionario is None:
        abort(404)

    # Se o formulário foi enviado.
    if request.method == "POST":

        # Obtém os dados enviados.
        nome = request.form.get("nome", "").strip()
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        cargo = request.form.get("cargo", "").strip()

        # Valida os campos obrigatórios.
        if (
            len(nome) < 2
            or len(usuario) < 3
            or not cargo
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

                    senha_hash = generate_password_hash(senha)

                else:
                    # Mantém a senha antiga quando nenhuma
                    # nova senha foi informada.
                    senha_hash = funcionario["senha_hash"]

                # Atualiza os dados do funcionário.
                funcionario_model.atualizar(
                    funcionario_id,
                    nome,
                    usuario,
                    senha_hash,
                    cargo
                )

                flash(
                    "Funcionário atualizado com sucesso.",
                    "sucesso"
                )

                return redirect(
                    url_for("funcionario.listar")
                )

            except ValueError as erro:
                flash(str(erro), "erro")

        # Exibe novamente o formulário em caso de erro.
        return render_template(
            "funcionario_form.html",
            funcionario=funcionario
        )

    # Exibe o formulário preenchido.
    return render_template(
        "funcionario_form.html",
        funcionario=funcionario
    )


@funcionario_bp.post("/<int:funcionario_id>/excluir")
def excluir(funcionario_id):
    # Verifica se o funcionário existe.
    funcionario = funcionario_model.buscar(funcionario_id)

    if funcionario is None:
        abort(404)

    # Impede que o funcionário atualmente logado
    # seja excluído acidentalmente.
    from flask import session

    if funcionario_id == session.get("funcionario_id"):
        flash(
            "Você não pode excluir o funcionário atualmente logado.",
            "erro"
        )

        return redirect(
            url_for("funcionario.listar")
        )

    # Remove o funcionário do banco.
    funcionario_model.excluir(funcionario_id)

    flash(
        "Funcionário excluído com sucesso.",
        "sucesso"
    )

    return redirect(
        url_for("funcionario.listar")
    )