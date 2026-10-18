"""Testes do serviço de recomendação (Sprint 06) e da sua integração com Notas, Frequência e Agenda.

O serviço FastAPI é simulado por um servidor HTTP local, para provar o contrato (JSON enviado e recebido), a
degradação elegante (fallback para o motor embutido) e a persistência em `recomendacao_ia`.
"""
import json
import socket
import threading
import unittest
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

from test_api import Base

ANO = date.today().year
LUCAS, ANA = f"{ANO}0001", f"{ANO}0004"


class ServicoFalso(BaseHTTPRequestHandler):
    recebidos: list = []
    resposta: dict = {}

    def do_POST(self):
        corpo = self.rfile.read(int(self.headers["Content-Length"]))
        type(self).recebidos.append((self.path, json.loads(corpo)))
        saida = json.dumps(type(self).resposta).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(saida)))
        self.end_headers()
        self.wfile.write(saida)

    def log_message(self, *a):  # silencia
        pass


class Rec(Base):
    def rec(self, h, **q):
        qs = "&".join(f"{k}={v}" for k, v in q.items())
        return self.c.get(f"/api/recomendacoes?{qs}", headers=h)

    def linhas(self, id_aluno):
        return self.sql("SELECT tipo, prioridade, titulo, origem FROM recomendacao_ia WHERE id_aluno = ? ORDER BY score DESC", (id_aluno,))

    def id_de(self, h, nome):
        for a in self.c.get("/api/usuarios?perfil=ALUNO", headers=self.admin()).get_json():
            if a["nome"] == nome:
                return a["id"]
        self.fail(nome)


