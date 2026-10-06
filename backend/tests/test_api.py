"""Testes de integração da API (banco SQLite temporário, recriado a cada execução).

    cd backend && python -m unittest discover -s tests -v
"""
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta

from app import create_app
from app.init_db import criar_banco

SENHA = "senha123"


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls._dir.name, "teste.db")
        criar_banco(cls.db)
        cls.app = create_app({"DATABASE": cls.db, "TESTING": True, "LOGIN_MAX_POR_MINUTO": 1000})

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()

    def setUp(self):
        self.c = self.app.test_client()

    def login(self, ident, senha=SENHA):
        r = self.c.post("/api/auth/login", json={"identificador": ident, "senha": senha})
        self.assertEqual(r.status_code, 200, r.get_json())
        return {"Authorization": f"Bearer {r.get_json()['token']}"}

    def admin(self):
        return self.login("admin@eduvance.com", "admin123")


class TestBancoELogin(Base):
    def test_health_conexao_banco(self):
        r = self.c.get("/api/health")
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertEqual(j["status"], "ok")
        self.assertGreaterEqual(j["tabelas"], 25)
        self.assertGreater(j["usuarios"], 100)

    def test_login_por_email(self):
        r = self.c.post("/api/auth/login", json={"identificador": "ricardo@eduvance.com", "senha": SENHA})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["usuario"]["perfil"], "PROFESSOR")
        self.assertNotIn("senha_hash", r.get_json()["usuario"])

    def test_login_aluno_por_matricula(self):
        r = self.c.post("/api/auth/login", json={"identificador": f"{date.today().year}0001", "senha": SENHA})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["usuario"]["nome"], "Lucas Silva")

    def test_login_email_case_insensitive(self):
        r = self.c.post("/api/auth/login", json={"identificador": "RICARDO@Eduvance.com", "senha": SENHA})
        self.assertEqual(r.status_code, 200)

    def test_login_senha_errada_e_usuario_inexistente(self):
        for ident, senha in [("ricardo@eduvance.com", "errada"), ("naoexiste@x.com", SENHA)]:
            r = self.c.post("/api/auth/login", json={"identificador": ident, "senha": senha})
            self.assertEqual(r.status_code, 401)
            self.assertEqual(r.get_json()["erro"], "Credenciais inválidas")

    def test_login_campos_obrigatorios(self):
        r = self.c.post("/api/auth/login", json={})
        self.assertEqual(r.status_code, 400)

    def test_senha_nao_e_texto_puro(self):
        import sqlite3

        con = sqlite3.connect(self.db)
        h = con.execute("SELECT senha_hash FROM usuario WHERE email='ricardo@eduvance.com'").fetchone()[0]
        con.close()
        self.assertNotIn(SENHA, h)
        self.assertTrue(h.startswith("pbkdf2:sha256"))

    def test_rota_protegida_sem_token(self):
        self.assertEqual(self.c.get("/api/dashboard").status_code, 401)
        self.assertEqual(self.c.get("/api/dashboard", headers={"Authorization": "Bearer lixo"}).status_code, 401)

    def test_me(self):
        r = self.c.get("/api/auth/me", headers=self.login("maria@eduvance.com"))
        self.assertEqual(r.get_json()["usuario"]["perfil"], "RESPONSAVEL")
        self.assertEqual(len(r.get_json()["usuario"]["alunos"]), 2)

    def test_usuario_inativo_nao_loga(self):
        h = self.admin()
        novo = self.c.post("/api/usuarios", headers=h, json={"nome": "Inativo Teste", "email": "inativo@x.com", "senha": "abc123", "perfil": "PROFESSOR", "ativo": False})
        self.assertEqual(novo.status_code, 201)
        r = self.c.post("/api/auth/login", json={"identificador": "inativo@x.com", "senha": "abc123"})
        self.assertEqual(r.status_code, 401)


