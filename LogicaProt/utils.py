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