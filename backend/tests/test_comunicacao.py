"""Testes do módulo Comunicação Escolar (Sprint 05): comunicados, ocorrências e notificações.

    cd backend && python -m unittest discover -s tests -v
"""
import unittest
from datetime import date, timedelta

from test_api import Base, _dia_util

ANO = date.today().year
MAT_LUCAS = f"{ANO}0001"


class ComBase(Base):
    def turma_id(self, h, nome):
        for t in self.c.get("/api/catalogo/turma-disciplinas", headers=h).get_json():
            if t["turma"] == nome:
                return t["idTurma"]
        self.fail(f"turma {nome} não encontrada")

    def eu(self, h):
        return self.c.get("/api/auth/me", headers=h).get_json()["usuario"]["id"]

    def novo_comunicado(self, h, titulo, publico="TODOS", id_turma=None, mensagem="Mensagem de teste com tamanho suficiente."):
        corpo = {"titulo": titulo, "mensagem": mensagem, "publico": publico}
        if id_turma:
            corpo["idTurma"] = id_turma
        return self.c.post("/api/comunicados", headers=h, json=corpo)

    def nova_ocorrencia(self, h, id_aluno, titulo="Atraso na entrada", gravidade="LEVE", tipo="DISCIPLINAR", **extra):
        return self.c.post("/api/ocorrencias", headers=h, json={
            "idAluno": id_aluno, "titulo": titulo, "descricao": "Descrição detalhada da ocorrência em sala.",
            "tipo": tipo, "gravidade": gravidade, **extra})

    def notificacoes(self, h, **q):
        qs = "&".join(f"{k}={v}" for k, v in q.items())
        return self.c.get(f"/api/notificacoes?{qs}", headers=h).get_json()