class TestCadastroEPerfis(Base):
    def test_admin_cadastra_cada_perfil(self):
        h = self.admin()
        casos = [
            {"perfil": "PROFESSOR", "nome": "Prof Novo", "email": "prof.novo@x.com", "especialidade": "Física"},
            {"perfil": "COORDENADOR", "nome": "Coord Nova", "email": "coord.nova@x.com", "cargo": "Coordenadora Pedagógica"},
            {"perfil": "RESPONSAVEL", "nome": "Resp Novo", "email": "resp.novo@x.com", "telefone": "(81) 90000-0000"},
            {"perfil": "ALUNO", "nome": "Aluno Novo", "email": "aluno.novo@x.com", "matricula": "TESTE001", "serie": "8º Ano", "idTurma": 2, "dataNascimento": "2011-05-05"},
        ]
        for c in casos:
            r = self.c.post("/api/usuarios", headers=h, json={**c, "senha": "abc123"})
            self.assertEqual(r.status_code, 201, r.get_json())
            self.assertEqual(r.get_json()["perfil"], c["perfil"])
        # o novo aluno consegue logar por matrícula
        self.assertEqual(self.c.post("/api/auth/login", json={"identificador": "TESTE001", "senha": "abc123"}).status_code, 200)

    def test_validacoes_de_cadastro(self):
        h = self.admin()
        r = self.c.post("/api/usuarios", headers=h, json={"perfil": "ALUNO", "nome": "Al", "email": "invalido", "senha": "123"})
        self.assertEqual(r.status_code, 400)
        campos = {d["campo"] for d in r.get_json()["detalhes"]}
        self.assertTrue({"nome", "email", "senha", "matricula"} <= campos)

    def test_email_e_matricula_duplicados(self):
        h = self.admin()
        r = self.c.post("/api/usuarios", headers=h, json={"perfil": "PROFESSOR", "nome": "Dup Email", "email": "RICARDO@eduvance.com", "senha": "abc123"})
        self.assertEqual(r.status_code, 409)
        r = self.c.post("/api/usuarios", headers=h, json={"perfil": "ALUNO", "nome": "Dup Mat", "email": "dup.mat@x.com", "senha": "abc123", "matricula": f"{date.today().year}0001"})
        self.assertEqual(r.status_code, 409)

    def test_aluno_com_no_maximo_dois_responsaveis(self):
        h = self.admin()
        ids = []
        for i in range(3):
            r = self.c.post("/api/usuarios", headers=h, json={"perfil": "RESPONSAVEL", "nome": f"Resp Max {i}", "email": f"max{i}@x.com", "senha": "abc123"})
            ids.append(r.get_json()["id"])
        resp = [{"idResponsavel": i, "grauParentesco": "Tio"} for i in ids]
        r = self.c.post("/api/usuarios", headers=h, json={"perfil": "ALUNO", "nome": "Aluno Tres Resp", "email": "tres@x.com", "senha": "abc123", "matricula": "MAX3", "responsaveis": resp})
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/usuarios", headers=h, json={"perfil": "ALUNO", "nome": "Aluno Dois Resp", "email": "dois@x.com", "senha": "abc123", "matricula": "MAX2", "responsaveis": resp[:2]})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.get_json()["responsaveis"]), 2)

    def test_rbac_cadastro_de_usuarios(self):
        # coordenador só gerencia professores
        h = self.login("paula@eduvance.com")
        ok = self.c.post("/api/usuarios", headers=h, json={"perfil": "PROFESSOR", "nome": "Prof da Paula", "email": "pp@x.com", "senha": "abc123"})
        self.assertEqual(ok.status_code, 201)
        nok = self.c.post("/api/usuarios", headers=h, json={"perfil": "ADMIN", "nome": "Tentativa Admin", "email": "adm@x.com", "senha": "abc123"})
        self.assertEqual(nok.status_code, 403)
        lista = self.c.get("/api/usuarios", headers=h).get_json()
        self.assertTrue(all(u["perfil"] == "PROFESSOR" for u in lista))
        # professor, aluno e responsável não acessam a gestão de usuários
        for ident in ("ricardo@eduvance.com", f"{date.today().year}0001", "maria@eduvance.com"):
            self.assertEqual(self.c.get("/api/usuarios", headers=self.login(ident)).status_code, 403)
            self.assertEqual(self.c.post("/api/usuarios", headers=self.login(ident), json={}).status_code, 403)

    def test_atualizar_e_excluir_usuario(self):
        h = self.admin()
        novo = self.c.post("/api/usuarios", headers=h, json={"perfil": "PROFESSOR", "nome": "Para Editar", "email": "editar@x.com", "senha": "abc123", "especialidade": "Artes"}).get_json()
        r = self.c.put(f"/api/usuarios/{novo['id']}", headers=h, json={"nome": "Editado Silva", "email": "editar@x.com", "especialidade": "Música", "senha": "nova123"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["nome"], "Editado Silva")
        self.assertEqual(r.get_json()["especialidade"], "Música")
        self.assertEqual(self.c.post("/api/auth/login", json={"identificador": "editar@x.com", "senha": "nova123"}).status_code, 200)
        self.assertEqual(self.c.delete(f"/api/usuarios/{novo['id']}", headers=h).status_code, 204)
        self.assertEqual(self.c.get(f"/api/usuarios/{novo['id']}", headers=h).status_code, 404)
        # não pode excluir a si mesmo
        me = self.c.get("/api/auth/me", headers=h).get_json()["usuario"]["id"]
        self.assertEqual(self.c.delete(f"/api/usuarios/{me}", headers=h).status_code, 400)


def _prazo(dias=3):
    return (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%dT18:00")


class TestCrudAtividades(Base):
    def _td(self, h, turma="8º Ano B", disciplina="Matemática"):
        for td in self.c.get("/api/catalogo/turma-disciplinas", headers=h).get_json():
            if td["turma"] == turma and td["disciplina"] == disciplina:
                return td["id"]
        self.fail("turma/disciplina não encontrada")

    def test_ciclo_completo_crud(self):
        h = self.login("ricardo@eduvance.com")
        td = self._td(h)
        # CREATE
        r = self.c.post("/api/atividades", headers=h, json={"titulo": "Lista de Logaritmos", "descricao": "Cap. 5", "dataEntrega": _prazo(), "idTurmaDisciplina": td})
        self.assertEqual(r.status_code, 201, r.get_json())
        a = r.get_json()
        self.assertEqual(a["turma"], "8º Ano B")
        # READ
        self.assertEqual(self.c.get(f"/api/atividades/{a['id']}", headers=h).get_json()["titulo"], "Lista de Logaritmos")
        self.assertIn(a["id"], [x["id"] for x in self.c.get("/api/atividades", headers=h).get_json()])
        # UPDATE
        r = self.c.put(f"/api/atividades/{a['id']}", headers=h, json={"titulo": "Lista de Logaritmos (revisada)", "descricao": "Cap. 5 e 6", "dataEntrega": _prazo(5), "idTurmaDisciplina": td})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["titulo"], "Lista de Logaritmos (revisada)")
        # persistência real: nova requisição lê do banco
        self.assertEqual(self.c.get(f"/api/atividades/{a['id']}", headers=h).get_json()["descricao"], "Cap. 5 e 6")
        # DELETE
        self.assertEqual(self.c.delete(f"/api/atividades/{a['id']}", headers=h).status_code, 204)
        self.assertEqual(self.c.get(f"/api/atividades/{a['id']}", headers=h).status_code, 404)

    def test_validacao_atividade(self):
        h = self.login("ricardo@eduvance.com")
        r = self.c.post("/api/atividades", headers=h, json={"titulo": "ab", "dataEntrega": "ontem", "idTurmaDisciplina": self._td(h)})
        self.assertEqual(r.status_code, 400)
        self.assertEqual({d["campo"] for d in r.get_json()["detalhes"]}, {"titulo", "dataEntrega"})

    def test_professor_nao_gerencia_turma_de_outro(self):
        prof = self.login("ricardo@eduvance.com")
        coord = self.login("paula@eduvance.com")
        td_outro = self._td(coord, "8º Ano B", "Português")  # professora Ana
        r = self.c.post("/api/atividades", headers=prof, json={"titulo": "Invasão", "dataEntrega": _prazo(), "idTurmaDisciplina": td_outro})
        self.assertEqual(r.status_code, 403)
        # atividade criada pela coordenadora na turma da Ana: Ricardo não edita nem exclui
        a = self.c.post("/api/atividades", headers=coord, json={"titulo": "Da Coordenação", "dataEntrega": _prazo(), "idTurmaDisciplina": td_outro}).get_json()
        self.assertEqual(self.c.put(f"/api/atividades/{a['id']}", headers=prof, json={"titulo": "Hack", "dataEntrega": _prazo(), "idTurmaDisciplina": td_outro}).status_code, 403)
        self.assertEqual(self.c.delete(f"/api/atividades/{a['id']}", headers=prof).status_code, 403)
        self.assertEqual(self.c.get(f"/api/atividades/{a['id']}", headers=prof).status_code, 403)
        self.assertEqual(self.c.delete(f"/api/atividades/{a['id']}", headers=coord).status_code, 204)

    def test_aluno_e_responsavel_somente_leitura(self):
        aluno = self.login(f"{date.today().year}0001")
        resp = self.login("maria@eduvance.com")
        td = self._td(self.admin())
        body = {"titulo": "Tentativa", "dataEntrega": _prazo(), "idTurmaDisciplina": td}
        for h in (aluno, resp):
            self.assertEqual(self.c.post("/api/atividades", headers=h, json=body).status_code, 403)
        lista = self.c.get("/api/atividades", headers=aluno).get_json()
        self.assertGreaterEqual(len(lista), 5)
        self.assertTrue(all(a["turma"] == "8º Ano B" for a in lista))
        self.assertTrue(all("urgencia" in a for a in lista))
        # responsável vê as atividades do aluno vinculado (escolhido por alunoId) e não as de aluno alheio
        lucas = self.c.get("/api/auth/me", headers=aluno).get_json()["usuario"]["id"]
        do_lucas = self.c.get(f"/api/atividades?alunoId={lucas}", headers=resp).get_json()
        self.assertTrue(len(do_lucas) >= 5 and all(a["turma"] == "8º Ano B" for a in do_lucas))
        mariana = self.c.get("/api/usuarios?q=mariana", headers=self.admin()).get_json()[0]["id"]
        self.assertEqual(self.c.get(f"/api/atividades?alunoId={mariana}", headers=resp).get_json(), [])

    def test_aluno_marca_entrega(self):
        h = self.login(f"{date.today().year}0001")
        a = self.c.get("/api/atividades", headers=h).get_json()[0]
        r = self.c.put(f"/api/atividades/{a['id']}/entrega", headers=h, json={"status": "ENTREGUE"})
        self.assertEqual(r.status_code, 200)
        depois = {x["id"]: x for x in self.c.get("/api/atividades", headers=h).get_json()}
        self.assertEqual(depois[a["id"]]["statusEntrega"], "ENTREGUE")
        self.assertEqual(depois[a["id"]]["urgencia"], "ENTREGUE")
        dash = self.c.get("/api/dashboard", headers=h).get_json()
        self.assertNotIn(a["id"], [x["id"] for x in dash["atividades"]])
        self.assertEqual(self.c.put(f"/api/atividades/{a['id']}/entrega", headers=h, json={"status": "XPTO"}).status_code, 400)


class TestNotasEDashboards(Base):
    def test_lancamento_de_notas(self):
        h = self.login("ricardo@eduvance.com")
        td = next(t["id"] for t in self.c.get("/api/catalogo/turma-disciplinas", headers=h).get_json() if t["turma"] == "8º Ano B")
        d = self.c.get(f"/api/notas/turma-disciplina/{td}", headers=h).get_json()
        self.assertEqual(len(d["alunos"]), 28)
        self.assertEqual(d["alunos"][0]["nome"], "Lucas Silva")
        self.assertEqual(d["alunos"][0]["valor"], 7.5)
        fill = d["alunos"][10]
        self.assertIsNone(fill["valor"])
        r = self.c.put("/api/notas", headers=h, json={"idAvaliacao": d["avaliacao"]["id"], "idAluno": fill["idAluno"], "valor": 8.25})
        self.assertEqual(r.status_code, 200)
        d2 = self.c.get(f"/api/notas/turma-disciplina/{td}", headers=h).get_json()
        self.assertEqual(d2["alunos"][10]["valor"], 8.25)
        self.assertEqual(self.c.put("/api/notas", headers=h, json={"idAvaliacao": d["avaliacao"]["id"], "idAluno": fill["idAluno"], "valor": 11}).status_code, 400)
        self.assertEqual(self.c.put("/api/notas", headers=h, json={"idAvaliacao": d["avaliacao"]["id"], "idAluno": fill["idAluno"], "valor": None}).status_code, 200)

    def test_notas_rbac(self):
        for ident in (f"{date.today().year}0001", "maria@eduvance.com"):
            self.assertEqual(self.c.put("/api/notas", headers=self.login(ident), json={"idAvaliacao": 1, "idAluno": 1, "valor": 10}).status_code, 403)
        # professor de outra disciplina não lança nota
        ana = self.login("ana.guimaraes@eduvance.com")
        coord = self.login("paula@eduvance.com")
        td_mat = next(t["id"] for t in self.c.get("/api/catalogo/turma-disciplinas", headers=coord).get_json() if t["turma"] == "8º Ano B" and t["disciplina"] == "Matemática")
        self.assertEqual(self.c.get(f"/api/notas/turma-disciplina/{td_mat}", headers=ana).status_code, 403)

    def test_dashboard_aluno_bate_com_prototipo(self):
        d = self.c.get("/api/dashboard", headers=self.login(f"{date.today().year}0001")).get_json()
        self.assertEqual(d["mediaGeral"], 8.2)
        self.assertEqual(d["faltas"], 3)
        self.assertEqual(d["atividadesPendentes"], 5)
        self.assertEqual(d["faltasStatus"], "Dentro do limite")
        self.assertEqual(d["classificacaoMedia"], "Excelente")
        self.assertEqual({b["materia"]: b["nota"] for b in d["boletim"]}["Matemática"], 7.5)

    def test_dashboard_por_perfil(self):
        prof = self.c.get("/api/dashboard", headers=self.login("ricardo@eduvance.com")).get_json()
        self.assertEqual(prof["perfil"], "PROFESSOR")
        self.assertEqual({t["turma"] for t in prof["turmas"]}, {"8º Ano A", "8º Ano B", "9º Ano A", "5º Ano A"})
        coord = self.c.get("/api/dashboard", headers=self.login("paula@eduvance.com")).get_json()
        self.assertEqual(coord["kpis"]["ocorrenciasAbertas"], 4)
        self.assertEqual(coord["kpis"]["professoresAtivos"] >= 5, True)
        self.assertEqual(len(coord["eventos"]), 3)
        resp = self.c.get("/api/dashboard", headers=self.login("maria@eduvance.com")).get_json()
        self.assertEqual([a["nome"] for a in resp["alunos"]], ["Lucas Silva", "Ana Silva"])
        self.assertEqual(resp["alunos"][0]["mediaGeral"], 8.2)
        adm = self.c.get("/api/dashboard", headers=self.admin()).get_json()
        self.assertEqual(adm["perfil"], "ADMIN")

    def test_resumo_do_aluno_respeita_vinculo(self):
        maria = self.login("maria@eduvance.com")
        lucas = self.c.get("/api/auth/me", headers=self.login(f"{date.today().year}0001")).get_json()["usuario"]["id"]
        r = self.c.get(f"/api/alunos/{lucas}/resumo", headers=maria)
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertEqual(len(j["boletim"]), 5)
        self.assertEqual(j["mensalidades"][0]["status"], "ABERTA")
        # Mariana (outro aluno) não é filha da Maria
        mariana = self.c.get("/api/usuarios?q=mariana", headers=self.admin()).get_json()[0]["id"]
        self.assertEqual(self.c.get(f"/api/alunos/{mariana}/resumo", headers=maria).status_code, 403)
        # joão (pai) também acessa Lucas
        self.assertEqual(self.c.get(f"/api/alunos/{lucas}/resumo", headers=self.login("joao.silva@eduvance.com")).status_code, 200)

    def test_vestibular(self):
        h = self.login(f"{date.today().year}0001")
        d = self.c.get("/api/vestibular", headers=h).get_json()
        self.assertEqual([s["classificacao"] for s in d["simulados"]], ["Excelente", "Acima da Média"])
        self.assertEqual(d["redacoes"][0]["nota"], 840)
        self.assertEqual(sorted(f["respostas"] for f in d["foruns"]), [8, 12])
        self.assertEqual(len(self.c.get("/api/vestibular?foco=Unicamp", headers=h).get_json()["simulados"]), 1)
        self.assertEqual(self.c.get("/api/vestibular", headers=self.login("ricardo@eduvance.com")).status_code, 403)
        r = self.c.post("/api/vestibular/redacoes", headers=h, json={"tema": "Tema curto de teste", "texto": "x" * 60})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.c.get("/api/vestibular", headers=h).get_json()["redacoes"]), 2)
        self.assertEqual(self.c.post("/api/vestibular/redacoes", headers=h, json={"tema": "Tema", "texto": "curto"}).status_code, 400)


