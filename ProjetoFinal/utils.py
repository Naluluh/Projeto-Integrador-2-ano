"""Funções pequenas compartilhadas entre Controllers e Views."""

import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import request, url_for

from config import NA_VERCEL

# Brasília (UTC-3), sem horário de verão
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# Tamanho máximo da imagem
TAMANHO_MAXIMO_IMAGEM = 2 * 1024 * 1024


def formatar_datahora(valor):
    """Converte o texto de data/hora do banco para dd/mm/aaaa hh:mm (Brasília)."""
    if not valor:
        return ""

    texto = str(valor).strip()

    try:
        momento = datetime.fromisoformat(texto)
    except ValueError:
        return str(valor)

    # O SQLite grava em UTC, sem o fuso
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)

    return momento.astimezone(FUSO_BRASILIA).strftime("%d/%m/%Y %H:%M")


def url_foto(caminho, padrao=None):
    """Devolve a URL de uma imagem.

    - "db:<id>"   -> foto enviada por um usuário e guardada no banco;
    - outro texto -> arquivo dentro da pasta static.
    """
    caminho = caminho or padrao

    if not caminho:
        return ""

    if str(caminho).startswith("db:"):
        return url_for("main.imagem", imagem_id=int(caminho[3:]))

    return url_for("static", filename=caminho)


def _tipo_da_imagem(dados):
    # Descobre o formato pelo conteúdo, não pelo nome
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if dados.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if dados.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "image/webp"
    return None


def salvar_imagem(arquivo):
    """Guarda a imagem enviada no banco e devolve "db:<id>".

    As fotos enviadas ficam na tabela "imagens" do banco local, junto com
    o resto dos dados (um único arquivo para copiar/fazer backup). Devolve None se nenhum arquivo foi enviado e
    levanta ValueError se o arquivo for inválido.
    """
    if not arquivo or not arquivo.filename:
        return None

    dados = arquivo.read(TAMANHO_MAXIMO_IMAGEM + 1)

    if not dados:
        return None

    if len(dados) > TAMANHO_MAXIMO_IMAGEM:
        raise ValueError("A imagem deve ter no máximo 2 MB.")

    tipo = _tipo_da_imagem(dados)

    if tipo is None:
        raise ValueError("Envie uma imagem PNG, JPG, GIF ou WEBP.")

    from models import imagem_model

    return f"db:{imagem_model.criar(tipo, dados)}"


def moeda_para_centavos(valor):
    # Vira texto, sem espaços nem R$
    texto = str(valor).strip().replace("R$", "").replace(" ", "")

    # Aceita formatos brasileiros, como:
    # 29,90
    # 1.299,90
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        # Decimal evita erro de arredondamento do float
        return int(
            (
                Decimal(texto) * 100
            ).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP
            )
        )

    # Valor que não vira número
    except InvalidOperation as erro:
        raise ValueError(
            "Valor monetário inválido"
        ) from erro


def formatar_moeda(centavos):
    # Centavos para reais
    valor = Decimal(int(centavos)) / 100

    # Formato brasileiro:
    # 1234 centavos → R$ 12,34
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

"""Decoradores utilizados para controle de acesso."""

from functools import wraps

from flask import (
    flash,
    redirect,
    session,
    url_for
)



# Regras de senha

SENHA_MIN = 8
SENHA_MAX = 32

# Mesma regra da tela (static/js/script.js e _macros.html)
SENHA_REGRAS_TEXTO = (
    "A senha deve ter de 8 a 32 caracteres, com pelo menos uma letra "
    "minúscula, uma maiúscula, um número e um símbolo especial "
    "(! @ # $ % & * etc.), sem espaços."
)


def validar_senha(senha):
    """Devolve None se a senha é válida, ou o texto do erro."""

    if not (SENHA_MIN <= len(senha) <= SENHA_MAX):
        return f"A senha deve ter entre {SENHA_MIN} e {SENHA_MAX} caracteres."

    if any(c.isspace() for c in senha):
        return "A senha não pode conter espaços."

    if not any(c in string.ascii_lowercase for c in senha):
        return "A senha precisa de pelo menos uma letra minúscula."

    if not any(c in string.ascii_uppercase for c in senha):
        return "A senha precisa de pelo menos uma letra maiúscula."

    if not any(c in string.digits for c in senha):
        return "A senha precisa de pelo menos um número."

    if not any(c in string.punctuation for c in senha):
        return "A senha precisa de pelo menos um símbolo especial (ex.: ! @ # $ %)."

    return None


