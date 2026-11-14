"""Configurações centralizadas da aplicação."""

import os
import secrets
from pathlib import Path


# Pasta do projeto
BASE_DIR = Path(__file__).resolve().parent

# Rodando na Vercel (lá o disco é somente leitura)
NA_VERCEL = bool(os.environ.get("VERCEL"))

# Pasta instance: banco e chave locais, fora do código
INSTANCE_DIR = BASE_DIR / "instance"

try:
    INSTANCE_DIR.mkdir(exist_ok=True)
except OSError:
    pass


def _url_do_banco():
    # Na Vercel vem do Neon (DATABASE_URL). Local, usa SQLite se não definir.
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")

    if not url:
        if NA_VERCEL:
            raise RuntimeError(
                "Defina DATABASE_URL (string de conexão do Neon) nas variáveis da Vercel."
            )

        return f"sqlite:///{(INSTANCE_DIR / 'sabor_e_clic.db').as_posix()}"

    # O Neon entrega postgresql://, o SQLAlchemy precisa do driver psycopg
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


def _chave_secreta():
    # 1) Variável de ambiente SECRET_KEY, se existir
    chave = os.environ.get("SECRET_KEY")

    if chave:
        return chave

    # Na Vercel não dá pra guardar arquivo, e cada instância teria uma chave diferente
    if NA_VERCEL:
        raise RuntimeError("Defina SECRET_KEY nas variáveis da Vercel.")

    # 2) Senão, gera uma chave na primeira execução e guarda em instance/secret_key
    #    (assim as sessões continuam válidas ao reiniciar)
    arquivo = INSTANCE_DIR / "secret_key"

    if arquivo.exists():
        return arquivo.read_text(encoding="utf-8").strip()

    chave = secrets.token_hex(32)
    arquivo.write_text(chave, encoding="utf-8")

    return chave


class Config:
    DATABASE_URL = _url_do_banco()

    # Chave da sessão do Flask
    SECRET_KEY = _chave_secreta()

    # JavaScript não consegue ler o cookie da sessão
    SESSION_COOKIE_HTTPONLY = True

    # Limita o envio do cookie entre sites
    SESSION_COOKIE_SAMESITE = "Lax"

    # Na Vercel é https; em localhost é http://, então não pode exigir
    SESSION_COOKIE_SECURE = NA_VERCEL

    # Sessão acaba após 30 minutos sem atividade
    INATIVIDADE_SEGUNDOS = 30 * 60

    # Anti força bruta no login: 15 erros bloqueiam a pessoa (e o IP) por 5 minutos
    LOGIN_MAX_TENTATIVAS = 15
    LOGIN_BLOQUEIO_SEGUNDOS = 5 * 60

    # Os erros só contam dentro dessa janela
    LOGIN_JANELA_SEGUNDOS = 15 * 60


def usa_postgres():
    return Config.DATABASE_URL.startswith("postgresql")
