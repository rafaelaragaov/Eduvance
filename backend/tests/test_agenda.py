"""Testes do módulo Agenda e Calendário Escolar (Sprint 06): agenda, calendário de provas, eventos, lembretes e
preferências (Configurações), incluindo a integração com Notas (Sprint 04) e Notificações (Sprint 05).

    cd backend && python -m unittest discover -s tests -v

As datas usadas nos cenários de escrita são fixas (novembro do ano corrente) e não dependem do dia da semana
em que a suíte é executada.
"""
import unittest
from datetime import date, timedelta

from test_api import Base

ANO = date.today().year
MAT_LUCAS, MAT_ANA = f"{ANO}0001", f"{ANO}0004"


def semana(ref: date | None = None):
    ref = ref or date.today()
    seg = ref - timedelta(days=ref.weekday())
    return seg, seg + timedelta(days=6)


_usados = iter(range(0, 40))


def dia_livre() -> str:
    """Um dia útil de novembro/ANO (a partir do dia 17, depois dos feriados fixos), diferente a cada chamada."""
    d, n = date(ANO, 11, 17), next(_usados)
    while True:
        if d.weekday() < 5:
            if n == 0:
                return d.isoformat()
            n -= 1
        d += timedelta(days=1)


class AgBase(Base):
    def turma_td(self, h, turma="8º Ano B", disciplina="Matemática"):
        for t in self.c.get("/api/catalogo/turma-disciplinas", headers=h).get_json():
            if t["turma"] == turma and t["disciplina"] == disciplina:
                return t
        self.fail("turma/disciplina não encontrada")

    def agenda(self, h, ini, fim, **q):
        qs = "".join(f"&{k}={v}" for k, v in q.items())
        r = self.c.get(f"/api/agenda?inicio={ini}&fim={fim}{qs}", headers=h)
        self.assertEqual(r.status_code, 200, r.get_json())
        return r.get_json()["itens"]

    def provas(self, h, **q):
        qs = "&".join(f"{k}={v}" for k, v in q.items())
        r = self.c.get(f"/api/agenda/provas?{qs}", headers=h)
        self.assertEqual(r.status_code, 200, r.get_json())
        return r.get_json()

    def notificacoes(self, h):
        return self.c.get("/api/notificacoes?limite=200", headers=h).get_json()["itens"]

    def nova_avaliacao(self, h, titulo, data, tipo="PROVA", turma="8º Ano B", disciplina="Matemática", bimestre=3):
        return self.c.post("/api/avaliacoes", headers=h, json={
            "titulo": titulo, "tipo": tipo, "bimestre": bimestre, "peso": 1, "dataAvaliacao": data,
            "idTurmaDisciplina": self.turma_td(h, turma, disciplina)["id"]})

    def novo_evento(self, h, titulo, data, **extra):
        corpo = {"titulo": titulo, "tipo": "EVENTO", "publico": "TODOS", "data": data, **extra}
        return self.c.post("/api/eventos", headers=h, json=corpo)