def validar_nova_senha(senha, confirmacao):
    """Valida a senha e a confirmação. Devolve None ou o texto do erro."""

    erro = validar_senha(senha)

    if erro:
        return erro

    # Compara a senha em texto puro (antes do hash): o hash do Werkzeug
    # tem sal aleatório, então dois hashes da mesma senha nunca são iguais
    if not secrets.compare_digest(
        senha.encode("utf-8"),
        confirmacao.encode("utf-8")
    ):
        return "A confirmação de senha não confere com a senha digitada."

    return None


def gerar_senha_temporaria(tamanho=12):
    """Gera uma senha aleatória que já cumpre as regras de senha."""

    sorteio = secrets.SystemRandom()

    # Evita símbolos que confundem ao ditar a senha
    simbolos = "!@#$%&*?"

    senha = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(simbolos),
    ]

    todos = string.ascii_letters + string.digits + simbolos
    senha += [secrets.choice(todos) for _ in range(tamanho - len(senha))]

    sorteio.shuffle(senha)

    return "".join(senha)


def ip_cliente():
    """IP de quem fez a requisição.

    Rodando localmente não há proxy na frente do app, então o cabeçalho
    X-Forwarded-For não é confiável (qualquer um poderia forjá-lo para
    escapar do bloqueio de tentativas de login).
    """

    # Na Vercel o proxy deles preenche o X-Forwarded-For, então dá pra confiar
    if NA_VERCEL:
        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()

        if ip:
            return ip[:64]

    return (request.remote_addr or "desconhecido")[:64]


def login_required(funcao):
    """
    Permite o acesso somente a usuários autenticados.
    """

    @wraps(funcao)
    def verificar_login(*args, **kwargs):

        # Tem alguém logado?
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for(
                    "auth.login",
                    proxima="/"
                )
            )

        return funcao(*args, **kwargs)

    return verificar_login


def administrador_required(funcao):
    """
    Permite o acesso somente a administradores.
    """

    @wraps(funcao)
    def verificar_administrador(*args, **kwargs):

        # Tem alguém logado?
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Confere o cargo na sessão
        if session.get("cargo") != "administrador":

            flash(
                "Você não tem permissão para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("main.inicio")
            )

        return funcao(*args, **kwargs)

    return verificar_administrador

def cozinheiro_required(funcao):
    """
    Permite o acesso somente a cozinheiros.
    """

    @wraps(funcao)
    def verificar_cozinheiro(*args, **kwargs):

        # Tem alguém logado?
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Confere o cargo na sessão
        if session.get("cargo") != "cozinheiro":

            flash(
                "Você não tem permissão para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("main.inicio")
            )

        return funcao(*args, **kwargs)

    return verificar_cozinheiro

def cliente_required(funcao):
    """
    Permite o acesso somente a clientes.
    """

    @wraps(funcao)
    def verificar_cliente(*args, **kwargs):

        # Tem alguém logado?
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Confere o cargo na sessão
        if session.get("cargo") != "cliente":

            flash(
                "Você não tem permissão para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("main.inicio")
            )

        return funcao(*args, **kwargs)

    return verificar_cliente

def gestor_required(funcao):
    """
    Permite o acesso a administradores e cozinheiros.
    """

    @wraps(funcao)
    def verificar_gestor(*args, **kwargs):

        # Tem alguém logado?
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Confere o cargo na sessão
        if session.get("cargo") != "administrador" and session.get("cargo") != "cozinheiro":

            flash(
                "Você não tem permissão para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("main.inicio")
            )

        return funcao(*args, **kwargs)

    return verificar_gestor

def adm_cli_required(funcao):
    """
    Permite o acesso a administradores e cozinheiros.
    """

    @wraps(funcao)
    def verificar_end(*args, **kwargs):

        # Tem alguém logado?
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Confere o cargo na sessão
        if session.get("cargo") != "administrador" and session.get("cargo") != "cliente":

            flash(
                "Você não tem permissão para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("main.inicio")
            )

        return funcao(*args, **kwargs)

    return verificar_end