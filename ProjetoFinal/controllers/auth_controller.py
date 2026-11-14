"""Rotas públicas de autenticação e cadastro de usuários."""

from psycopg import IntegrityError

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

from models import perfil_chef_model
from models import usuario_model as usuario_model
from utils import administrador_required
from utils import salvar_imagem

# Foto usada quando nenhuma imagem é enviada.
FOTO_PADRAO = "images/fotos_perfil/usuarios/template_usuarios.jpeg"

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

        # Procura o usuário no banco.
        usuario = usuario_model.buscar_por_usuario(
            nome_usuario
        )

        # Verifica se o usuário existe
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

            # Guarda o ID do usuário.
            session["usuario_id"] = usuario["id"]

            # Guarda o nome para exibição.
            session["usuario_nome"] = usuario["nome"]

            # Guarda o cargo para controle de permissões.
            session["cargo"] = usuario["cargo"]

            # Cozinheiro cadastrado pelo administrador ainda não tem perfil:
            # leva direto para o cadastro do perfil.
            if (
                usuario["cargo"] == "cozinheiro"
                and perfil_chef_model.perfil_id(usuario["id"]) is None
            ):
                return redirect(
                    url_for("perfil_chef.cadastrar")
                )

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


def _cadastrar_usuario(cargos_permitidos, template):
    """Valida o formulário e cria o usuário.

    Usada pelo cadastro público e pelo cadastro feito pelo administrador.
    """

    if request.method != "POST":
        return render_template(template)

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

    # Validação básica dos campos.
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

        return render_template(template)

    try:

        # A foto é guardada no banco (a Vercel não permite gravar em disco).
        foto_url = salvar_imagem(
            request.files.get("foto_perfil")
        ) or FOTO_PADRAO

        # Transforma a senha em hash
        # antes de armazená-la.
        senha_hash = generate_password_hash(
            senha
        )

        # Cria o usuário.
        usuario_id = usuario_model.criar(
            nome,
            nome_usuario,
            senha_hash,
            cargo,
            foto_url
        )

    except ValueError as erro:

        # Imagem inválida.
        flash(
            str(erro),
            "erro"
        )

        return render_template(template)

    except IntegrityError:

        # O usuário possui uma restrição UNIQUE.
        flash(
            "Esse nome de usuário já está em uso.",
            "erro"
        )

        return render_template(template)

    return usuario_id, cargo


@auth_bp.route(
    "/cadastro",
    methods=("GET", "POST")
)
def cadastro():

    resultado = _cadastrar_usuario(
        {"cliente", "cozinheiro"},
        "cadastro_usuario.html"
    )

    # Formulário (GET) ou erro de validação: já é uma resposta.
    if not isinstance(resultado, tuple):
        return resultado

    usuario_id, cargo = resultado

    # Entra automaticamente com a conta recém-criada.
    session.clear()

    session["usuario_id"] = usuario_id
    session["usuario_nome"] = request.form.get("nome", "").strip()
    session["cargo"] = cargo

    if cargo == "cliente":
        return redirect(
            url_for("endereco.cadastrar")
        )

    return redirect(
        url_for("perfil_chef.cadastrar")
    )


@auth_bp.route(
    "/adm/cadastro",
    methods=("GET", "POST")
)
@administrador_required
def cadastro_adm():

    resultado = _cadastrar_usuario(
        {"cliente", "cozinheiro", "administrador"},
        "adm_cadastro_usuario.html"
    )

    # Formulário (GET) ou erro de validação: já é uma resposta.
    if not isinstance(resultado, tuple):
        return resultado

    usuario_id, cargo = resultado

    # Mantém o comportamento original: cliente criado por aqui
    # assume a sessão e segue para o cadastro de endereço.
    if cargo == "cliente":

        session.clear()

        session["usuario_id"] = usuario_id
        session["usuario_nome"] = request.form.get("nome", "").strip()
        session["cargo"] = cargo

        return redirect(
            url_for("endereco.cadastrar")
        )

    flash(
        "Novo usuário cadastrado.",
        "sucesso"
    )

    return redirect(
        url_for("main.inicio")
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
