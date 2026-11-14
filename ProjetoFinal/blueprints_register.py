# Registra no app todos os grupos de rotas

# Liga cada grupo de rotas ao app
def registrar_blueprints(app):
        from controllers.auth_controller import auth_bp
        from controllers.usuario_controller import usuario_bp
        from controllers.ingrediente_controller import ingrediente_bp
        from controllers.main_controller import main_bp
        from controllers.pedido_controller import pedido_bp
        from controllers.prato_controller import prato_bp
        from controllers.endereco_controller import endereco_bp
        from controllers.categorias_controller import categorias_bp
        from controllers.chefs_controller import chefs_bp
        from controllers.perfil_chef_controller import perfil_bp
        from controllers.reserva_controller import reservas_bp
        
        # Registra os Blueprints na aplicação.
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(usuario_bp)
        app.register_blueprint(prato_bp)
        app.register_blueprint(ingrediente_bp)
        app.register_blueprint(pedido_bp)
        app.register_blueprint(endereco_bp)
        app.register_blueprint(categorias_bp)
        app.register_blueprint(chefs_bp)
        app.register_blueprint(perfil_bp)
        app.register_blueprint(reservas_bp)