# ---------------------------------------------------------------------------
# Sprint 04 — módulo Notas, Frequência e Boletim
# ---------------------------------------------------------------------------
def _dia_util(recuo=0):
    d = date.today() - timedelta(days=recuo)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


class ModuloBase(Base):
    def td(self, h, turma="8º Ano B", disciplina="Matemática"):
        for t in self.c.get("/api/catalogo/turma-disciplinas", headers=h).get_json():
            if t["turma"] == turma and t["disciplina"] == disciplina:
                return t["id"]
        self.fail("turma/disciplina não encontrada")

    def nova_avaliacao(self, h, titulo, bimestre=3, tipo="TESTE", peso=1, turma="8º Ano B", disciplina="Matemática"):
        r = self.c.post("/api/avaliacoes", headers=h, json={
            "titulo": titulo, "tipo": tipo, "bimestre": bimestre, "peso": peso,
            "dataAvaliacao": f"{date.today().year}-10-20", "idTurmaDisciplina": self.td(h, turma, disciplina)})
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()

    def id_lucas(self):
        return self.c.get("/api/auth/me", headers=self.login(f"{date.today().year}0001")).get_json()["usuario"]["id"]


class TestAvaliacoes(ModuloBase):
    def test_ciclo_completo_e_persistencia(self):
        h = self.login("ricardo@eduvance.com")
        a = self.nova_avaliacao(h, "Teste de Funções")
        self.assertEqual(a["turma"], "8º Ano B")
        self.assertEqual(a["notasLancadas"], 0)
        r = self.c.put(f"/api/avaliacoes/{a['id']}", headers=h, json={
            "titulo": "Teste de Funções (revisado)", "tipo": "PROVA", "bimestre": 3, "peso": 2,
            "dataAvaliacao": f"{date.today().year}-10-22", "idTurmaDisciplina": a["idTurmaDisciplina"]})
        self.assertEqual(r.status_code, 200, r.get_json())
        lido = self.c.get(f"/api/avaliacoes/{a['id']}", headers=h).get_json()
        self.assertEqual((lido["titulo"], lido["tipo"], lido["peso"]), ("Teste de Funções (revisado)", "PROVA", 2.0))
        self.assertIn(a["id"], [x["id"] for x in self.c.get("/api/avaliacoes?bimestre=3", headers=h).get_json()])
        self.assertEqual(self.c.delete(f"/api/avaliacoes/{a['id']}", headers=h).status_code, 204)
        self.assertEqual(self.c.get(f"/api/avaliacoes/{a['id']}", headers=h).status_code, 404)

    def test_validacoes(self):
        h = self.login("ricardo@eduvance.com")
        td = self.td(h)
        r = self.c.post("/api/avaliacoes", headers=h, json={"titulo": "x", "tipo": "XYZ", "bimestre": 9, "dataAvaliacao": "2026-02-30", "peso": 10})
        self.assertEqual(r.status_code, 400)
        campos = {d["campo"] for d in r.get_json()["detalhes"]}
        self.assertTrue({"titulo", "tipo", "bimestre", "dataAvaliacao", "peso", "idTurmaDisciplina"} <= campos)
        r = self.c.post("/api/avaliacoes", headers=h, json={"titulo": "Prova antiga", "tipo": "PROVA", "bimestre": 1, "dataAvaliacao": "2019-05-10", "idTurmaDisciplina": td})
        self.assertEqual(r.status_code, 400)
        self.assertIn("ano letivo", r.get_json()["detalhes"][0]["mensagem"])

    def test_titulo_duplicado_no_bimestre(self):
        h = self.login("ricardo@eduvance.com")
        self.nova_avaliacao(h, "Prova Duplicada", bimestre=4)
        r = self.c.post("/api/avaliacoes", headers=h, json={"titulo": "prova duplicada", "tipo": "PROVA", "bimestre": 4,
                                                           "dataAvaliacao": f"{date.today().year}-11-10", "idTurmaDisciplina": self.td(h)})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["detalhes"][0]["campo"], "titulo")
        # o mesmo título em outro bimestre é permitido
        self.nova_avaliacao(h, "Prova Duplicada", bimestre=3)

    def test_nao_exclui_avaliacao_com_notas(self):
        h = self.login("ricardo@eduvance.com")
        a = self.nova_avaliacao(h, "Prova com Notas")
        aluno = self.c.get(f"/api/notas/avaliacao/{a['id']}", headers=h).get_json()["alunos"][0]["idAluno"]
        self.assertEqual(self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=h, json={"notas": [{"idAluno": aluno, "valor": 7}]}).status_code, 200)
        r = self.c.delete(f"/api/avaliacoes/{a['id']}", headers=h)
        self.assertEqual(r.status_code, 409)
        self.assertIn("notas lançadas", r.get_json()["erro"])
        self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=h, json={"notas": [{"idAluno": aluno, "valor": None}]})
        self.assertEqual(self.c.delete(f"/api/avaliacoes/{a['id']}", headers=h).status_code, 204)

    def test_rbac(self):
        ricardo, ana = self.login("ricardo@eduvance.com"), self.login("ana.guimaraes@eduvance.com")
        a = self.nova_avaliacao(ricardo, "Só do Ricardo")
        # outro professor não vê, não edita e não exclui
        self.assertEqual(self.c.get(f"/api/avaliacoes/{a['id']}", headers=ana).status_code, 403)
        self.assertEqual(self.c.delete(f"/api/avaliacoes/{a['id']}", headers=ana).status_code, 403)
        self.assertNotIn(a["id"], [x["id"] for x in self.c.get("/api/avaliacoes", headers=ana).get_json()])
        # nem cria numa disciplina que não leciona
        r = self.c.post("/api/avaliacoes", headers=ana, json={"titulo": "Invasão", "tipo": "PROVA", "bimestre": 3,
                        "dataAvaliacao": f"{date.today().year}-10-20", "idTurmaDisciplina": a["idTurmaDisciplina"]})
        self.assertEqual(r.status_code, 403)
        # coordenação e admin gerenciam; aluno e responsável não acessam
        self.assertEqual(self.c.get(f"/api/avaliacoes/{a['id']}", headers=self.login("paula@eduvance.com")).status_code, 200)
        self.assertEqual(self.c.get("/api/avaliacoes", headers=self.admin()).status_code, 200)
        for ident in (f"{date.today().year}0001", "maria@eduvance.com"):
            self.assertEqual(self.c.get("/api/avaliacoes", headers=self.login(ident)).status_code, 403)


