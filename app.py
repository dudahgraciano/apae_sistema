from flask import Flask, jsonify, render_template, request

import extensions
from config import Config
from routes.atividades import atividades_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.midias import midias_bp
from routes.registros import registros_bp
from routes.usuarios import usuarios_bp
from utils import auditoria

# Só aceita scripts, estilos, imagens e vídeos do próprio sistema.
POLITICA_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "media-src 'self'; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


def criar_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY não definida. Confira o arquivo .env.")

    extensions.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(atividades_bp)
    app.register_blueprint(midias_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(registros_bp)

    auditoria.init_app(app)

    @app.after_request
    def cabecalhos_de_seguranca(resposta):
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "same-origin"
        resposta.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # A CSP fica desligada no modo de desenvolvimento, porque a página de
        # erros do Flask (debugger) usa scripts próprios que ela bloquearia.
        if not app.debug:
            resposta.headers["Content-Security-Policy"] = POLITICA_CSP
        # Páginas internas não devem ficar no cache (ex.: botão "Voltar" após sair)
        if resposta.mimetype == "text/html":
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    @app.errorhandler(403)
    def erro_403(erro):
        return render_template("erros/erro.html", codigo=403,
                               titulo="Acesso não permitido",
                               mensagem="Você não tem permissão para ver esta página."), 403

    @app.errorhandler(404)
    def erro_404(erro):
        return render_template("erros/erro.html", codigo=404,
                               titulo="Página não encontrada",
                               mensagem="O endereço que você tentou abrir não existe."), 404

    @app.errorhandler(413)
    def erro_413(erro):
        if request.path.endswith("/midias"):
            return jsonify(erro="O envio ultrapassou o limite de 512 MB. "
                                "Envie menos arquivos de cada vez."), 413
        return render_template("erros/erro.html", codigo=413,
                               titulo="Arquivo grande demais",
                               mensagem="O envio ultrapassou o limite permitido."), 413

    @app.errorhandler(429)
    def erro_429(erro):
        return render_template("erros/erro.html", codigo=429,
                               titulo="Muitas tentativas",
                               mensagem="Aguarde um minuto e tente novamente."), 429

    return app


app = criar_app()

if __name__ == "__main__":
    app.run(debug=False)