class TestRecomendacoes(Rec):
    def test_aluno_recebe_recomendacoes_com_contrato_completo(self):
        h = self.login(LUCAS)
        r = self.rec(h)
        self.assertEqual(r.status_code, 200, r.get_json())
        j = r.get_json()
        self.assertEqual(j["origem"], "motor")
        self.assertTrue(j["itens"], "o aluno do seed tem provas e atividades próximas")
        self.assertLessEqual(len(j["itens"]), 6)
        for i in j["itens"]:
            self.assertTrue({"tipo", "prioridade", "score", "titulo", "mensagem", "motivo", "link"} <= set(i))
            self.assertIn(i["prioridade"], ("ALTA", "MEDIA", "BAIXA"))
        scores = [i["score"] for i in j["itens"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertIn(j["resumo"]["nivel"], ("TRANQUILO", "CUIDADO", "ATENCAO"))

    def test_cruza_agenda_com_notas_no_texto_da_prova(self):
        j = self.rec(self.login(LUCAS)).get_json()
        provas = [i for i in j["itens"] if i["tipo"] == "PROVA"]
        self.assertTrue(provas, "há prova nos próximos 7 dias no seed")
        com_media = [p for p in provas if p["motivo"].get("media") is not None]
        self.assertTrue(com_media)
        self.assertIn("média atual", com_media[0]["mensagem"])

    def test_resultado_e_persistido_sem_duplicar(self):
        h = self.login(LUCAS)
        uid = self.c.get("/api/auth/me", headers=h).get_json()["usuario"]["id"]
        j1 = self.rec(h).get_json()
        j2 = self.rec(h).get_json()
        linhas = self.linhas(uid)
        self.assertEqual(len(linhas), len(j1["itens"]))
        self.assertEqual(len(j1["itens"]), len(j2["itens"]))
        self.assertEqual([l[2] for l in linhas], [i["titulo"] for i in j1["itens"]])

    def test_reforco_aparece_apos_nota_baixa(self):
        """Integração Notas -> Recomendação: lançar uma nota baixa passa a gerar reforço na disciplina."""
        prof = self.login("ricardo@eduvance.com")
        td = next(t for t in self.c.get("/api/catalogo/turma-disciplinas", headers=prof).get_json()
                  if t["turma"] == "8º Ano B" and t["disciplina"] == "Matemática")
        av = self.c.post("/api/avaliacoes", headers=prof, json={
            "titulo": "Prova de reforço (teste)", "tipo": "PROVA", "bimestre": 2, "peso": 5, "dataAvaliacao": _dia_passado(), "idTurmaDisciplina": td["id"]})
        self.assertEqual(av.status_code, 201, av.get_json())
        h = self.login(LUCAS)
        lucas = self.c.get("/api/auth/me", headers=h).get_json()["usuario"]["id"]
        antes = self.rec(h).get_json()["itens"]
        self.assertFalse(any(i["tipo"] == "REFORCO" and i["disciplina"] == "Matemática" and i["prioridade"] == "ALTA" for i in antes))
        r = self.c.put(f"/api/notas/avaliacao/{av.get_json()['id']}", headers=prof, json={"notas": [{"idAluno": lucas, "valor": 1.0}]})
        self.assertIn(r.status_code, (200, 201), r.get_json())
        j = self.rec(h).get_json()
        self.assertTrue(any(i["tipo"] == "REFORCO" and i["disciplina"] == "Matemática" and i["prioridade"] == "ALTA" for i in j["itens"]), j["itens"])


class TestPermissoes(Rec):
    def test_exige_autenticacao(self):
        self.assertEqual(self.c.get("/api/recomendacoes").status_code, 401)

    def test_aluno_nao_ve_de_outro_aluno(self):
        h = self.login(LUCAS)
        outro = self.c.get("/api/auth/me", headers=self.login(ANA)).get_json()["usuario"]["id"]
        self.assertEqual(self.rec(h, idAluno=outro).status_code, 403)

    def test_responsavel_so_ve_dos_filhos(self):
        h = self.login("maria@eduvance.com")
        filhos = self.c.get("/api/dashboard", headers=h).get_json()["alunos"]
        self.assertEqual(self.rec(h, idAluno=filhos[0]["id"]).status_code, 200)
        nao_filho = self.c.get("/api/auth/me", headers=self.login(LUCAS)).get_json()["usuario"]["id"]
        if nao_filho not in [f["id"] for f in filhos]:
            self.assertEqual(self.rec(h, idAluno=nao_filho).status_code, 403)
        if len(filhos) > 1:
            self.assertEqual(self.rec(h).status_code, 400, "vários filhos: precisa informar o aluno")

    def test_professor_so_ve_alunos_das_suas_turmas_e_coordenacao_ve_todos(self):
        lucas = self.c.get("/api/auth/me", headers=self.login(LUCAS)).get_json()["usuario"]["id"]
        self.assertEqual(self.rec(self.login("ricardo@eduvance.com"), idAluno=lucas).status_code, 200)
        self.assertEqual(self.rec(self.login("paula@eduvance.com"), idAluno=lucas).status_code, 200)
        self.assertEqual(self.rec(self.login("paula@eduvance.com")).status_code, 400, "staff precisa informar o aluno")
        self.assertEqual(self.rec(self.login("paula@eduvance.com"), idAluno=999999).status_code, 404)


class TestServicoHttp(Rec):
    """O Flask conversa com o serviço pelo contrato POST /recomendar (o mesmo que o FastAPI expõe)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.srv = HTTPServer(("127.0.0.1", 0), ServicoFalso)
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        ServicoFalso.recebidos = []
        ServicoFalso.resposta = {
            "itens": [{"tipo": "REFORCO", "prioridade": "ALTA", "score": 91.0, "titulo": "Veio do serviço", "mensagem": "Resposta do serviço externo.",
                       "disciplina": "Matemática", "motivo": {"media": 3.0}, "link": "/boletim"}],
            "resumo": {"nivel": "CUIDADO", "altas": 1, "total": 1}}
        self.app.config["RECOMENDACAO_URL"] = self.url

    def tearDown(self):
        self.app.config["RECOMENDACAO_URL"] = ""

    def test_usa_o_servico_e_envia_dados_dos_tres_modulos(self):
        h = self.login(LUCAS)
        j = self.rec(h).get_json()
        self.assertEqual(j["origem"], "servico")
        self.assertEqual([i["titulo"] for i in j["itens"]], ["Veio do serviço"])
        caminho, corpo = ServicoFalso.recebidos[-1]
        self.assertEqual(caminho, "/recomendar")
        self.assertTrue(corpo["disciplinas"] and all("media" in d and "nome" in d for d in corpo["disciplinas"]), "Notas")
        self.assertIn("faltas", corpo)                                                                     # Frequência
        self.assertTrue(all({"titulo", "disciplina", "dias"} <= set(p) for p in corpo["provas"]) and corpo["provas"], "Agenda")
        self.assertIn("mediaAprovacao", corpo["parametros"])
        uid = self.c.get("/api/auth/me", headers=h).get_json()["usuario"]["id"]
        self.assertEqual(self.linhas(uid)[0][3], "servico", "a origem fica registrada no banco")

    def test_resposta_fora_do_contrato_cai_no_motor(self):
        ServicoFalso.resposta = {"qualquer": "coisa"}
        self.assertEqual(self.rec(self.login(LUCAS)).get_json()["origem"], "motor-fallback")

    def test_servico_fora_do_ar_cai_no_motor_embutido(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            porta = s.getsockname()[1]
        self.app.config["RECOMENDACAO_URL"] = f"http://127.0.0.1:{porta}"
        r = self.rec(self.login(LUCAS))
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertEqual(j["origem"], "motor-fallback")
        self.assertTrue(j["itens"], "o aluno continua recebendo recomendações")


def _dia_passado() -> str:
    from datetime import timedelta
    d = date.today() - timedelta(days=3)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


if __name__ == "__main__":
    unittest.main()