# ---------------------------------------------------------------------------
class TestAgenda(AgBase):
    def test_agenda_do_aluno_so_tem_a_propria_turma(self):
        lucas = self.login(MAT_LUCAS)
        ini, fim = semana()
        itens = self.agenda(lucas, ini, fim)
        self.assertTrue(itens)
        for i in itens:
            if i["tipo"] != "EVENTO":
                self.assertEqual(i["turma"], "8º Ano B", i)
        # 5 disciplinas x dias úteis da semana que não são feriado/recesso
        bloqueados = {i["inicio"][:10] for i in itens if i["tipo"] == "EVENTO" and i["categoria"] in ("FERIADO", "RECESSO")}
        for i in itens:
            if i["tipo"] == "EVENTO" and i["categoria"] == "RECESSO" and i.get("fim"):
                d = date.fromisoformat(i["inicio"][:10])
                while d <= date.fromisoformat(i["fim"][:10]):
                    bloqueados.add(d.isoformat())
                    d += timedelta(days=1)
        uteis = [ini + timedelta(days=k) for k in range(5) if (ini + timedelta(days=k)).isoformat() not in bloqueados]
        self.assertEqual(len([i for i in itens if i["tipo"] == "AULA"]), 5 * len(uteis))

    def test_agenda_junta_atividades_provas_e_eventos_com_link(self):
        lucas = self.login(MAT_LUCAS)
        hoje = date.today()
        itens = self.agenda(lucas, hoje, hoje + timedelta(days=30), tipos="ATIVIDADE,AVALIACAO,EVENTO")
        self.assertEqual({i["tipo"] for i in itens} - {"EVENTO"}, {"ATIVIDADE", "AVALIACAO"})
        for i in itens:
            self.assertTrue(i["link"].startswith("/"))
        trig = next(i for i in itens if i["titulo"] == "Exercícios de Trigonometria")
        self.assertEqual(trig["status"], "PENDENTE")
        # integração com Notas: avaliação já corrigida mostra a nota do próprio aluno
        passadas = self.agenda(lucas, hoje - timedelta(days=30), hoje - timedelta(days=1), tipos="AVALIACAO")
        self.assertTrue(any(i["nota"] is not None for i in passadas))

    def test_aluno_entrega_atividade_e_agenda_reflete(self):
        lucas = self.login(MAT_LUCAS)
        hoje = date.today()
        ativ = next(a for a in self.c.get("/api/atividades", headers=lucas).get_json() if a["titulo"] == "Resumo: Revolução Industrial")
        r = self.c.put(f"/api/atividades/{ativ['id']}/entrega", headers=lucas, json={"status": "ENTREGUE"})
        self.assertIn(r.status_code, (200, 204), r.get_data(as_text=True))
        itens = self.agenda(lucas, hoje, hoje + timedelta(days=10), tipos="ATIVIDADE")
        self.assertEqual(next(i for i in itens if i["refId"] == ativ["id"])["status"], "ENTREGUE")
        # e some dos próximos compromissos
        prox = self.c.get("/api/agenda/proximos?dias=14&limite=30", headers=lucas).get_json()
        self.assertFalse(any(i["titulo"] == "Resumo: Revolução Industrial" for i in prox))

    def test_responsavel_ve_a_turma_de_cada_filho(self):
        maria = self.login("maria@eduvance.com")
        hoje = date.today()
        itens = self.agenda(maria, hoje, hoje + timedelta(days=30), tipos="ATIVIDADE,AVALIACAO")
        self.assertEqual({i["turma"] for i in itens}, {"8º Ano B", "5º Ano A"})
        self.assertEqual({i["aluno"] for i in itens}, {"Lucas Silva", "Ana Silva"})   # rótulo do aluno quando há mais de um
        lucas_id = self.c.get("/api/auth/me", headers=self.login(MAT_LUCAS)).get_json()["usuario"]["id"]
        so_lucas = self.agenda(maria, hoje, hoje + timedelta(days=30), tipos="ATIVIDADE,AVALIACAO", idAluno=lucas_id)
        self.assertEqual({i["turma"] for i in so_lucas}, {"8º Ano B"})
        # aluno que não é filho dela
        outro = self.c.get("/api/auth/me", headers=self.login(f"{ANO}0002")).get_json()["usuario"]["id"]
        r = self.c.get(f"/api/agenda?inicio={hoje}&fim={hoje}&idAluno={outro}", headers=maria)
        self.assertEqual(r.status_code, 403)

    def test_professor_e_coordenacao(self):
        hoje = date.today()
        ricardo = self.login("ricardo@eduvance.com")
        paula = self.login("paula@eduvance.com")
        meus = self.agenda(ricardo, hoje, hoje + timedelta(days=30), tipos="AVALIACAO")
        todos = self.agenda(paula, hoje, hoje + timedelta(days=30), tipos="AVALIACAO")
        self.assertTrue(meus)
        self.assertGreaterEqual(len(todos), len(meus))
        self.assertTrue(all(i["disciplina"] == "Matemática" for i in meus))
        so_8b = self.agenda(paula, hoje, hoje + timedelta(days=30), tipos="AVALIACAO", idTurma=self.turma_td(paula)["idTurma"])
        self.assertTrue(so_8b and all(i["turma"] == "8º Ano B" for i in so_8b))

    def test_validacoes_da_consulta(self):
        h = self.login(MAT_LUCAS)
        hoje = date.today()
        self.assertEqual(self.c.get("/api/agenda?inicio=ontem&fim=hoje", headers=h).status_code, 400)
        self.assertEqual(self.c.get(f"/api/agenda?inicio={hoje}&fim={hoje - timedelta(days=1)}", headers=h).status_code, 400)
        self.assertEqual(self.c.get(f"/api/agenda?inicio={hoje}&fim={hoje + timedelta(days=200)}", headers=h).status_code, 400)
        self.assertEqual(self.c.get(f"/api/agenda?inicio={hoje}&fim={hoje}&tipos=XYZ", headers=h).status_code, 400)
        self.assertEqual(self.c.get("/api/agenda").status_code, 401)

    def test_dashboard_traz_compromissos_para_todos_os_perfis(self):
        for ident, senha in [(MAT_LUCAS, "senha123"), ("maria@eduvance.com", "senha123"), ("ricardo@eduvance.com", "senha123"),
                             ("paula@eduvance.com", "senha123"), ("admin@eduvance.com", "admin123")]:
            d = self.c.get("/api/dashboard", headers=self.login(ident, senha)).get_json()
            self.assertIn("compromissos", d, ident)
            self.assertIn("semAulaHoje", d)
        lucas = self.c.get("/api/dashboard", headers=self.login(MAT_LUCAS)).get_json()
        self.assertTrue(lucas["compromissos"])
        self.assertLessEqual(len(lucas["compromissos"]), 6)
        self.assertTrue(all(c["link"].startswith("/") and c["tipo"] != "AULA" for c in lucas["compromissos"]))
        self.assertEqual([c["inicio"][:10] for c in lucas["compromissos"]], sorted(c["inicio"][:10] for c in lucas["compromissos"]))


