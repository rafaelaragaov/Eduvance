"""Inicia o Eduvance localmente: API + front-end em http://localhost:5000"""
import os
import sys

from app import create_app
from app.config import Config

if __name__ == "__main__":
    if not os.path.isfile(Config.DATABASE):
        print(f"✖ Banco não encontrado em {Config.DATABASE}.\n  Rode primeiro: python -m app.init_db", file=sys.stderr)
        sys.exit(1)
    porta = int(os.environ.get("PORT", "5000"))
    print(f"✔ Eduvance em http://localhost:{porta}  (banco: {Config.DATABASE})")
    create_app().run(host="127.0.0.1", port=porta, debug=os.environ.get("EDUVANCE_DEBUG") == "1")
