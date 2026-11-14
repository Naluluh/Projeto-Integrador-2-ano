# Cria o app Flask e liga tudo (banco, filtros, rotas e segurança)
"""Application Factory do Sabor e Clic."""

import time

from flask import Flask, flash, redirect, render_template, request, session, url_for

from config import Config
from database import init_app as init_database
from utils import formatar_moeda, formatar_datahora, formatar_dataiso, url_foto
from blueprints_register import registrar_blueprints
from seguranca import iniciar_csrf


# Monta e devolve o app Flask
def create_app(test_config=None):
    # Arquivos estáticos ficam em public/static (a Vercel serve essa pasta direto)
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="public/static",
    )

    app.config.from_object(Config)

    # Para trocar configurações nos testes
    if test_config:
        app.config.update(test_config)

    # Importa os blueprints
    registrar_blueprints(app)

    # Proteção CSRF (tem que vir antes dos outros before_request)
    iniciar_csrf(app)
    
    # Filtro |moeda (valores em reais)
    app.jinja_env.filters["moeda"] = formatar_moeda

    # Filtro |datahora (horário de Brasília)
    app.jinja_env.filters["datahora"] = formatar_datahora
    app.jinja_env.filters["dataiso"] = formatar_dataiso

    # Função foto_src(...) para mostrar imagens (da pasta static ou do banco)
    app.jinja_env.globals["foto_src"] = url_foto

    # Roda antes de toda requisição
    @app.before_request
    def exigir_login():
        # Rotas liberadas sem login
        rotas_publicas = {
            "auth.login",
            "auth.cadastro",
            "auth.esqueci_senha",
            "static",
        }

        if request.endpoint in rotas_publicas:
            return None

        # Só guarda a página de destino se abrir por GET
        proxima = request.path if request.method == "GET" else None

        # Sem login: vai para a tela de entrada
        if "usuario_id" not in session:
            return redirect(url_for("auth.login", proxima=proxima))

        # Sem requisição por 30 minutos, a sessão acaba.
        # A checagem é no servidor para não depender do JavaScript.
        agora = int(time.time())
        ultima = session.get("ultima_atividade")

        if (
            ultima is None
            or agora - ultima > app.config["INATIVIDADE_SEGUNDOS"]
        ):
            session.clear()

            flash(
                "Sua sessão foi encerrada após 30 minutos de inatividade. "
                "Faça login novamente.",
                "aviso"
            )

            return redirect(url_for("auth.login", proxima=proxima))

        # Ainda ativo: renova o prazo
        session["ultima_atividade"] = agora

        # Senha temporária: só pode trocar a senha (ou sair)
        if session.get("trocar_senha") and request.endpoint not in {
            "auth.alterar_senha",
            "auth.logout",
            "main.sessao_ping",
        }:
            return redirect(url_for("auth.alterar_senha"))

        return None

    # Sem cache nas páginas da conta (o botão voltar não mostra a página depois do logout)
    @app.after_request
    def nao_guardar_cache(resposta):
        if resposta.mimetype == "text/html":
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    # Passa o prazo de inatividade para o JavaScript (base.html)
    @app.context_processor
    def dados_da_sessao():
        return {"inatividade_segundos": app.config["INATIVIDADE_SEGUNDOS"]}

    # Página de erro 404
    @app.errorhandler(404)
    def pagina_nao_encontrada(_erro):
        return render_template("404.html"), 404

    # Conecta no banco (cria as tabelas se faltar) e fecha a conexão ao fim da requisição
    init_database(app)

    return app


app = create_app()


# Só inicia o servidor se rodar este arquivo direto
if __name__ == "__main__":
    app.run(debug=True)