"""Rotas de autenticação: login, cadastro, troca e recuperação de senha."""

import math
import time

from sqlalchemy.exc import IntegrityError

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

from models import login_model
from models import perfil_chef_model
from models import usuario_model as usuario_model
from utils import administrador_required
from utils import ip_cliente
from utils import salvar_imagem
from utils import validar_nova_senha

# Foto padrão quando não envia imagem
FOTO_PADRAO = "images/fotos_perfil/usuarios/template_usuarios.jpeg"

# Blueprint de autenticação
auth_bp = Blueprint("auth", __name__)


def _iniciar_sessao(usuario_id, nome, cargo, trocar_senha=False):
    """Cria a sessão da pessoa que acabou de entrar."""

    # Limpa dados antigos da sessão
    session.clear()

    session["usuario_id"] = usuario_id
    session["usuario_nome"] = nome
    session["cargo"] = cargo

    # Início do timeout de inatividade (ver app.py)
    session["ultima_atividade"] = int(time.time())

    # Senha temporária: só navega depois de trocar a senha
    if trocar_senha:
        session["trocar_senha"] = True


def _destino_apos_login(usuario_id, cargo, proxima=None):
    """Para onde a pessoa vai depois de entrar."""

    # Cozinheiro novo ainda sem perfil: vai direto pro cadastro do perfil
    if (
        cargo == "cozinheiro"
        and perfil_chef_model.perfil_id(usuario_id) is None
    ):
        return url_for("perfil_chef.cadastrar")

    return proxima or url_for("main.inicio")


def _proxima_segura(valor):
    """Aceita só caminhos internos (evita redirecionar para outro site)."""

    if (
        valor
        and valor.startswith("/")
        and not valor.startswith("//")
        and "\\" not in valor
    ):
        return valor

    return None


def _texto_espera(segundos):
    minutos = math.ceil(segundos / 60)

    if minutos <= 1:
        return "cerca de 1 minuto"

    return f"cerca de {minutos} minutos"


@auth_bp.route("/login", methods=("GET", "POST"))
def login():

    proxima = _proxima_segura(
        request.args.get("proxima") or request.form.get("proxima")
    )

    if request.method == "POST":

        nome_usuario = request.form.get("usuario", "").strip()[:64]

        senha = request.form.get("senha", "")

        # Conta tentativas por usuário e por IP
        # (assim não dá pra testar vários usuários do mesmo lugar)
        chave_usuario = f"usuario:{nome_usuario.lower()}"
        chave_ip = f"ip:{ip_cliente()}"

        espera = login_model.segundos_de_bloqueio(
            [chave_usuario, chave_ip]
        )

        if espera:
            flash(
                "Muitas tentativas de login. Por segurança, aguarde "
                f"{_texto_espera(espera)} para tentar novamente.",
                "erro"
            )

            return render_template("login.html", proxima=proxima), 429

        usuario = usuario_model.buscar_por_usuario(nome_usuario)

        # Confere usuário e senha
        if usuario and check_password_hash(usuario["senha_hash"], senha):

            login_model.limpar(chave_usuario)

            _iniciar_sessao(
                usuario["id"],
                usuario["nome"],
                usuario["cargo"],
                trocar_senha=bool(usuario["senha_temporaria"])
            )

            if usuario["senha_temporaria"]:
                flash(
                    "Você entrou com uma senha temporária. "
                    "Defina uma nova senha para continuar.",
                    "aviso"
                )

                return redirect(url_for("auth.alterar_senha"))

            return redirect(
                _destino_apos_login(
                    usuario["id"], usuario["cargo"], proxima
                )
            )

        # Login errado: conta a falha
        bloqueio = max(
            login_model.registrar_falha(chave_usuario),
            login_model.registrar_falha(chave_ip)
        )

        if bloqueio:
            flash(
                "Limite de tentativas atingido. O login ficou bloqueado por "
                f"{_texto_espera(bloqueio)}.",
                "erro"
            )

            return render_template("login.html", proxima=proxima), 429

        # Mesma mensagem para usuário inexistente e senha errada
        flash("Usuário ou senha inválidos.", "erro")

    return render_template("login.html", proxima=proxima)


def _cadastrar_usuario(cargos_permitidos, template):
    """Valida o formulário e cria o usuário.

    Usada pelo cadastro público e pelo cadastro feito pelo administrador.
    """

    if request.method != "POST":
        return render_template(template, dados={})

    nome = request.form.get("nome", "").strip()
    nome_usuario = request.form.get("usuario", "").strip()
    senha = request.form.get("senha", "")
    confirmacao = request.form.get("confirmar_senha", "")
    cargo = request.form.get("cargo", "").strip()

    # Se der erro, mantém o digitado (menos as senhas)
    dados = {"nome": nome, "usuario": nome_usuario, "cargo": cargo}

    # Validação dos campos
    if (
        len(nome) < 2
        or len(nome_usuario) < 3
        or cargo not in cargos_permitidos
    ):
        flash("Preencha todos os campos corretamente.", "erro")
        return render_template(template, dados=dados)

    # Regras de senha e confirmação
    erro_senha = validar_nova_senha(senha, confirmacao)

    if erro_senha:
        flash(erro_senha, "erro")
        return render_template(template, dados=dados)

    try:

        # Foto vai pro banco
        foto_url = salvar_imagem(
            request.files.get("foto_perfil")
        ) or FOTO_PADRAO

        # Guarda a senha em hash
        senha_hash = generate_password_hash(senha)

        usuario_id = usuario_model.criar(
            nome,
            nome_usuario,
            senha_hash,
            cargo,
            foto_url
        )

    except ValueError as erro:

        # Imagem inválida
        flash(str(erro), "erro")
        return render_template(template, dados=dados)

    except IntegrityError:

        # Usuário repetido (UNIQUE)
        flash("Esse nome de usuário já está em uso.", "erro")
        return render_template(template, dados=dados)

    return usuario_id, cargo


