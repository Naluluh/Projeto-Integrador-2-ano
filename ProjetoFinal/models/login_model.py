"""Controle de tentativas de login (proteção contra força bruta).

As contagens ficam no banco (e não na memória) para sobreviverem a
reinícios do servidor.

Os horários são guardados como segundos desde 1970 (inteiros), calculados
no Python: assim o mesmo SQL funciona igual em qualquer banco.
"""

import time

from flask import current_app

from database import get_db


def _agora():
    return int(time.time())


def segundos_de_bloqueio(chaves):
    """Maior tempo (em segundos) que ainda falta para alguma das chaves
    poder tentar de novo. Devolve 0 quando nenhuma está bloqueada."""

    db = get_db()
    agora = _agora()
    restante = 0

    for chave in chaves:
        linha = db.execute(
            "SELECT bloqueado_ate FROM login_tentativas WHERE chave = ?",
            (chave,)
        ).fetchone()

        if linha and linha["bloqueado_ate"] > agora:
            restante = max(restante, linha["bloqueado_ate"] - agora)

    return restante


def registrar_falha(chave):
    """Soma uma tentativa errada. Ao atingir o limite, bloqueia a chave.

    Devolve quantos segundos de bloqueio foram aplicados (0 se não houve).
    """

    limite = current_app.config["LOGIN_MAX_TENTATIVAS"]
    bloqueio = current_app.config["LOGIN_BLOQUEIO_SEGUNDOS"]
    janela = current_app.config["LOGIN_JANELA_SEGUNDOS"]

    db = get_db()
    agora = _agora()

    try:
        # Operação única no banco: duas tentativas simultâneas não se perdem.
        linha = db.execute(
            """
            INSERT INTO login_tentativas
                (chave, tentativas, atualizado_em, bloqueado_ate)
            VALUES (?, 1, ?, 0)
            ON CONFLICT (chave) DO UPDATE SET
                tentativas = CASE
                    WHEN login_tentativas.atualizado_em < ? THEN 1
                    ELSE login_tentativas.tentativas + 1
                END,
                atualizado_em = ?
            RETURNING tentativas
            """,
            (chave, agora, agora - janela, agora)
        ).fetchone()

        aplicado = 0

        if linha["tentativas"] >= limite:
            db.execute(
                """
                UPDATE login_tentativas
                SET tentativas = 0, bloqueado_ate = ?
                WHERE chave = ?
                """,
                (agora + bloqueio, chave)
            )
            aplicado = bloqueio

        # Faxina: remove registros antigos que não bloqueiam mais ninguém.
        db.execute(
            """
            DELETE FROM login_tentativas
            WHERE atualizado_em < ? AND bloqueado_ate < ?
            """,
            (agora - janela * 4, agora)
        )

        db.commit()
        return aplicado

    except Exception:
        db.rollback()
        raise


def limpar(chave):
    """Zera a contagem (usado quando a pessoa acerta a senha)."""

    db = get_db()
    db.execute("DELETE FROM login_tentativas WHERE chave = ?", (chave,))
    db.commit()
