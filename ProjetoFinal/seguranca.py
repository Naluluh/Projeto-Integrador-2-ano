# Proteção CSRF: todo POST precisa trazer o token da sessão
import hmac
import secrets
from urllib.parse import urlparse

from flask import flash, jsonify, redirect, request, session, url_for


# Devolve o token da sessão (cria na primeira vez)
def gerar_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)

    return session["csrf"]


# Só volta para a página anterior se ela for deste mesmo site
def _voltar_para():
    anterior = request.referrer

    if anterior and urlparse(anterior).netloc == request.host:
        return anterior

    return url_for("auth.login")


# Liga a checagem do token em toda requisição que altera dados
def iniciar_csrf(app):
    app.jinja_env.globals["csrf_token"] = gerar_token

    # Recusa o POST que não trouxer o token certo
    @app.before_request
    def conferir_csrf():
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None

        enviado = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        esperado = session.get("csrf", "")

        if esperado and enviado and hmac.compare_digest(enviado, esperado):
            return None

        # Token faltando ou errado: não executa a ação
        if "X-CSRF-Token" in request.headers or request.is_json:
            return jsonify({"mensagem": "Sessão inválida. Recarregue a página."}), 400

        flash("A página expirou. Tente de novo.", "erro")

        return redirect(_voltar_para())
