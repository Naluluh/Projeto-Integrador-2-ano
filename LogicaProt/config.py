"""Configurações centralizadas da aplicação."""

import os
from pathlib import Path


# Diretório principal do projeto.
BASE_DIR = Path(__file__).resolve().parent


class Config:
    # Chave utilizada pelo Flask para proteger os dados da sessão.
    # Em produção, deve ser definida através de uma variável de ambiente.
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "troque-esta-chave-em-producao"
    )

    # Caminho do banco SQLite do restaurante.
    DATABASE = os.environ.get(
        "DATABASE",
        str(BASE_DIR / "instance" / "restaurante.db")
    )

    # Impede que JavaScript acesse diretamente o cookie da sessão.
    SESSION_COOKIE_HTTPONLY = True

    # Ajuda a controlar o envio do cookie em requisições entre sites.
    SESSION_COOKIE_SAMESITE = "Lax"