# ---------------------------------------------------------------------------
class TestCalendarioDeProvas(AgBase):
    def test_aluno_ve_proximas_provas_da_propria_turma(self):
        lucas = self.login(MAT_LUCAS)
        provas = self.provas(lucas)
        self.assertTrue(provas)
        self.assertTrue(all(p["turma"] == "8º Ano B" and p["diasRestantes"] >= 0 for p in provas))
        self.assertEqual([p["data"] for p in provas], sorted(p["data"] for p in provas))
        self.assertTrue(all(p["podeRemarcar"] is False for p in provas))   # aluno não remarca
        passadas = self.provas(lucas, periodo="passadas")
        self.assertTrue(passadas and all(p["diasRestantes"] < 0 for p in passadas))
        self.assertTrue(all(p["bimestre"] == 1 for p in self.provas(lucas, periodo="todas", bimestre=1)))
        self.assertEqual(self.c.get("/api/agenda/provas?periodo=xx", headers=lucas).status_code, 400)
        self.assertEqual(self.c.get("/api/agenda/provas?bimestre=9", headers=lucas).status_code, 400)

    def test_responsavel_com_dois_filhos_em_turmas_diferentes(self):
        provas = self.provas(self.login("maria@eduvance.com"), periodo="todas")
        self.assertEqual({p["turma"] for p in provas}, {"8º Ano B", "5º Ano A"})
        self.assertTrue(all(p["aluno"] for p in provas))

    def test_remarcar_avisa_alunos_e_responsaveis_e_persiste(self):
        ricardo = self.login("ricardo@eduvance.com")
        nova = dia_livre()
        r = self.nova_avaliacao(ricardo, "Prova de Equações", dia_livre())
        self.assertEqual(r.status_code, 201, r.get_json())
        av = r.get_json()
        self.assertGreater(av["notificados"], 28)   # 28 alunos + responsáveis
        r = self.c.patch(f"/api/avaliacoes/{av['id']}/data", headers=ricardo, json={"dataAvaliacao": nova, "motivo": "Feriado municipal"})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(r.get_json()["dataAvaliacao"], nova)
        self.assertGreater(r.get_json()["notificados"], 28)
        for ident in (MAT_LUCAS, "maria@eduvance.com"):
            n = [x for x in self.notificacoes(self.login(ident)) if "remarcada" in x["titulo"] and "Equações" in x["titulo"]]
            self.assertTrue(n, ident)
            self.assertEqual(n[0]["tipo"], "AGENDA")
            self.assertEqual(n[0]["link"], "/provas")
            self.assertIn("Feriado municipal", n[0]["mensagem"])
        # o professor autor não é notificado do que ele mesmo fez
        self.assertFalse(any("Equações" in x["titulo"] for x in self.notificacoes(ricardo)))
        # persistência: aparece na nova data no calendário do aluno
        provas = self.provas(self.login(MAT_LUCAS), periodo="todas")
        self.assertEqual(next(p for p in provas if p["id"] == av["id"])["data"], nova)
        # quem leciona vê o botão de remarcar
        self.assertTrue(next(p for p in self.provas(ricardo, periodo="todas") if p["id"] == av["id"])["podeRemarcar"])

    def test_regras_de_data_da_avaliacao(self):
        ricardo = self.login("ricardo@eduvance.com")
        sabado = next(date(ANO, 11, 21) + timedelta(days=k) for k in range(7) if (date(ANO, 11, 21) + timedelta(days=k)).weekday() == 5)
        r = self.nova_avaliacao(ricardo, "Prova no sábado", sabado.isoformat())
        self.assertEqual(r.status_code, 400)
        self.assertIn("fim de semana", r.get_json()["detalhes"][0]["mensagem"])
        # feriado do calendário escolar bloqueia a data (integração Calendário -> Avaliações)
        r = self.nova_avaliacao(ricardo, "Prova no feriado", f"{ANO}-11-02") if date(ANO, 11, 2).weekday() < 5 else None
        if r is not None:
            self.assertEqual(r.status_code, 400)
            self.assertIn("Finados", r.get_json()["detalhes"][0]["mensagem"])
        # no máximo 2 provas por dia na mesma turma
        d = dia_livre()
        self.assertEqual(self.nova_avaliacao(ricardo, "Prova A", d, disciplina="Matemática").status_code, 201)
        marcelo = self.login("marcelo@eduvance.com")
        self.assertEqual(self.nova_avaliacao(marcelo, "Prova B", d, disciplina="Geografia").status_code, 201)
        paula = self.login("paula@eduvance.com")
        r = self.nova_avaliacao(paula, "Prova C", d, disciplina="História")
        self.assertEqual(r.status_code, 409, r.get_json())
        self.assertIn("2 provas", r.get_json()["erro"])
        # teste/trabalho não entram no limite
        self.assertEqual(self.nova_avaliacao(paula, "Teste D", d, tipo="TESTE", disciplina="História").status_code, 201)

    def test_editar_sem_mudar_a_data_nao_reaplica_regras(self):
        """Regressão: avaliações antigas (inclusive em fim de semana/feriado) continuam editáveis (título/peso)."""
        paula = self.login("paula@eduvance.com")
        antigas = [a for a in self.c.get("/api/avaliacoes", headers=paula).get_json() if a["titulo"] == "Prova B2" and a["turma"] == "8º Ano B"]
        a = antigas[0]
        r = self.c.put(f"/api/avaliacoes/{a['id']}", headers=paula, json={
            "titulo": a["titulo"], "tipo": a["tipo"], "bimestre": a["bimestre"], "dataAvaliacao": a["dataAvaliacao"],
            "peso": 1.5, "idTurmaDisciplina": a["idTurmaDisciplina"]})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(r.get_json()["notificados"], 0)   # data não mudou: ninguém é avisado

    def test_remarcar_rbac_e_regras(self):
        ricardo = self.login("ricardo@eduvance.com")
        av = self.nova_avaliacao(ricardo, "Prova de Funções", dia_livre()).get_json()
        url = f"/api/avaliacoes/{av['id']}/data"
        # aluno e professor de outra disciplina
        self.assertEqual(self.c.patch(url, headers=self.login(MAT_LUCAS), json={"dataAvaliacao": dia_livre()}).status_code, 403)
        self.assertEqual(self.c.patch(url, headers=self.login("marcelo@eduvance.com"), json={"dataAvaliacao": dia_livre()}).status_code, 403)
        self.assertEqual(self.c.patch("/api/avaliacoes/99999/data", headers=ricardo, json={"dataAvaliacao": dia_livre()}).status_code, 404)
        # validações
        self.assertEqual(self.c.patch(url, headers=ricardo, json={}).status_code, 400)
        self.assertEqual(self.c.patch(url, headers=ricardo, json={"dataAvaliacao": av["dataAvaliacao"]}).status_code, 400)   # mesma data
        self.assertEqual(self.c.patch(url, headers=ricardo, json={"dataAvaliacao": f"{ANO + 1}-03-10"}).status_code, 400)       # outro ano letivo
        # a coordenação pode remarcar qualquer uma
        self.assertEqual(self.c.patch(url, headers=self.login("paula@eduvance.com"), json={"dataAvaliacao": dia_livre()}).status_code, 200)

    def test_nao_remarca_avaliacao_com_notas(self):
        ricardo = self.login("ricardo@eduvance.com")
        td = self.turma_td(ricardo)["id"]
        passada = next(a for a in self.c.get(f"/api/avaliacoes?idTurmaDisciplina={td}", headers=ricardo).get_json() if a["notasLancadas"])
        r = self.c.patch(f"/api/avaliacoes/{passada['id']}/data", headers=ricardo, json={"dataAvaliacao": dia_livre()})
        self.assertEqual(r.status_code, 409)
        self.assertIn("notas lançadas", r.get_json()["erro"])
        marcada = next(p for p in self.provas(ricardo, periodo="passadas") if p["id"] == passada["id"])
        self.assertFalse(marcada["podeRemarcar"])

    def test_lancar_notas_nao_escolhe_avaliacao_futura(self):
        """Regressão da integração Calendário × Notas: a tela de lançamento abre na última avaliação já realizada."""
        ricardo = self.login("ricardo@eduvance.com")
        td = self.turma_td(ricardo)["id"]
        d = self.c.get(f"/api/notas/turma-disciplina/{td}", headers=ricardo).get_json()
        self.assertLessEqual(d["avaliacao"]["data"], date.today().isoformat())
        self.assertEqual(d["alunos"][0]["valor"], 7.5)


