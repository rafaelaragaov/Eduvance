"""Testes do motor de recomendação (sem dependências): python -m unittest discover -s recomendacao/tests -t ."""
import unittest

from recomendacao import motor


def disc(nome, media, notas=(), freq=None, aulas=0):
    return {"nome": nome, "media": media, "notas": [{"valor": v, "data": f"2026-0{i + 1}-01"} for i, v in enumerate(notas)], "frequencia": freq, "aulas": aulas}


def tipos(r):
    return [i["tipo"] for i in r["itens"]]


class TestMotor(unittest.TestCase):
    def test_entrada_vazia_nao_quebra(self):
        r = motor.gerar({})
        self.assertEqual(r["itens"], [])
        self.assertEqual(r["resumo"], {"nivel": "TRANQUILO", "altas": 0, "total": 0})

    def test_media_abaixo_da_aprovacao_gera_reforco_alto(self):
        r = motor.gerar({"disciplinas": [disc("Matemática", 4.5)]})
        i = r["itens"][0]
        self.assertEqual((i["tipo"], i["prioridade"], i["disciplina"]), ("REFORCO", "ALTA", "Matemática"))
        self.assertIn("faltam 1,5", i["mensagem"])
        self.assertEqual(i["motivo"]["media"], 4.5)

    def test_media_proxima_do_minimo_gera_atencao_media(self):
        i = motor.gerar({"disciplinas": [disc("História", 6.4)]})["itens"][0]
        self.assertEqual((i["tipo"], i["prioridade"]), ("REFORCO", "MEDIA"))

    def test_media_alta_vira_destaque(self):
        r = motor.gerar({"disciplinas": [disc("Português", 9.3)]})
        self.assertEqual(tipos(r), ["DESTAQUE"])
        self.assertEqual(r["itens"][0]["link"], "/vestibular")

    def test_queda_de_notas_exige_tres_avaliacoes(self):
        self.assertEqual(tipos(motor.gerar({"disciplinas": [disc("Ciências", 7.5, [8, 4])]})), [])
        r = motor.gerar({"disciplinas": [disc("Ciências", 7.5, [9, 8, 5])]})
        self.assertEqual(tipos(r), ["REFORCO"])
        self.assertIn("queda", r["itens"][0]["titulo"].lower())

    def test_prova_cruza_agenda_com_notas(self):
        base = {"provas": [{"titulo": "Prova B2", "disciplina": "Matemática", "dias": 2}]}
        fraca = motor.gerar({**base, "disciplinas": [disc("Matemática", 4.0)]})
        forte = motor.gerar({**base, "disciplinas": [disc("Matemática", 8.0)]})
        pf = next(i for i in fraca["itens"] if i["tipo"] == "PROVA")
        pg = next(i for i in forte["itens"] if i["tipo"] == "PROVA")
        self.assertGreater(pf["score"], pg["score"])
        self.assertEqual((pf["motivo"]["minutosPorDia"], pg["motivo"]["minutosPorDia"]), (60, 30))
        self.assertIn("4,0", pf["mensagem"])

    def test_prova_fora_da_janela_ou_passada_e_ignorada(self):
        r = motor.gerar({"provas": [{"titulo": "A", "disciplina": "X", "dias": 8}, {"titulo": "B", "disciplina": "X", "dias": -1}]})
        self.assertEqual(r["itens"], [])

    def test_prova_mais_proxima_pesa_mais(self):
        r = motor.gerar({"provas": [{"titulo": "Longe", "disciplina": "X", "dias": 6}, {"titulo": "Perto", "disciplina": "Y", "dias": 1}]})
        self.assertEqual(r["itens"][0]["titulo"], "Perto em 1 dias".replace("em 1 dias", "amanhã"))

    def test_faltas_em_tres_faixas(self):
        self.assertEqual(tipos(motor.gerar({"faltas": 8})), [])
        self.assertEqual(motor.gerar({"faltas": 9})["itens"][0]["prioridade"], "MEDIA")
        self.assertEqual(motor.gerar({"faltas": 12})["itens"][0]["prioridade"], "ALTA")
        i = motor.gerar({"faltas": 15})["itens"][0]
        self.assertEqual((i["prioridade"], i["score"]), ("ALTA", 100.0))

    def test_frequencia_baixa_por_disciplina_respeita_minimo_de_aulas(self):
        self.assertEqual(tipos(motor.gerar({"disciplinas": [disc("Artes", 7, freq=50, aulas=3)]})), [])
        self.assertEqual(tipos(motor.gerar({"disciplinas": [disc("Artes", 7, freq=50, aulas=10)]})), ["FREQUENCIA"])

    def test_atividade_vencendo_ou_atrasada(self):
        r = motor.gerar({"atividades": [{"titulo": "Lista", "disciplina": "Mat", "dias": 0}, {"titulo": "Resumo", "disciplina": "His", "dias": -2}, {"titulo": "Longe", "dias": 5}]})
        self.assertEqual(sorted(i["titulo"] for i in r["itens"]), ["Entrega atrasada: Resumo", "Entrega hoje: Lista"])
        self.assertEqual(r["itens"][0]["titulo"], "Entrega atrasada: Resumo")

    def test_ordenacao_limite_e_nivel_de_atencao(self):
        dados = {"disciplinas": [disc(f"D{i}", 3.0 + i / 10) for i in range(8)], "faltas": 15}
        r = motor.gerar(dados)
        self.assertEqual(len(r["itens"]), motor.LIMITE_ITENS)
        scores = [i["score"] for i in r["itens"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(r["resumo"]["nivel"], "ATENCAO")

    def test_saida_e_deterministica(self):
        d = {"disciplinas": [disc("Matemática", 5.0, [8, 7, 4])], "faltas": 10, "provas": [{"titulo": "P", "disciplina": "Matemática", "dias": 3}]}
        self.assertEqual(motor.gerar(d), motor.gerar(d))

    def test_parametros_personalizados(self):
        padrao = motor.gerar({"disciplinas": [disc("Matemática", 6.5)]})["itens"][0]
        rigida = motor.gerar({"parametros": {"mediaAprovacao": 7.0}, "disciplinas": [disc("Matemática", 6.5)]})["itens"][0]
        self.assertTrue(padrao["titulo"].startswith("Atenção"))   # 6,5 passa de 6,0
        self.assertTrue(rigida["titulo"].startswith("Reforço"))   # 6,5 não passa de 7,0


if __name__ == "__main__":
    unittest.main()