class TestNotasEmLote(ModuloBase):
    def test_lancamento_persistente_e_media(self):
        h = self.login("ricardo@eduvance.com")
        a = self.nova_avaliacao(h, "Prova Lote")
        d = self.c.get(f"/api/notas/avaliacao/{a['id']}", headers=h).get_json()
        self.assertEqual(len(d["alunos"]), 28)
        self.assertIsNone(d["media"])
        ids = [x["idAluno"] for x in d["alunos"]][:3]
        r = self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=h, json={"notas": [
            {"idAluno": ids[0], "valor": "8,0"}, {"idAluno": ids[1], "valor": 6}, {"idAluno": ids[2], "valor": 10}]})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual((r.get_json()["salvas"], r.get_json()["media"]), (3, 8.0))
        # lido novamente do banco
        lidas = {x["idAluno"]: x["valor"] for x in self.c.get(f"/api/notas/avaliacao/{a['id']}", headers=h).get_json()["alunos"]}
        self.assertEqual([lidas[i] for i in ids], [8.0, 6.0, 10.0])
        # valor nulo remove a nota
        r = self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=h, json={"notas": [{"idAluno": ids[1], "valor": None}]})
        self.assertEqual(r.get_json()["removidas"], 1)
        self.assertEqual(r.get_json()["media"], 9.0)

    def test_validacao_atomica(self):
        h = self.login("ricardo@eduvance.com")
        a = self.nova_avaliacao(h, "Prova Atômica")
        ids = [x["idAluno"] for x in self.c.get(f"/api/notas/avaliacao/{a['id']}", headers=h).get_json()["alunos"]][:3]
        r = self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=h, json={"notas": [
            {"idAluno": ids[0], "valor": 9}, {"idAluno": ids[1], "valor": 11}, {"idAluno": ids[2], "valor": "abc"}]})
        self.assertEqual(r.status_code, 400)
        self.assertEqual({d["campo"] for d in r.get_json()["detalhes"]}, {f"nota-{ids[1]}", f"nota-{ids[2]}"})
        # nada foi gravado, nem a nota válida
        self.assertTrue(all(x["valor"] is None for x in self.c.get(f"/api/notas/avaliacao/{a['id']}", headers=h).get_json()["alunos"]))
        self.assertEqual(self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=h, json={"notas": []}).status_code, 400)
        r = self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=h, json={"notas": [{"idAluno": 999999, "valor": 5}]})
        self.assertEqual(r.status_code, 400)

    def test_rbac_do_lancamento(self):
        h = self.login("ricardo@eduvance.com")
        a = self.nova_avaliacao(h, "Prova RBAC")
        corpo = {"notas": [{"idAluno": self.id_lucas(), "valor": 5}]}
        self.assertEqual(self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=self.login("ana.guimaraes@eduvance.com"), json=corpo).status_code, 403)
        self.assertEqual(self.c.get(f"/api/notas/avaliacao/{a['id']}", headers=self.login("ana.guimaraes@eduvance.com")).status_code, 403)
        for ident in (f"{date.today().year}0001", "maria@eduvance.com"):
            self.assertEqual(self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=self.login(ident), json=corpo).status_code, 403)
        self.assertEqual(self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=self.login("paula@eduvance.com"), json=corpo).status_code, 200)
        self.assertEqual(self.c.get("/api/notas/avaliacao/999999", headers=h).status_code, 404)


