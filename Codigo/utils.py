"""Funções pequenas compartilhadas entre Controllers e Views."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


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
    Permite o acesso somente a administradores.
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
    Permite o acesso somente a administradores.
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