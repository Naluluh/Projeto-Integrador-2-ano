"""Rotas públicas de autenticação e cadastro de funcionários."""

import sqlite3

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from models import usuario as usuario_model
from utils import administrador_required
from utils import cozinheiro_required
from utils import cliente_required


# Cria o Blueprint responsável pela autenticação.
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=("GET", "POST"))
def login():

    # Se o formulário foi enviado.
    if request.method == "POST":

        # Obtém o usuário informado.
        nome_usuario = request.form.get(
            "usuario",
            ""
        ).strip()

        # Obtém a senha.
        senha = request.form.get(
            "senha",
            ""
        )

        # Procura o funcionário no banco.
        usuario = usuario_model.buscar_por_usuario(
            nome_usuario
        )

        # Verifica se o funcionário existe
        # e se a senha está correta.
        if (
            usuario
            and check_password_hash(
                usuario["senha_hash"],
                senha
            )
        ):

            # Remove dados antigos da sessão.
            session.clear()

            # Guarda o ID do funcionário.
            session["usuario_id"] = usuario["id"]

            # Guarda o nome para exibição.
            session["usuario_nome"] = usuario["nome"]

            # Guarda o cargo para controle de permissões.
            session["cargo"] = usuario["cargo"]

            # Vai para o painel principal.
            return redirect(
                url_for("main.inicio")
            )

        # Login inválido.
        flash(
            "Usuário ou senha inválidos.",
            "erro"
        )

    # Exibe a tela de login.
    return render_template("login.html")


@auth_bp.route(
    "/cadastro",
    methods=("GET", "POST")
)
def cadastro():

    # Verifica se o formulário foi enviado.
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

        # Tipos de usuário permitidos
        # no cadastro público.
        cargos_publicos = {
            "cliente",
            "cozinheiro"
        }

        # Validação básica dos campos.
        if (
            len(nome) < 2
            or len(nome_usuario) < 3
            or len(senha) < 6
            or cargo not in cargos_publicos
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

                # Cria o funcionário.
                usuario_model.criar(
                    nome,
                    nome_usuario,
                    senha_hash,
                    cargo
                )

                flash(
                    "Cadastro realizado. Agora faça o login.",
                    "sucesso"
                )

                return redirect(
                    url_for("auth.login")
                )

            except sqlite3.IntegrityError:

                # O usuário possui uma restrição UNIQUE.
                flash(
                    "Esse nome de usuário já está em uso.",
                    "erro"
                )

    return render_template(
        "cadastro_usuario.html"
    )


@auth_bp.post("/logout")
def logout():

    # Remove todos os dados da sessão.
    session.clear()

    flash(
        "Sessão encerrada.",
        "sucesso"
    )

    return redirect(
        url_for("auth.login")
    )