class TestFrequencia(ModuloBase):
    def _chamada(self, h, td, dia, faltosos=()):
        d = self.c.get(f"/api/frequencia?idTurmaDisciplina={td}&data={dia}", headers=h).get_json()
        return d, [{"idAluno": a["idAluno"], "presente": a["idAluno"] not in faltosos} for a in d["alunos"]]

    def test_chamada_persistente_e_atualizacao(self):
        h = self.login("ricardo@eduvance.com")
        td, dia = self.td(h), _dia_util()
        d, regs = self._chamada(h, td, dia)
        self.assertFalse(d["registrada"])
        self.assertEqual(len(regs), 28)
        faltoso = regs[5]["idAluno"]
        r = self.c.put("/api/frequencia", headers=h, json={"idTurmaDisciplina": td, "data": str(dia),
                       "registros": [{**x, "presente": x["idAluno"] != faltoso} for x in regs]})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(r.get_json()["resumo"], {"presentes": 27, "faltas": 1})
        # lido de novo do banco
        d2 = self.c.get(f"/api/frequencia?idTurmaDisciplina={td}&data={dia}", headers=h).get_json()
        self.assertTrue(d2["registrada"])
        self.assertFalse(next(a for a in d2["alunos"] if a["idAluno"] == faltoso)["presente"])
        # corrigir a chamada não duplica registros
        r = self.c.put("/api/frequencia", headers=h, json={"idTurmaDisciplina": td, "data": str(dia), "registros": [{**x, "presente": True} for x in regs]})
        self.assertEqual(r.get_json()["resumo"]["faltas"], 0)
        self.assertEqual(next(a for a in r.get_json()["alunos"] if a["idAluno"] == faltoso)["aulas"], 1)

    def test_validacoes_da_chamada(self):
        h = self.login("ricardo@eduvance.com")
        td = self.td(h)
        d, regs = self._chamada(h, td, _dia_util())
        base = {"idTurmaDisciplina": td, "registros": regs}
        futuro = self.c.put("/api/frequencia", headers=h, json={**base, "data": str(date.today() + timedelta(days=3))})
        self.assertEqual(futuro.status_code, 400)
        self.assertIn("futura", futuro.get_json()["erro"])
        sabado = date.today() - timedelta(days=(date.today().weekday() - 5) % 7 or 7)
        self.assertEqual(sabado.weekday(), 5)
        self.assertEqual(self.c.put("/api/frequencia", headers=h, json={**base, "data": str(sabado)}).status_code, 400)
        self.assertEqual(self.c.put("/api/frequencia", headers=h, json={**base, "data": "31/12/2025"}).status_code, 400)
        incompleta = self.c.put("/api/frequencia", headers=h, json={**base, "data": str(_dia_util(1)), "registros": regs[:10]})
        self.assertEqual(incompleta.status_code, 400)
        self.assertIn("faltam 18", incompleta.get_json()["erro"])
        ruim = self.c.put("/api/frequencia", headers=h, json={**base, "data": str(_dia_util(1)), "registros": [{"idAluno": regs[0]["idAluno"], "presente": "sim"}]})
        self.assertEqual(ruim.status_code, 400)

    def test_rbac_da_chamada(self):
        h = self.login("ricardo@eduvance.com")
        td = self.td(h)
        _, regs = self._chamada(h, td, _dia_util(2))
        corpo = {"idTurmaDisciplina": td, "data": str(_dia_util(2)), "registros": regs}
        self.assertEqual(self.c.put("/api/frequencia", headers=self.login("ana.guimaraes@eduvance.com"), json=corpo).status_code, 403)
        self.assertEqual(self.c.get(f"/api/frequencia?idTurmaDisciplina={td}&data={_dia_util()}", headers=self.login("ana.guimaraes@eduvance.com")).status_code, 403)
        for ident in (f"{date.today().year}0001", "maria@eduvance.com"):
            self.assertEqual(self.c.put("/api/frequencia", headers=self.login(ident), json=corpo).status_code, 403)

    def test_faltas_acumuladas_e_alerta(self):
        h = self.login("ricardo@eduvance.com")
        td = self.td(h, "8º Ano A", "Matemática")
        faltoso = self.c.get(f"/api/frequencia?idTurmaDisciplina={td}&data={_dia_util()}", headers=h).get_json()["alunos"][0]["idAluno"]
        for recuo in range(0, 14):
            d = _dia_util(recuo * 2)
            _, regs = self._chamada(h, td, d)
            self.c.put("/api/frequencia", headers=h, json={"idTurmaDisciplina": td, "data": str(d),
                       "registros": [{**x, "presente": x["idAluno"] != faltoso} for x in regs]})
        a = next(x for x in self.c.get(f"/api/frequencia?idTurmaDisciplina={td}&data={_dia_util()}", headers=h).get_json()["alunos"] if x["idAluno"] == faltoso)
        self.assertGreaterEqual(a["faltas"], 10)
        self.assertTrue(a["abaixoDoMinimo"])
        # reflete no boletim: reprovado por faltas
        b = self.c.get(f"/api/boletim/{faltoso}", headers=self.admin()).get_json()
        mat = next(x for x in b["disciplinas"] if x["materia"] == "Matemática")
        self.assertEqual(mat["situacao"], "Reprovado por faltas")