# ---------------------------------------------------------------------------
class TestEventos(AgBase):
    def test_crud_completo_e_persistencia(self):
        paula = self.login("paula@eduvance.com")
        r = self.novo_evento(paula, "Feira de Profissões", dia_livre(), hora="09:00", horaFim="12:00", dataFim=None,
                             descricao="Palestras no auditório.", tipo="EVENTO")
        self.assertEqual(r.status_code, 201, r.get_json())
        ev = r.get_json()
        self.assertGreater(ev["notificados"], 100)       # público TODOS, exceto a coordenadora
        self.assertEqual((ev["hora"], ev["horaFim"], ev["diaInteiro"]), ("09:00", "12:00", False))
        self.assertEqual(self.c.get(f"/api/eventos/{ev['id']}", headers=self.login(MAT_LUCAS)).get_json()["titulo"], "Feira de Profissões")
        # editar: mudar de data remarca e avisa
        nova = dia_livre()
        r = self.c.put(f"/api/eventos/{ev['id']}", headers=paula, json={"titulo": "Feira de Profissões", "tipo": "EVENTO", "publico": "TODOS", "data": nova, "hora": "14:00"})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertGreater(r.get_json()["notificados"], 100)
        self.assertTrue(any("remarcado" in n["titulo"] for n in self.notificacoes(self.login(MAT_LUCAS))))
        self.assertEqual(self.c.get(f"/api/eventos/{ev['id']}", headers=self.login(MAT_LUCAS)).get_json()["data"], nova)
        # excluir avisa o cancelamento e remove
        self.assertEqual(self.c.delete(f"/api/eventos/{ev['id']}", headers=paula).status_code, 204)
        self.assertEqual(self.c.get(f"/api/eventos/{ev['id']}", headers=paula).status_code, 404)
        self.assertTrue(any("cancelado" in n["titulo"] for n in self.notificacoes(self.login(MAT_LUCAS))))
        self.assertEqual(self.c.delete(f"/api/eventos/{ev['id']}", headers=paula).status_code, 404)

    def test_validacoes(self):
        paula = self.login("paula@eduvance.com")
        d = dia_livre()
        def campos(**corpo):
            r = self.c.post("/api/eventos", headers=paula, json=corpo)
            self.assertEqual(r.status_code, 400, r.get_json())
            return {x["campo"] for x in r.get_json()["detalhes"]}
        self.assertEqual(campos(), {"titulo", "tipo", "data"})
        self.assertIn("titulo", campos(titulo="ab", tipo="EVENTO", data=d))
        self.assertIn("tipo", campos(titulo="Evento válido", tipo="FESTA", data=d))
        self.assertIn("data", campos(titulo="Evento válido", tipo="EVENTO", data="20/11/2026"))
        self.assertIn("hora", campos(titulo="Evento válido", tipo="EVENTO", data=d, hora="25:99"))
        self.assertIn("idTurma", campos(titulo="Evento válido", tipo="EVENTO", data=d, publico="TURMA"))
        self.assertIn("publico", campos(titulo="Feriado local", tipo="FERIADO", data=d, publico="ALUNOS"))
        self.assertIn("dataFim", campos(titulo="Evento válido", tipo="EVENTO", data=d, dataFim="2020-01-01"))
        self.assertIn("horaFim", campos(titulo="Evento válido", tipo="EVENTO", data=d, hora="10:00", horaFim="09:00", dataFim=d))
        r = self.novo_evento(paula, "Evento válido", d, publico="TURMA", idTurma=99999)
        self.assertEqual(r.status_code, 400)

    def test_rbac(self):
        d = dia_livre()
        for ident in (MAT_LUCAS, "maria@eduvance.com", "ricardo@eduvance.com"):
            self.assertEqual(self.novo_evento(self.login(ident), "Evento proibido", d).status_code, 403, ident)
        self.assertEqual(self.novo_evento(self.admin(), "Evento do admin", d).status_code, 201)
        ev = self.novo_evento(self.login("paula@eduvance.com"), "Evento da Paula", d, hora="10:00").get_json()
        for ident in (MAT_LUCAS, "ricardo@eduvance.com"):
            h = self.login(ident)
            self.assertEqual(self.c.put(f"/api/eventos/{ev['id']}", headers=h, json={"titulo": "Alterado", "tipo": "EVENTO", "data": d}).status_code, 403)
            self.assertEqual(self.c.delete(f"/api/eventos/{ev['id']}", headers=h).status_code, 403)
        self.assertEqual(self.c.get("/api/eventos").status_code, 401)

    def test_visibilidade_por_publico(self):
        paula = self.login("paula@eduvance.com")
        t8b = self.turma_td(paula)["idTurma"]
        ev = self.novo_evento(paula, "Passeio do 8º B", dia_livre(), publico="TURMA", idTurma=t8b).get_json()
        ver = lambda ident: self.c.get(f"/api/eventos/{ev['id']}", headers=self.login(ident)).status_code
        self.assertEqual(ver(MAT_LUCAS), 200)                 # aluno da turma
        self.assertEqual(ver("maria@eduvance.com"), 200)      # responsável de aluno da turma
        self.assertEqual(ver("ricardo@eduvance.com"), 200)    # professor que leciona na turma
        self.assertEqual(ver(MAT_ANA), 404)                   # aluna de outra turma
        # notificação só para quem é do público
        self.assertTrue(any("Passeio do 8º B" in n["mensagem"] for n in self.notificacoes(self.login(MAT_LUCAS))))
        self.assertFalse(any("Passeio do 8º B" in n["mensagem"] for n in self.notificacoes(self.login(MAT_ANA))))
        prof = self.novo_evento(paula, "Formação docente", dia_livre(), publico="PROFESSORES").get_json()
        self.assertEqual(self.c.get(f"/api/eventos/{prof['id']}", headers=self.login(MAT_LUCAS)).status_code, 404)
        self.assertEqual(self.c.get(f"/api/eventos/{prof['id']}", headers=self.login("ricardo@eduvance.com")).status_code, 200)
        # o público não muda depois de cadastrado
        r = self.c.put(f"/api/eventos/{prof['id']}", headers=paula, json={"titulo": "Formação docente", "tipo": "EVENTO", "publico": "ALUNOS", "data": dia_livre()})
        self.assertEqual(r.status_code, 409)

    def test_evento_repetido(self):
        paula = self.login("paula@eduvance.com")
        d = dia_livre()
        self.assertEqual(self.novo_evento(paula, "Sarau literário", d, hora="19:00").status_code, 201)
        self.assertEqual(self.novo_evento(paula, "sarau literário", d, hora="19:00").status_code, 409)
        self.assertEqual(self.novo_evento(paula, "Sarau literário", d, hora="20:00").status_code, 201)

    def test_feriado_suspende_aulas_e_nao_cobre_dia_com_prova(self):
        paula = self.login("paula@eduvance.com")
        lucas = self.login(MAT_LUCAS)
        # um dia com prova marcada não pode virar feriado/recesso (Avaliações -> Calendário)
        d_prova = dia_livre()
        self.assertEqual(self.nova_avaliacao(self.login("ricardo@eduvance.com"), "Prova antes do feriado", d_prova).status_code, 201)
        r = self.novo_evento(paula, "Recesso inesperado", d_prova, tipo="RECESSO")
        self.assertEqual(r.status_code, 409, r.get_json())
        self.assertIn("avaliação", r.get_json()["erro"])
        # dia livre: vira feriado e as aulas somem da agenda (Calendário -> Agenda)
        d = dia_livre()
        antes = [i for i in self.agenda(lucas, d, d, tipos="AULA")]
        self.assertEqual(len(antes), 5)
        r = self.novo_evento(paula, "Feriado municipal", d, tipo="FERIADO")
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertTrue(r.get_json()["diaInteiro"])
        self.assertEqual(self.agenda(lucas, d, d, tipos="AULA"), [])
        self.assertEqual([i["categoria"] for i in self.agenda(lucas, d, d, tipos="EVENTO")], ["FERIADO"])
        # e não dá para marcar prova nesse dia
        r = self.nova_avaliacao(self.login("ricardo@eduvance.com"), "Prova no feriado municipal", d)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Feriado municipal", r.get_json()["detalhes"][0]["mensagem"])

    def test_recesso_de_varios_dias(self):
        paula = self.login("paula@eduvance.com")
        lucas = self.login(MAT_LUCAS)
        ini = dia_livre()
        fim = (date.fromisoformat(ini) + timedelta(days=2)).isoformat()
        for _ in range(3):   # consome os dias seguintes para não colidir com os outros testes
            dia_livre()
        r = self.novo_evento(paula, "Semana de planejamento", ini, dataFim=fim, tipo="RECESSO")
        self.assertEqual(r.status_code, 201, r.get_json())
        itens = self.agenda(lucas, ini, fim, tipos="EVENTO")
        self.assertEqual(itens[0]["fim"][:10], fim)
        self.assertEqual([i for i in self.agenda(lucas, ini, fim, tipos="AULA") if i["inicio"][:10] in
                          {(date.fromisoformat(ini) + timedelta(days=k)).isoformat() for k in range(3)}], [])

    def test_feriado_suspende_aulas_do_dia_no_servico(self):
        """Mesma regra do dashboard, sem depender do dia da semana: aulas_do_dia numa segunda-feira com feriado."""
        from datetime import datetime
        from app.services import academico as ac
        seg = next(date(ANO, 11, 17) + timedelta(days=k) for k in range(7) if (date(ANO, 11, 17) + timedelta(days=k)).weekday() == 0)
        agora = datetime(seg.year, seg.month, seg.day, 8, 30)
        with self.app.app_context():
            self.assertTrue(ac.aulas_do_dia(agora=agora))
            self.novo_evento(self.login("paula@eduvance.com"), "Feriado da segunda", seg.isoformat(), tipo="FERIADO")
            self.assertEqual(ac.aulas_do_dia(agora=agora), [])

    def test_feriado_de_hoje_zera_a_agenda_do_dashboard(self):
        paula = self.login("paula@eduvance.com")
        hoje = date.today().isoformat()
        if date.today().weekday() >= 5 or self.c.get(f"/api/agenda?inicio={hoje}&fim={hoje}&tipos=AVALIACAO", headers=paula).get_json()["itens"]:
            self.skipTest("hoje é fim de semana ou tem avaliação marcada")
        lucas = self.login(MAT_LUCAS)
        self.assertTrue(self.c.get("/api/dashboard", headers=lucas).get_json()["agendaHoje"])
        self.assertEqual(self.novo_evento(paula, "Feriado de teste", hoje, tipo="FERIADO").status_code, 201)
        d = self.c.get("/api/dashboard", headers=lucas).get_json()
        self.assertEqual(d["agendaHoje"], [])
        self.assertEqual(d["semAulaHoje"], "Feriado de teste")


