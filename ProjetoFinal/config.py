"""Configurações centralizadas da aplicação."""

import hashlib
import os
from pathlib import Path


# Diretório principal do projeto.
BASE_DIR = Path(__file__).resolve().parent


def _url_do_banco():
    # A integração Neon <-> Vercel cria DATABASE_URL (conexão com pooler).
    # POSTGRES_URL e DATABASE são aceitas como alternativas.
    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("DATABASE")
    )


def _chave_secreta(url_banco):
    # 1) Variável de ambiente SECRET_KEY (recomendado definir na Vercel).
    chave = os.environ.get("SECRET_KEY")

    # 2) Nome antigo usado nas versões anteriores do projeto.
    chave = chave or os.environ.get("bl0ck3d_f0r_th3_0th3rs")

    if chave:
        return chave

    # 3) Sem variável definida: deriva uma chave estável (igual em todas as
    #    instâncias da Vercel) a partir da URL do banco, que é secreta e não
    #    está no repositório. Nunca use um valor fixo escrito no código,
    #    pois o repositório é público e qualquer pessoa poderia forjar sessões.
    if url_banco:
        return hashlib.sha256(
            b"sabor-e-clic|" + url_banco.encode("utf-8")
        ).hexdigest()

    # Somente para desenvolvimento local sem banco configurado.
    return "chave-apenas-para-desenvolvimento-local"


class Config:
    # URL PostgreSQL hospedada no Neon.
    DATABASE_URL = _url_do_banco()

    # Chave utilizada pelo Flask para proteger os dados da sessão.
    SECRET_KEY = _chave_secreta(DATABASE_URL)

    # Impede que JavaScript acesse diretamente o cookie da sessão.
    SESSION_COOKIE_HTTPONLY = True

    # Ajuda a controlar o envio do cookie em requisições entre sites.
    SESSION_COOKIE_SAMESITE = "Lax"

    # Na Vercel o site é servido por HTTPS: o cookie só trafega criptografado.
    SESSION_COOKIE_SECURE = bool(os.environ.get("VERCEL"))

    # Encerra a sessão após 30 minutos sem nenhuma atividade.
    INATIVIDADE_SEGUNDOS = 30 * 60

    # Proteção contra força bruta no login: após 15 tentativas erradas,
    # a pessoa (e o IP) ficam 5 minutos sem poder tentar de novo.
    LOGIN_MAX_TENTATIVAS = 15
    LOGIN_BLOQUEIO_SEGUNDOS = 5 * 60

    # Tentativas erradas só contam dentro desta janela de tempo.
    LOGIN_JANELA_SEGUNDOS = 15 * 60