class TestBoletimCompleto(ModuloBase):
    def test_boletim_do_aluno_bate_com_o_seed(self):
        lucas = self.id_lucas()
        b = self.c.get(f"/api/boletim/{lucas}", headers=self.login(f"{date.today().year}0001")).get_json()
        self.assertEqual(b["aluno"]["nome"], "Lucas Silva")
        self.assertEqual([d["materia"] for d in b["disciplinas"]], ["Matemática", "Português", "História", "Ciências", "Geografia"])
        mat = b["disciplinas"][0]
        # B1: prova 7,0 (peso 1) e trabalho 8,0 (peso 0,5) -> 7,3; B2: prova 7,5
        self.assertEqual((mat["bimestres"]["1"], mat["bimestres"]["2"], mat["bimestres"]["3"]), (7.3, 7.5, None))
        self.assertEqual((mat["mediaParcial"], mat["situacao"]), (7.4, "Aprovado"))
        self.assertEqual(mat["frequencia"], 95.0)
        self.assertEqual(len(mat["avaliacoes"]), 3)
        self.assertEqual(b["faltasTotal"], 3)

    def test_media_ponderada_responde_a_novas_notas(self):
        h = self.login("ricardo@eduvance.com")
        a = self.nova_avaliacao(h, "Prova B3 Peso 2", bimestre=3, tipo="PROVA", peso=2)
        self.c.put(f"/api/notas/avaliacao/{a['id']}", headers=h, json={"notas": [{"idAluno": self.id_lucas(), "valor": 4}]})
        b = self.c.get(f"/api/boletim/{self.id_lucas()}", headers=self.admin()).get_json()
        mat = b["disciplinas"][0]
        self.assertEqual(mat["bimestres"]["3"], 4.0)
        self.assertEqual(mat["mediaParcial"], 6.3)  # (7,3 + 7,5 + 4,0) / 3
        self.assertEqual(mat["situacao"], "Aprovado")

    def test_rbac_do_boletim(self):
        lucas = self.id_lucas()
        outro = self.c.get("/api/catalogo/alunos?busca=Mariana", headers=self.admin()).get_json()[0]["id"]
        self.assertEqual(self.c.get(f"/api/boletim/{lucas}", headers=self.login("maria@eduvance.com")).status_code, 200)
        self.assertEqual(self.c.get(f"/api/boletim/{outro}", headers=self.login("maria@eduvance.com")).status_code, 403)
        self.assertEqual(self.c.get(f"/api/boletim/{outro}", headers=self.login(f"{date.today().year}0001")).status_code, 403)
        self.assertEqual(self.c.get(f"/api/boletim/{outro}", headers=self.login("paula@eduvance.com")).status_code, 200)
        self.assertEqual(self.c.get(f"/api/boletim/{lucas}", headers=self.login("ricardo@eduvance.com")).status_code, 200)
        self.assertEqual(self.c.get("/api/boletim/999999", headers=self.admin()).status_code, 404)
        self.assertEqual(self.c.get(f"/api/boletim/{lucas}").status_code, 401)

    def test_catalogo_de_alunos_por_perfil(self):
        self.assertEqual(len(self.c.get("/api/catalogo/alunos", headers=self.login("ricardo@eduvance.com")).get_json()), 110)
        self.assertEqual(len(self.c.get("/api/catalogo/alunos?idTurma=2", headers=self.admin()).get_json()), 28)
        self.assertEqual(self.c.get("/api/catalogo/alunos", headers=self.login("maria@eduvance.com")).status_code, 403)


if __name__ == "__main__":
    unittest.main()