# ---------------------------------------------------------------------------
class TestLembretes(AgBase):
    def test_lembretes_de_atividade_pendente_sem_repeticao(self):
        lucas = self.login(MAT_LUCAS)
        def lembretes():
            return [n for n in self.notificacoes(lucas) if n["titulo"].startswith("Lembrete")]
        self.assertEqual(self.c.get("/api/notificacoes/contagem", headers=lucas).status_code, 200)
        primeira = lembretes()
        self.assertTrue(primeira, "esperava lembretes das atividades que vencem hoje/amanhã")
        self.assertTrue(all(n["tipo"] == "AGENDA" for n in primeira))
        self.assertTrue(any("Trigonometria" in n["mensagem"] for n in primeira) or any("Redação" in n["mensagem"] for n in primeira))
        for _ in range(3):
            self.c.get("/api/notificacoes/contagem", headers=lucas)
        self.assertEqual(len(lembretes()), len(primeira))   # idempotente

    def test_lembrete_some_quando_a_atividade_e_entregue(self):
        ana = self.login(MAT_ANA)
        self.c.get("/api/notificacoes/contagem", headers=ana)
        antes = len([n for n in self.notificacoes(ana) if n["titulo"].startswith("Lembrete")])
        # entrega a atividade que vence em ~2 dias: nenhum lembrete novo, e a existente permanece como histórico
        for a in self.c.get("/api/atividades", headers=ana).get_json():
            self.c.put(f"/api/atividades/{a['id']}/entrega", headers=ana, json={"status": "ENTREGUE"})
        self.c.get("/api/notificacoes/contagem", headers=ana)
        self.assertEqual(len([n for n in self.notificacoes(ana) if n["titulo"].startswith("Lembrete")]), antes)

    def test_professor_nao_recebe_lembretes(self):
        h = self.login("ricardo@eduvance.com")
        self.c.get("/api/notificacoes/contagem", headers=h)
        self.assertFalse([n for n in self.notificacoes(h) if n["titulo"].startswith("Lembrete")])


