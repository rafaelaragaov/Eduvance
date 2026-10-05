"""Erros de API e validação simples de corpo JSON."""
import re
import sqlite3
from datetime import datetime

from flask import jsonify


class ApiError(Exception):
    def __init__(self, status: int, mensagem: str, detalhes=None):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem
        self.detalhes = detalhes


def nao_encontrado(o_que="Recurso") -> ApiError:
    return ApiError(404, f"{o_que} não encontrado")


def proibido(msg="Você não tem permissão para esta ação") -> ApiError:
    return ApiError(403, msg)


def registrar_handlers(app):
    @app.errorhandler(ApiError)
    def _api(e: ApiError):
        corpo = {"erro": e.mensagem}
        if e.detalhes:
            corpo["detalhes"] = e.detalhes
        return jsonify(corpo), e.status

    @app.errorhandler(sqlite3.IntegrityError)
    def _integridade(e: sqlite3.IntegrityError):
        msg = str(e)
        if "usuario.email" in msg:
            return jsonify(erro="Já existe um usuário com este e-mail"), 409
        if "aluno.matricula" in msg:
            return jsonify(erro="Já existe um aluno com esta matrícula"), 409
        if "máximo 2 responsáveis" in msg:
            return jsonify(erro="Um aluno pode ter no máximo 2 responsáveis vinculados"), 400
        if "FOREIGN KEY" in msg:
            return jsonify(erro="Operação inválida: registro relacionado inexistente ou em uso"), 409
        if "UNIQUE" in msg:
            return jsonify(erro="Registro duplicado"), 409
        return jsonify(erro="Dados inválidos para o banco de dados"), 400

    @app.errorhandler(404)
    def _404(_e):
        return jsonify(erro="Rota não encontrada"), 404

    @app.errorhandler(405)
    def _405(_e):
        return jsonify(erro="Método não permitido"), 405

    @app.errorhandler(Exception)
    def _500(e):
        app.logger.exception(e)
        return jsonify(erro="Erro interno do servidor"), 500


# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Corpo:
    """Validador minimalista: acumula erros por campo e os levanta de uma vez em .validar()."""

    def __init__(self, dados):
        if not isinstance(dados, dict):
            raise ApiError(400, "Corpo da requisição deve ser um objeto JSON")
        self.d = dados
        self.erros: list[dict] = []

    def _erro(self, campo, msg):
        self.erros.append({"campo": campo, "mensagem": msg})

    def tem(self, campo) -> bool:
        return campo in self.d

    def texto(self, campo, rotulo=None, minimo=0, maximo=255, obrigatorio=True, minusculo=False, nulavel=False):
        rotulo = rotulo or campo
        v = self.d.get(campo)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            if obrigatorio:
                self._erro(campo, f"{rotulo} é obrigatório")
            return None
        if not isinstance(v, str):
            self._erro(campo, f"{rotulo} deve ser texto")
            return None
        v = v.strip()
        if len(v) < minimo:
            self._erro(campo, f"{rotulo} deve ter ao menos {minimo} caracteres")
        if len(v) > maximo:
            self._erro(campo, f"{rotulo} deve ter no máximo {maximo} caracteres")
        return v.lower() if minusculo else v

    def email(self, campo="email"):
        v = self.texto(campo, "E-mail", maximo=160, minusculo=True)
        if v and not EMAIL_RE.match(v):
            self._erro(campo, "E-mail inválido")
        return v

    def inteiro(self, campo, rotulo=None, obrigatorio=True, minimo=1):
        rotulo = rotulo or campo
        v = self.d.get(campo)
        if v is None or v == "":
            if obrigatorio:
                self._erro(campo, f"{rotulo} é obrigatório")
            return None
        if isinstance(v, bool) or not isinstance(v, (int, str)) or (isinstance(v, str) and not v.lstrip("-").isdigit()):
            self._erro(campo, f"{rotulo} deve ser um número inteiro")
            return None
        v = int(v)
        if v < minimo:
            self._erro(campo, f"{rotulo} inválido")
        return v

    def numero(self, campo, rotulo=None, minimo=0.0, maximo=10.0, obrigatorio=True):
        rotulo = rotulo or campo
        v = self.d.get(campo)
        if v is None or v == "":
            if obrigatorio:
                self._erro(campo, f"{rotulo} é obrigatório")
            return None
        try:
            if isinstance(v, bool):
                raise ValueError
            n = float(v)
        except (TypeError, ValueError):
            self._erro(campo, f"{rotulo} deve ser numérico")
            return None
        if not (minimo <= n <= maximo):
            self._erro(campo, f"{rotulo} deve estar entre {minimo:g} e {maximo:g}")
        return n

    def data(self, campo, rotulo=None, obrigatorio=True):
        rotulo = rotulo or campo
        v = self.d.get(campo)
        if v in (None, ""):
            if obrigatorio:
                self._erro(campo, f"{rotulo} é obrigatória")
            return None
        if not isinstance(v, str) or not DATA_RE.match(v):
            self._erro(campo, f"{rotulo} inválida (use AAAA-MM-DD)")
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            self._erro(campo, f"{rotulo} inválida")
            return None
        return v

    def data_hora(self, campo, rotulo=None) -> str | None:
        """Aceita 'YYYY-MM-DDTHH:MM[:SS]' e devolve 'YYYY-MM-DDTHH:MM:SS' (horário local)."""
        rotulo = rotulo or campo
        v = self.d.get(campo)
        if not isinstance(v, str) or not v.strip():
            self._erro(campo, f"{rotulo} é obrigatório")
            return None
        v = v.strip().replace(" ", "T")
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(v[:19] if fmt.endswith("%S") else v, fmt)
                if fmt == "%Y-%m-%d":
                    dt = dt.replace(hour=23, minute=59)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue
        self._erro(campo, f"{rotulo} inválido")
        return None

    def validar(self):
        if self.erros:
            raise ApiError(400, "Dados inválidos", self.erros)
