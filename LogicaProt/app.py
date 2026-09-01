"""Application Factory do Restaurante Online."""

from flask import Flask, redirect, render_template, request, session, url_for

from config import Config
from database import init_app as init_database
from utils import formatar_moeda


def create_app(test_config=None):
    # Cria a aplicação Flask usando a pasta instance para arquivos específicos da aplicação.
    app = Flask(__name__, instance_relative_config=True)

    # Carrega as configurações centralizadas.
    app.config.from_object(Config)

    # Permite substituir configurações durante os testes.
    if test_config:
        app.config.update(test_config)

    # Importa os Blueprints responsáveis pelas diferentes partes do sistema.
    from controllers.auth_controller import auth_bp
    from controllers.funcionario_controller import funcionario_bp
    from controllers.ingrediente_controller import ingrediente_bp
    from controllers.main_controller import main_bp
    from controllers.pedido_controller import pedido_bp
    from controllers.prato_controller import prato_bp

    # Registra os Blueprints na aplicação.
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(funcionario_bp)
    app.register_blueprint(prato_bp)
    app.register_blueprint(ingrediente_bp)
    app.register_blueprint(pedido_bp)

    # Cria o filtro Jinja |moeda para exibir valores em reais.
    app.jinja_env.filters["moeda"] = formatar_moeda

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
            and "funcionario_id" not in session
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

    # Inicializa o banco de dados e cria as tabelas necessárias.
    init_database(app)

    return app


# Cria a aplicação.
app = create_app()


# Executa o servidor apenas quando este arquivo for executado diretamente.
if __name__ == "__main__":
    app.run(debug=True)