# ---------------------------------------------------------------------------
class TestPreferencias(AgBase):
    def test_padrao_e_atualizacao_persistente(self):
        h = self.login(MAT_LUCAS)
        self.assertEqual(self.c.get("/api/preferencias", headers=h).get_json(), {"fonte": 100, "tema": "auto", "salvo": False})
        r = self.c.put("/api/preferencias", headers=h, json={"fonte": 130})
        self.assertEqual(r.get_json(), {"fonte": 130, "tema": "auto", "salvo": True})
        r = self.c.put("/api/preferencias", headers=h, json={"tema": "escuro"})
        self.assertEqual(r.get_json(), {"fonte": 130, "tema": "escuro", "salvo": True})
        # persiste em um novo login (outro dispositivo)
        self.assertEqual(self.c.get("/api/preferencias", headers=self.login(MAT_LUCAS)).get_json(), {"fonte": 130, "tema": "escuro", "salvo": True})
        # restaurar o padrão
        self.assertEqual(self.c.delete("/api/preferencias", headers=h).get_json(), {"fonte": 100, "tema": "auto", "salvo": False})
        self.assertEqual(self.c.get("/api/preferencias", headers=h).get_json(), {"fonte": 100, "tema": "auto", "salvo": False})

    def test_validacoes_e_isolamento(self):
        h = self.login(MAT_LUCAS)
        for corpo in ({"fonte": 77}, {"fonte": "grande"}, {"fonte": True}, {"tema": "roxo"}):
            self.assertEqual(self.c.put("/api/preferencias", headers=h, json=corpo).status_code, 400, corpo)
        self.assertEqual(self.c.put("/api/preferencias", headers=h, data="x", content_type="application/json").status_code, 400)
        self.c.put("/api/preferencias", headers=h, json={"fonte": 150})
        self.assertEqual(self.c.get("/api/preferencias", headers=self.login(MAT_ANA)).get_json()["fonte"], 100)   # cada um tem a sua
        self.assertEqual(self.c.get("/api/preferencias").status_code, 401)


if __name__ == "__main__":
    unittest.main()