class TestComunicados(ComBase):
    def test_ciclo_completo_leitura_e_persistencia(self):
        paula = self.login("paula@eduvance.com")
        lucas = self.login(MAT_LUCAS)
        antes = self.c.get("/api/comunicados/nao-lidos", headers=lucas).get_json()["total"]
        r = self.novo_comunicado(paula, "Mutirão de limpeza")
        self.assertEqual(r.status_code, 201, r.get_json())
        novo = r.get_json()
        self.assertGreater(novo["notificados"], 100)  # todos os usuários, exceto a autora
        self.assertTrue(novo["lido"])  # o autor não precisa "ler" o próprio aviso

        # aparece para o aluno como não lido e gera notificação
        self.assertEqual(self.c.get("/api/comunicados/nao-lidos", headers=lucas).get_json()["total"], antes + 1)
        item = next(c for c in self.c.get("/api/comunicados", headers=lucas).get_json() if c["id"] == novo["id"])
        self.assertFalse(item["lido"])
        self.assertTrue(any("Mutirão" in n["titulo"] for n in self.notificacoes(lucas)["itens"]))

        # marcar como lido é idempotente e persiste
        for _ in range(2):
            self.assertTrue(self.c.put(f"/api/comunicados/{novo['id']}/lido", headers=lucas).get_json()["lido"])
        self.assertEqual(self.c.get("/api/comunicados/nao-lidos", headers=lucas).get_json()["total"], antes)
        lidos_ids = [c["id"] for c in self.c.get("/api/comunicados?lido=nao", headers=lucas).get_json()]
        self.assertNotIn(novo["id"], lidos_ids)

        # quem publicou acompanha a leitura
        det = self.c.get(f"/api/comunicados/{novo['id']}", headers=paula).get_json()
        self.assertEqual(det["leitura"]["lidos"], 1)
        self.assertGreater(det["leitura"]["destinatarios"], 100)

        # edição e exclusão
        e = self.c.put(f"/api/comunicados/{novo['id']}", headers=paula, json={"titulo": "Mutirão de limpeza (atualizado)", "mensagem": "Novo horário: sábado às 8h."})
        self.assertEqual(e.status_code, 200)
        self.assertEqual(self.c.get(f"/api/comunicados/{novo['id']}", headers=paula).get_json()["titulo"], "Mutirão de limpeza (atualizado)")
        self.assertEqual(self.c.delete(f"/api/comunicados/{novo['id']}", headers=paula).status_code, 204)
        self.assertEqual(self.c.get(f"/api/comunicados/{novo['id']}", headers=paula).status_code, 404)

    def test_validacoes(self):
        paula = self.login("paula@eduvance.com")
        turma = self.turma_id(paula, "8º Ano B")
        r = self.c.post("/api/comunicados", headers=paula, json={"titulo": "ab", "mensagem": "curta", "publico": "ALIENS"})
        self.assertEqual(r.status_code, 400)
        campos = {d["campo"] for d in r.get_json()["detalhes"]}
        self.assertEqual(campos, {"titulo", "mensagem", "publico"})
        self.assertEqual(self.c.post("/api/comunicados", headers=paula, json={}).status_code, 400)
        self.assertEqual(self.c.post("/api/comunicados", headers=paula, data="não é json", content_type="application/json").status_code, 400)
        sem_turma = self.novo_comunicado(paula, "Aviso da turma", "TURMA")
        self.assertEqual(sem_turma.status_code, 400)
        self.assertEqual(sem_turma.get_json()["detalhes"][0]["campo"], "idTurma")
        self.assertEqual(self.novo_comunicado(paula, "Aviso geral", "TODOS", turma).status_code, 400)
        self.assertEqual(self.novo_comunicado(paula, "Turma fantasma", "TURMA", 99999).status_code, 400)
        longo = self.novo_comunicado(paula, "T" * 121)
        self.assertEqual(longo.status_code, 400)

    def test_comunicado_repetido_e_conflito(self):
        paula = self.login("paula@eduvance.com")
        self.assertEqual(self.novo_comunicado(paula, "Aviso único", "PROFESSORES").status_code, 201)
        r = self.novo_comunicado(paula, "aviso ÚNICO".replace("Ú", "ú"), "PROFESSORES")
        self.assertEqual(r.status_code, 409)
        self.assertIn("já foi publicado", r.get_json()["erro"])
        # o mesmo título para outro público é permitido
        self.assertEqual(self.novo_comunicado(paula, "Aviso único", "ALUNOS").status_code, 201)

    def test_permissoes_de_publicacao(self):
        roberta = self.login("roberta@eduvance.com")  # leciona só no 9º Ano A
        t9 = self.turma_id(roberta, "9º Ano A")
        t8b = self.turma_id(self.admin(), "8º Ano B")
        self.assertEqual(self.novo_comunicado(roberta, "Entrega da redação", "TURMA", t9).status_code, 201)
        self.assertEqual(self.novo_comunicado(roberta, "Aviso fora da turma", "TURMA", t8b).status_code, 403)
        self.assertEqual(self.novo_comunicado(roberta, "Aviso geral indevido", "TODOS").status_code, 403)
        for ident in (MAT_LUCAS, "maria@eduvance.com"):
            self.assertEqual(self.novo_comunicado(self.login(ident), "Tentativa indevida").status_code, 403)
        self.assertEqual(self.c.post("/api/comunicados", json={}).status_code, 401)

    def test_visibilidade_por_publico(self):
        paula = self.login("paula@eduvance.com")
        lucas, maria, ricardo = self.login(MAT_LUCAS), self.login("maria@eduvance.com"), self.login("ricardo@eduvance.com")
        t9 = self.turma_id(paula, "9º Ano A")
        t8b = self.turma_id(paula, "8º Ano B")
        so_resp = self.novo_comunicado(paula, "Somente responsáveis", "RESPONSAVEIS").get_json()["id"]
        so_prof = self.novo_comunicado(paula, "Somente professores", "PROFESSORES").get_json()["id"]
        so_9a = self.novo_comunicado(paula, "Somente 9º Ano A", "TURMA", t9).get_json()["id"]
        so_8b = self.novo_comunicado(paula, "Somente 8º Ano B", "TURMA", t8b).get_json()["id"]

        def ids(h):
            return {c["id"] for c in self.c.get("/api/comunicados", headers=h).get_json()}

        self.assertEqual({so_resp, so_prof, so_9a, so_8b} - ids(lucas), {so_resp, so_prof, so_9a})  # aluno do 8ºB só vê o da própria turma
        self.assertTrue({so_resp, so_8b} <= ids(maria))     # Lucas (8ºB) é filho dela
        self.assertFalse({so_prof, so_9a} & ids(maria))
        self.assertTrue({so_prof, so_9a, so_8b} <= ids(ricardo))   # leciona em ambas as turmas
        self.assertFalse(so_resp in ids(ricardo))
        self.assertTrue({so_resp, so_prof, so_9a, so_8b} <= ids(paula))
        # acesso direto a um comunicado que não é para o usuário
        self.assertEqual(self.c.get(f"/api/comunicados/{so_prof}", headers=lucas).status_code, 404)
        self.assertEqual(self.c.put(f"/api/comunicados/{so_prof}/lido", headers=lucas).status_code, 404)

    def test_edicao_exclusao_e_publico_imutavel(self):
        paula = self.login("paula@eduvance.com")
        ricardo = self.login("ricardo@eduvance.com")
        cid = self.novo_comunicado(paula, "Aviso da coordenação").get_json()["id"]
        corpo = {"titulo": "Alterado pelo professor", "mensagem": "Mensagem alterada indevidamente."}
        self.assertEqual(self.c.put(f"/api/comunicados/{cid}", headers=ricardo, json=corpo).status_code, 403)
        self.assertEqual(self.c.delete(f"/api/comunicados/{cid}", headers=ricardo).status_code, 403)
        troca = self.c.put(f"/api/comunicados/{cid}", headers=paula, json={**corpo, "publico": "ALUNOS"})
        self.assertEqual(troca.status_code, 400)
        self.assertEqual(troca.get_json()["detalhes"][0]["campo"], "publico")
        # o professor edita o que ele mesmo publicou
        t = self.turma_id(ricardo, "8º Ano A")
        meu = self.novo_comunicado(ricardo, "Aviso do professor", "TURMA", t).get_json()["id"]
        self.assertEqual(self.c.put(f"/api/comunicados/{meu}", headers=ricardo, json=corpo).status_code, 200)
        self.assertEqual(self.c.delete(f"/api/comunicados/{meu}", headers=ricardo).status_code, 204)


