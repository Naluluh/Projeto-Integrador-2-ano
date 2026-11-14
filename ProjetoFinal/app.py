"""Application Factory do Sabor e Clic."""

import time

from flask import Flask, flash, redirect, render_template, request, session, url_for

from config import Config
from database import init_app as init_database
from utils import formatar_moeda, formatar_datahora, url_foto
from blueprints_register import registrar_blueprints


def create_app(test_config=None):
    # Cria a aplicação Flask usando a pasta instance para arquivos específicos da aplicação.
    app = Flask(__name__, instance_relative_config=True)

    # Carrega as configurações centralizadas.
    app.config.from_object(Config)

    # Permite substituir configurações durante os testes.
    if test_config:
        app.config.update(test_config)

    # Importa os Blueprints responsáveis pelas diferentes partes do sistema.
    registrar_blueprints(app)
    
    # Cria o filtro Jinja |moeda para exibir valores em reais.
    app.jinja_env.filters["moeda"] = formatar_moeda

    # Cria o filtro Jinja |datahora para exibir datas no horário de Brasília.
    app.jinja_env.filters["datahora"] = formatar_datahora

    # Função Jinja foto_src(...) para exibir imagens (arquivos da pasta
    # static ou fotos enviadas pelos usuários, guardadas no banco).
    app.jinja_env.globals["foto_src"] = url_foto

    # Middleware executado antes de cada requisição.
    @app.before_request
    def exigir_login():
        # Rotas que podem ser acessadas sem estar autenticado.
        rotas_publicas = {
            "auth.login",
            "auth.cadastro",
            "auth.esqueci_senha",
            "static",
        }

        if request.endpoint in rotas_publicas:
            return None

        # Só guarda a página de destino quando ela pode ser aberta por GET.
        proxima = request.path if request.method == "GET" else None

        # Sem sessão: redireciona para o login.
        if "usuario_id" not in session:
            return redirect(url_for("auth.login", proxima=proxima))

        # Timeout de inatividade: sem nenhuma requisição por 30 minutos,
        # a sessão é encerrada. A checagem é feita aqui, no servidor, e não
        # só no navegador, para não depender do JavaScript.
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

        # Pessoa ativa: renova o prazo.
        session["ultima_atividade"] = agora

        # Entrou com senha temporária: só pode trocar a senha (ou sair).
        if session.get("trocar_senha") and request.endpoint not in {
            "auth.alterar_senha",
            "auth.logout",
            "main.sessao_ping",
        }:
            return redirect(url_for("auth.alterar_senha"))

        return None

    # Páginas com dados da conta não devem ficar no cache do navegador
    # (o botão "voltar" não mostra a página depois de sair).
    @app.after_request
    def nao_guardar_cache(resposta):
        if resposta.mimetype == "text/html":
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    # Disponibiliza o prazo de inatividade para o JavaScript (base.html).
    @app.context_processor
    def dados_da_sessao():
        return {"inatividade_segundos": app.config["INATIVIDADE_SEGUNDOS"]}

    # Página personalizada para erros 404.
    @app.errorhandler(404)
    def pagina_nao_encontrada(_erro):
        return render_template("404.html"), 404

    # Registra o fechamento da conexão com o banco ao fim de cada requisição.
    # As tabelas são criadas sob demanda (ver database.get_db), e não mais
    # ao importar o app, para não atrasar nem derrubar o carregamento.
    init_database(app)

    return app


# Cria a aplicação.
app = create_app()


# Executa o servidor apenas quando este arquivo for executado diretamente.
if __name__ == "__main__":
    app.run(debug=True)