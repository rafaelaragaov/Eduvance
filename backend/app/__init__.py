"""Eduvance - API REST (Flask) + entrega do front-end compilado."""
import os

from flask import Flask, jsonify, send_from_directory

from .config import Config
from .db import dialeto, fechar_db, one
from .errors import registrar_handlers


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    app.teardown_appcontext(fechar_db)
    registrar_handlers(app)

    from .routes import (agenda, atividades, auth, avaliacoes, boletim, catalogo, comunicados, dashboard, eventos, frequencia,
                         notas, notificacoes, ocorrencias, preferencias, recomendacoes, usuarios, vestibular)

    for m in (auth, usuarios, catalogo, atividades, avaliacoes, boletim, frequencia, notas, vestibular, comunicados,
              ocorrencias, notificacoes, agenda, eventos, preferencias, recomendacoes, dashboard):
        app.register_blueprint(m.bp)

    @app.get("/api/health")
    def health():
        """Comprova a conexão aplicação <-> banco de dados (entrega 1 da Sprint 03)."""
        try:
            if dialeto() == "postgresql":
                tabelas = one("SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'")["n"]
                versao = one("SHOW server_version")["server_version"]
                banco, destino = "PostgreSQL", one("SELECT current_database() AS d")["d"]
            else:
                tabelas = one("SELECT COUNT(*) AS n FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")["n"]
                versao = one("SELECT sqlite_version() AS v")["v"]
                banco, destino = "SQLite", os.path.basename(app.config["DATABASE"])
            usuarios_ = one("SELECT COUNT(*) AS n FROM usuario")["n"]
        except Exception:  # banco ausente/sem schema
            return jsonify(status="erro", mensagem="Banco de dados indisponível. Execute: python -m app.init_db"), 503
        return jsonify(status="ok", banco=banco, versao=versao, arquivo=destino, tabelas=tabelas, usuarios=usuarios_)

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
