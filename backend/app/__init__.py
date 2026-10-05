"""Eduvance - API REST (Flask) + entrega do front-end compilado."""
import os

from flask import Flask, jsonify, send_from_directory

from .config import Config
from .db import fechar_db, one
from .errors import registrar_handlers


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    app.teardown_appcontext(fechar_db)
    registrar_handlers(app)

    from .routes import atividades, auth, catalogo, dashboard, notas, usuarios, vestibular

    for m in (auth, usuarios, catalogo, atividades, notas, vestibular, dashboard):
        app.register_blueprint(m.bp)

    @app.get("/api/health")
    def health():
        """Comprova a conexão aplicação <-> banco de dados (entrega 1 da Sprint 03)."""
        try:
            tabelas = one("SELECT COUNT(*) AS n FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")["n"]
            usuarios_ = one("SELECT COUNT(*) AS n FROM usuario")["n"]
            versao = one("SELECT sqlite_version() AS v")["v"]
        except Exception:  # banco ausente/sem schema
            return jsonify(status="erro", mensagem="Banco de dados indisponível. Execute: python -m app.init_db"), 503
        return jsonify(
            status="ok", banco="SQLite", versao=versao, arquivo=os.path.basename(app.config["DATABASE"]),
            tabelas=tabelas, usuarios=usuarios_,
        )

    # ---- Front-end (SPA) ----
    dist = app.config["FRONTEND_DIST"]

    @app.get("/", defaults={"caminho": ""})
    @app.get("/<path:caminho>")
    def spa(caminho):
        if caminho.startswith("api/"):
            return jsonify(erro="Rota não encontrada"), 404
        alvo = os.path.join(dist, caminho)
        if caminho and os.path.isfile(alvo):
            return send_from_directory(dist, caminho)
        if os.path.isfile(os.path.join(dist, "index.html")):
            return send_from_directory(dist, "index.html")
        return (
            "Front-end ainda não compilado. Rode: cd frontend && npm install && npm run build",
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    @app.after_request
    def cabecalhos_seguranca(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if resp.mimetype == "application/json":
            resp.headers["Cache-Control"] = "no-store"
        return resp

    return app
