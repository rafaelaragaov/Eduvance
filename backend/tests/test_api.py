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


if __name__ == "__main__":
    unittest.main()