@auth_bp.route("/cadastro", methods=("GET", "POST"))
def cadastro():

    resultado = _cadastrar_usuario(
        {"cliente", "cozinheiro"},
        "cadastro_usuario.html"
    )

    # GET ou erro de validação: já é uma resposta
    if not isinstance(resultado, tuple):
        return resultado

    usuario_id, cargo = resultado

    # Já entra com a conta nova
    _iniciar_sessao(usuario_id, request.form.get("nome", "").strip(), cargo)

    if cargo == "cliente":
        return redirect(url_for("endereco.cadastrar"))

    return redirect(url_for("perfil_chef.cadastrar"))


@auth_bp.route("/adm/cadastro", methods=("GET", "POST"))
@administrador_required
def cadastro_adm():

    resultado = _cadastrar_usuario(
        {"cliente", "cozinheiro", "administrador"},
        "adm_cadastro_usuario.html"
    )

    # GET ou erro de validação: já é uma resposta
    if not isinstance(resultado, tuple):
        return resultado

    usuario_id, cargo = resultado

    # Mesmo comportamento de antes: o cliente criado aqui assume a sessão
    # e segue para o cadastro de endereço
    if cargo == "cliente":

        _iniciar_sessao(
            usuario_id, request.form.get("nome", "").strip(), cargo
        )

        return redirect(url_for("endereco.cadastrar"))

    flash("Novo usuário cadastrado.", "sucesso")

    return redirect(url_for("main.inicio"))


@auth_bp.route("/alterar-senha", methods=("GET", "POST"))
def alterar_senha():
    """Troca de senha de quem está logado (exige a senha atual)."""

    usuario = usuario_model.buscar(session["usuario_id"])

    if usuario is None:
        session.clear()
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        atual = request.form.get("senha_atual", "")
        nova = request.form.get("senha", "")
        confirmacao = request.form.get("confirmar_senha", "")

        # Limita tentativas da senha atual (evita adivinhar com a sessão aberta)
        chave = f"senha:{usuario['id']}"
        espera = login_model.segundos_de_bloqueio([chave])

        if espera:
            flash(
                "Muitas tentativas. Aguarde "
                f"{_texto_espera(espera)} para tentar novamente.",
                "erro"
            )
            return render_template("alterar_senha.html"), 429

        if not check_password_hash(usuario["senha_hash"], atual):
            login_model.registrar_falha(chave)
            flash("A senha atual está incorreta.", "erro")
            return render_template("alterar_senha.html")

        erro = validar_nova_senha(nova, confirmacao)

        if erro:
            flash(erro, "erro")
            return render_template("alterar_senha.html")

        if check_password_hash(usuario["senha_hash"], nova):
            flash("A nova senha deve ser diferente da senha atual.", "erro")
            return render_template("alterar_senha.html")

        usuario_model.atualizar_senha(
            usuario["id"],
            generate_password_hash(nova),
            temporaria=False
        )

        login_model.limpar(chave)
        session.pop("trocar_senha", None)

        flash("Senha alterada com sucesso.", "sucesso")

        return redirect(
            _destino_apos_login(usuario["id"], usuario["cargo"])
        )

    return render_template("alterar_senha.html")


@auth_bp.route("/esqueci-senha", methods=("GET", "POST"))
def esqueci_senha():
    """Pedido de redefinição de senha.

    O sistema não guarda e-mail nem telefone, então não há como enviar um
    link. O pedido fica visível para o administrador, que gera uma senha
    temporária e a repassa à pessoa (ela será obrigada a trocá-la ao entrar).
    """

    if request.method == "POST":

        # Cada pedido conta como tentativa (não enche a lista do admin)
        chave_ip = f"reset:{ip_cliente()}"
        espera = login_model.segundos_de_bloqueio([chave_ip])

        if espera:
            flash(
                "Muitos pedidos seguidos. Aguarde "
                f"{_texto_espera(espera)} e tente novamente.",
                "erro"
            )
            return render_template("esqueci_senha.html"), 429

        login_model.registrar_falha(chave_ip)

        nome_usuario = request.form.get("usuario", "").strip()[:64]

        if nome_usuario:
            usuario_model.solicitar_redefinicao(
                nome_usuario, int(time.time())
            )

        # Mesma resposta exista a conta ou não (não revela quem tem conta)
        flash(
            "Pedido registrado. Se o usuário existir, o administrador "
            "foi avisado e vai gerar uma senha temporária para você.",
            "sucesso"
        )

        return redirect(url_for("auth.login"))

    return render_template("esqueci_senha.html")


@auth_bp.post("/logout")
def logout():

    # Limpa a sessão
    session.clear()

    flash("Sessão encerrada.", "sucesso")

    return redirect(url_for("auth.login"))