class TestOcorrencias(ComBase):
    def test_fluxo_registro_analise_resolucao(self):
        ricardo, paula = self.login("ricardo@eduvance.com"), self.login("paula@eduvance.com")
        maria, joao = self.login("maria@eduvance.com"), self.login("joao.silva@eduvance.com")
        lucas = self.eu(self.login(MAT_LUCAS))
        n_paula = self.notificacoes(paula)["naoLidas"]
        n_maria = self.notificacoes(maria)["naoLidas"]

        r = self.nova_ocorrencia(ricardo, lucas, "Discussão com colega", "GRAVE")
        self.assertEqual(r.status_code, 201, r.get_json())
        o = r.get_json()
        self.assertEqual((o["status"], o["professor"], o["gravidade"]), ("ABERTA", "Ricardo Ramos", "GRAVE"))
        self.assertTrue(o["podeEditar"])
        # coordenação e AMBOS os responsáveis são avisados (gravidade grave)
        self.assertEqual(self.notificacoes(paula)["naoLidas"], n_paula + 1)
        self.assertEqual(self.notificacoes(maria)["naoLidas"], n_maria + 1)
        self.assertTrue(any("Discussão" in n["mensagem"] for n in self.notificacoes(joao)["itens"]))
        self.assertTrue(self.notificacoes(paula)["itens"][0]["link"].startswith("/ocorrencias/"))

        # coordenação analisa
        n_prof = self.notificacoes(ricardo)["naoLidas"]
        a = self.c.put(f"/api/ocorrencias/{o['id']}/status", headers=paula, json={"status": "EM_ANALISE"})
        self.assertEqual(a.status_code, 200, a.get_json())
        self.assertFalse(self.c.get(f"/api/ocorrencias/{o['id']}", headers=ricardo).get_json()["podeEditar"])  # professor só edita enquanto ABERTA
        # resolver exige parecer
        sem = self.c.put(f"/api/ocorrencias/{o['id']}/status", headers=paula, json={"status": "RESOLVIDA"})
        self.assertEqual(sem.status_code, 400)
        self.assertEqual(sem.get_json()["detalhes"][0]["campo"], "parecer")
        curto = self.c.put(f"/api/ocorrencias/{o['id']}/status", headers=paula, json={"status": "RESOLVIDA", "parecer": "ok"})
        self.assertEqual(curto.status_code, 400)
        ok = self.c.put(f"/api/ocorrencias/{o['id']}/status", headers=paula, json={"status": "RESOLVIDA", "parecer": "Conversa com os alunos e os responsáveis."})
        self.assertEqual(ok.status_code, 200)
        fin = ok.get_json()
        self.assertEqual(fin["status"], "RESOLVIDA")
        self.assertEqual(fin["parecer"], "Conversa com os alunos e os responsáveis.")
        self.assertIsNotNone(fin["resolvidaEm"])
        self.assertEqual([h["statusNovo"] for h in fin["historico"]], ["ABERTA", "EM_ANALISE", "RESOLVIDA"])
        self.assertEqual(self.notificacoes(ricardo)["naoLidas"], n_prof + 2)  # em análise + resolvida
        # resolvida é imutável e a situação nunca retrocede
        for corpo in ({"status": "EM_ANALISE"}, {"status": "ABERTA"}, {"status": "RESOLVIDA", "parecer": "Parecer repetido aqui."}):
            self.assertEqual(self.c.put(f"/api/ocorrencias/{o['id']}/status", headers=paula, json=corpo).status_code, 409)
        self.assertEqual(self.c.put(f"/api/ocorrencias/{o['id']}", headers=paula, json={"titulo": "Outro título", "descricao": "Outra descrição qualquer.", "tipo": "DISCIPLINAR"}).status_code, 409)
        # persistência: nova leitura traz os mesmos dados
        again = self.c.get(f"/api/ocorrencias/{o['id']}", headers=maria).get_json()
        self.assertEqual((again["status"], len(again["historico"])), ("RESOLVIDA", 3))

    def test_validacoes(self):
        ricardo = self.login("ricardo@eduvance.com")
        lucas = self.eu(self.login(MAT_LUCAS))
        r = self.c.post("/api/ocorrencias", headers=ricardo, json={"idAluno": lucas, "titulo": "x", "descricao": "curta", "tipo": "OUTRO", "gravidade": "ENORME"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual({d["campo"] for d in r.get_json()["detalhes"]}, {"titulo", "descricao", "tipo", "gravidade"})
        self.assertEqual(self.c.post("/api/ocorrencias", headers=ricardo, json={}).status_code, 400)
        elogio = self.nova_ocorrencia(ricardo, lucas, "Excelente participação", "GRAVE", "ELOGIO")
        self.assertEqual(elogio.status_code, 400)
        self.assertEqual(elogio.get_json()["detalhes"][0]["campo"], "gravidade")
        futura = self.nova_ocorrencia(ricardo, lucas, "Fato no futuro", dataOcorrencia=str(date.today() + timedelta(days=2)))
        self.assertEqual(futura.status_code, 400)
        self.assertEqual(futura.get_json()["detalhes"][0]["campo"], "dataOcorrencia")
        self.assertEqual(self.nova_ocorrencia(ricardo, 99999, "Aluno inexistente").status_code, 400)

    def test_duplicidade_no_mesmo_dia(self):
        ricardo = self.login("ricardo@eduvance.com")
        lucas = self.eu(self.login(MAT_LUCAS))
        self.assertEqual(self.nova_ocorrencia(ricardo, lucas, "Sem material").status_code, 201)
        r = self.nova_ocorrencia(ricardo, lucas, "SEM MATERIAL")
        self.assertEqual(r.status_code, 409)
        self.assertIn("já foi registrada", r.get_json()["erro"])
        # outro dia (data informada) é permitido
        ontem = _dia_util(1)
        self.assertEqual(self.nova_ocorrencia(ricardo, lucas, "Sem material", dataOcorrencia=str(ontem)).status_code, 201)

    def test_permissoes_e_escopo(self):
        roberta = self.login("roberta@eduvance.com")  # só leciona no 9º Ano A
        ricardo, paula = self.login("ricardo@eduvance.com"), self.login("paula@eduvance.com")
        lucas_h, maria, thiago = self.login(MAT_LUCAS), self.login("maria@eduvance.com"), self.login(f"{ANO}0003")
        lucas, thiago_id = self.eu(lucas_h), self.eu(thiago)
        # professor só registra para alunos das próprias turmas
        self.assertEqual(self.nova_ocorrencia(roberta, lucas, "Fora da turma").status_code, 403)
        # aluno e responsável não registram nem mudam situação
        for h in (lucas_h, maria):
            self.assertEqual(self.nova_ocorrencia(h, lucas, "Tentativa indevida").status_code, 403)
        o = self.nova_ocorrencia(ricardo, thiago_id, "Falta de respeito", "MEDIA").get_json()
        self.assertEqual(self.c.put(f"/api/ocorrencias/{o['id']}/status", headers=ricardo, json={"status": "EM_ANALISE"}).status_code, 403)
        self.assertEqual(self.c.put(f"/api/ocorrencias/{o['id']}/status", headers=thiago, json={"status": "RESOLVIDA", "parecer": "Eu mesmo resolvi isto."}).status_code, 403)
        # cada perfil só enxerga o que lhe cabe
        def alunos(h):
            return {x["idAluno"] for x in self.c.get("/api/ocorrencias", headers=h).get_json()}
        self.assertEqual(alunos(lucas_h), {lucas})
        self.assertNotIn(thiago_id, alunos(lucas_h))
        self.assertIn(lucas, alunos(maria))
        self.assertNotIn(thiago_id, alunos(maria))
        self.assertIn(thiago_id, alunos(paula))
        self.assertEqual(self.c.get(f"/api/ocorrencias/{o['id']}", headers=lucas_h).status_code, 404)
        self.assertEqual(self.c.get(f"/api/ocorrencias/{o['id']}", headers=roberta).status_code, 404)
        self.assertEqual(self.c.get("/api/ocorrencias").status_code, 401)

    def test_edicao_exclusao_e_filtros(self):
        ricardo, ana, paula = self.login("ricardo@eduvance.com"), self.login("ana.guimaraes@eduvance.com"), self.login("paula@eduvance.com")
        lucas = self.eu(self.login(MAT_LUCAS))
        o = self.nova_ocorrencia(ricardo, lucas, "Uso de fone de ouvido").get_json()
        e = self.c.put(f"/api/ocorrencias/{o['id']}", headers=ricardo, json={"titulo": "Uso de fone de ouvido em prova", "descricao": "Usou fone durante a prova de matemática.", "tipo": "DISCIPLINAR", "gravidade": "MEDIA"})
        self.assertEqual(e.status_code, 200)
        self.assertEqual(e.get_json()["gravidade"], "MEDIA")
        # outro professor não vê nem altera
        self.assertEqual(self.c.put(f"/api/ocorrencias/{o['id']}", headers=ana, json={"titulo": "Invasão", "descricao": "Tentativa indevida de edição.", "tipo": "DISCIPLINAR"}).status_code, 404)
        self.assertEqual(self.c.delete(f"/api/ocorrencias/{o['id']}", headers=ana).status_code, 404)
        # em análise: o professor não pode mais excluir
        self.c.put(f"/api/ocorrencias/{o['id']}/status", headers=paula, json={"status": "EM_ANALISE"})
        self.assertEqual(self.c.delete(f"/api/ocorrencias/{o['id']}", headers=ricardo).status_code, 403)
        # filtros
        lista = self.c.get("/api/ocorrencias?status=EM_ANALISE&gravidade=MEDIA", headers=paula).get_json()
        self.assertTrue(lista and all(x["status"] == "EM_ANALISE" and x["gravidade"] == "MEDIA" for x in lista))
        self.assertTrue(any(x["id"] == o["id"] for x in self.c.get("/api/ocorrencias?busca=fone", headers=paula).get_json()))
        self.assertEqual(self.c.get("/api/ocorrencias?status=INEXISTENTE", headers=paula).status_code, 400)
        resumo = self.c.get("/api/ocorrencias/resumo", headers=paula).get_json()
        self.assertEqual(set(resumo), {"ABERTA", "EM_ANALISE", "RESOLVIDA"})
        # autor exclui enquanto aberta
        outra = self.nova_ocorrencia(ricardo, lucas, "Esqueceu o caderno").get_json()
        self.assertEqual(self.c.delete(f"/api/ocorrencias/{outra['id']}", headers=ricardo).status_code, 204)
        self.assertEqual(self.c.get(f"/api/ocorrencias/{outra['id']}", headers=paula).status_code, 404)

    def test_dashboard_da_coordenacao_conta_em_analise(self):
        paula = self.login("paula@eduvance.com")
        d = self.c.get("/api/dashboard", headers=paula).get_json()
        pendentes = sum(1 for o in self.c.get("/api/ocorrencias", headers=paula).get_json() if o["status"] != "RESOLVIDA")
        self.assertEqual(d["kpis"]["ocorrenciasAbertas"], pendentes)


class TestMensagensDeErro(ComBase):
    def test_nao_encontrado_concorda_com_o_genero(self):
        paula = self.login("paula@eduvance.com")
        for rota, esperado in (("/api/ocorrencias/99999", "Ocorrência não encontrada"), ("/api/avaliacoes/99999", "Avaliação não encontrada"),
                               ("/api/atividades/99999", "Atividade não encontrada"), ("/api/comunicados/99999", "Comunicado não encontrado"),
                               ("/api/boletim/99999", "Aluno não encontrado")):
            r = self.c.get(rota, headers=paula)
            self.assertEqual(r.status_code, 404, rota)
            self.assertEqual(r.get_json()["erro"], esperado)
        r = self.c.put("/api/notificacoes/99999/lida", headers=paula)
        self.assertEqual(r.get_json()["erro"], "Notificação não encontrada")


class TestFrequenciaCoerente(ComBase):
    def test_abaixo_do_minimo_so_com_aulas_suficientes(self):
        ricardo = self.login("roberta@eduvance.com")  # 9º Ano A · Redação não tem chamadas no seed
        td = next(t["id"] for t in self.c.get("/api/catalogo/turma-disciplinas", headers=ricardo).get_json()
                  if t["turma"] == "9º Ano A" and t["disciplina"] == "Redação")
        dia = _dia_util()
        alunos = self.c.get(f"/api/frequencia?idTurmaDisciplina={td}&data={dia}", headers=ricardo).get_json()["alunos"]
        regs = [{"idAluno": a["idAluno"], "presente": a["idAluno"] != alunos[0]["idAluno"]} for a in alunos]
        r = self.c.put("/api/frequencia", headers=ricardo, json={"idTurmaDisciplina": td, "data": str(dia), "registros": regs}).get_json()
        faltoso = next(a for a in r["alunos"] if a["idAluno"] == alunos[0]["idAluno"])
        self.assertEqual((faltoso["aulas"], faltoso["faltas"], faltoso["frequencia"]), (1, 1, 0.0))
        self.assertFalse(faltoso["abaixoDoMinimo"])  # 0% com apenas 1 aula registrada não é alarme
        self.assertEqual(r["alertas"], 0)


class TestNotificacoes(ComBase):
    def test_leitura_individual_e_em_massa(self):
        maria = self.login("maria@eduvance.com")
        d = self.notificacoes(maria)
        self.assertGreaterEqual(d["naoLidas"], 1)
        self.assertEqual(self.c.get("/api/notificacoes/contagem", headers=maria).get_json()["naoLidas"], d["naoLidas"])
        n = next(x for x in d["itens"] if not x["lida"])
        r = self.c.put(f"/api/notificacoes/{n['id']}/lida", headers=maria)
        self.assertEqual(r.get_json()["naoLidas"], d["naoLidas"] - 1)
        self.assertTrue(next(x for x in self.notificacoes(maria)["itens"] if x["id"] == n["id"])["lida"])
        self.assertTrue(all(not x["lida"] for x in self.notificacoes(maria, naoLidas=1)["itens"]))
        self.assertEqual(self.c.put("/api/notificacoes/lidas", headers=maria).get_json()["naoLidas"], 0)
        self.assertEqual(self.notificacoes(maria, naoLidas=1)["itens"], [])

    def test_cada_usuario_acessa_so_as_suas(self):
        maria, lucas = self.login("maria@eduvance.com"), self.login(MAT_LUCAS)
        nid = self.notificacoes(maria)["itens"][0]["id"]
        self.assertEqual(self.c.put(f"/api/notificacoes/{nid}/lida", headers=lucas).status_code, 404)
        self.assertEqual(self.c.delete(f"/api/notificacoes/{nid}", headers=lucas).status_code, 404)
        self.assertEqual(self.c.get("/api/notificacoes").status_code, 401)
        self.assertEqual(self.c.delete(f"/api/notificacoes/{nid}", headers=maria).status_code, 204)
        self.assertNotIn(nid, [x["id"] for x in self.notificacoes(maria)["itens"]])

    def test_alerta_de_frequencia_abaixo_do_minimo_uma_unica_vez(self):
        ricardo = self.login("ricardo@eduvance.com")
        td = next(t["id"] for t in self.c.get("/api/catalogo/turma-disciplinas", headers=ricardo).get_json()
                  if t["turma"] == "5º Ano A" and t["disciplina"] == "Matemática")
        alunos = self.c.get(f"/api/frequencia?idTurmaDisciplina={td}&data={_dia_util()}", headers=ricardo).get_json()["alunos"]
        faltoso = alunos[0]
        h_aluno = self.login(faltoso["matricula"])
        antes = [n for n in self.notificacoes(h_aluno)["itens"] if n["tipo"] == "FREQUENCIA"]
        self.assertEqual(antes, [])
        alertas = []
        for recuo in range(0, 24, 1):
            dia = _dia_util(recuo)
            if dia.weekday() >= 5 or str(dia) in {str(a) for a in alertas}:
                continue
            regs = [{"idAluno": a["idAluno"], "presente": a["idAluno"] != faltoso["idAluno"]} for a in alunos]
            r = self.c.put("/api/frequencia", headers=ricardo, json={"idTurmaDisciplina": td, "data": str(dia), "registros": regs})
            self.assertEqual(r.status_code, 200, r.get_json())
            alertas.append(dia)
        nots = [n for n in self.notificacoes(h_aluno)["itens"] if n["tipo"] == "FREQUENCIA"]
        self.assertEqual(len(nots), 1)  # apenas na transição, mesmo com várias chamadas depois
        self.assertIn("Matemática", nots[0]["titulo"])
        self.assertIn("mínimo exigido é 75%", nots[0]["mensagem"])


if __name__ == "__main__":
    unittest.main()
