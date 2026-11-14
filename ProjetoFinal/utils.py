"""Funções pequenas compartilhadas entre Controllers e Views."""

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import url_for

# Brasília (UTC-3). O Brasil não adota mais horário de verão.
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# Tamanho máximo das imagens enviadas (a Vercel limita o corpo da requisição).
TAMANHO_MAXIMO_IMAGEM = 2 * 1024 * 1024


def formatar_datahora(valor):
    """Converte o texto de data/hora do banco para dd/mm/aaaa hh:mm (Brasília)."""
    if not valor:
        return ""

    texto = str(valor).strip()

    # O PostgreSQL pode devolver o fuso como "+00"; o Python precisa de "+00:00".
    if re.search(r"[+-]\d{2}$", texto):
        texto += ":00"

    try:
        momento = datetime.fromisoformat(texto)
    except ValueError:
        return str(valor)

    # Datas sem fuso (formato antigo do SQLite) já estavam em UTC.
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
    # Identifica o formato pelo conteúdo do arquivo, e não pelo nome.
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

    A Vercel não permite gravar arquivos em disco, então as fotos enviadas
    ficam na tabela "imagens". Devolve None se nenhum arquivo foi enviado e
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
    # Converte o valor recebido para texto e remove espaços e o símbolo R$.
    texto = str(valor).strip().replace("R$", "").replace(" ", "")

    # Aceita formatos brasileiros, como:
    # 29,90
    # 1.299,90
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        # Converte o valor para Decimal para evitar problemas de
        # precisão comuns em números de ponto flutuante.
        return int(
            (
                Decimal(texto) * 100
            ).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP
            )
        )

    # Caso o valor não possa ser convertido para número.
    except InvalidOperation as erro:
        raise ValueError(
            "Valor monetário inválido"
        ) from erro


def formatar_moeda(centavos):
    # Converte os centavos para reais.
    valor = Decimal(int(centavos)) / 100

    # Formata no padrão brasileiro:
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


def login_required(funcao):
    """
    Permite o acesso somente a usuários autenticados.
    """

    @wraps(funcao)
    def verificar_login(*args, **kwargs):

        # Verifica se existe um funcionário autenticado.
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

        # Primeiro verifica se existe alguém logado.
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Depois verifica o cargo armazenado na sessão.
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

        # Primeiro verifica se existe alguém logado.
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Depois verifica o cargo armazenado na sessão.
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

        # Primeiro verifica se existe alguém logado.
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Depois verifica o cargo armazenado na sessão.
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

        # Primeiro verifica se existe alguém logado.
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Depois verifica o cargo armazenado na sessão.
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

        # Primeiro verifica se existe alguém logado.
        if "usuario_id" not in session:

            flash(
                "Faça login para acessar esta página.",
                "erro"
            )

            return redirect(
                url_for("auth.login")
            )

        # Depois verifica o cargo armazenado na sessão.
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