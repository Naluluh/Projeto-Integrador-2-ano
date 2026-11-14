"""Application Factory do Sabor e Clic."""

from flask import Flask, redirect, render_template, request, session, url_for

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
        # Rotas que podem ser acessadas sem funcionário autenticado.
        rotas_publicas = {
            "auth.login",
            "auth.cadastro",
            "static",
        }

        # Se a rota não for pública e não houver funcionário na sessão,
        # o usuário é redirecionado para o login.
        if (
            request.endpoint not in rotas_publicas
            and "usuario_id" not in session
        ):
            return redirect(
                url_for(
                    "auth.login",
                    proxima=request.path
                )
            )

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