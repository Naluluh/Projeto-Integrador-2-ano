"""Configurações centralizadas da aplicação."""

import os
from pathlib import Path


# Diretório principal do projeto.
BASE_DIR = Path(__file__).resolve().parent


class Config:
    # Chave utilizada pelo Flask para proteger os dados da sessão.
    # Em produção, deve ser definida através de uma variável de ambiente.
    SECRET_KEY = os.environ.get(
        "bl0ck3d_f0r_th3_0th3rs", "secret_key_67"
    )

    # URL PostgreSQL hospedada no Neon.
    DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE")

    # Impede que JavaScript acesse diretamente o cookie da sessão.
    SESSION_COOKIE_HTTPONLY = True

    # Ajuda a controlar o envio do cookie em requisições entre sites.
    SESSION_COOKIE_SAMESITE = "Lax"