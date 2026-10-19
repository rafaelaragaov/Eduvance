"""Testes do paralelismo e do ponto de entrada (Sprint 07).

Garantem que calcular em vários processos dá exatamente o mesmo resultado que calcular em um só, que o
recálculo em lote grava no banco e que o executável responde aos modos novos.
"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import paralelo  # noqa: E402
from app.config import COMPILADO, RAIZ  # noqa: E402
from test_api import Base  # noqa: E402


class Processos(unittest.TestCase):
    def test_resolver_processos(self):
        self.assertEqual(paralelo.resolver_processos("auto"), os.cpu_count() or 1)
        self.assertEqual(paralelo.resolver_processos(None), os.cpu_count() or 1)
        self.assertEqual(paralelo.resolver_processos("3"), 3)
        with self.assertRaises(ValueError):
            paralelo.resolver_processos("0")
        with self.assertRaises(ValueError):
            paralelo.resolver_processos("abc")

    def test_lote_sintetico_e_deterministico(self):
        self.assertEqual(paralelo.lote_sintetico(5), paralelo.lote_sintetico(5))
        self.assertNotEqual(paralelo.lote_sintetico(5, semente=1), paralelo.lote_sintetico(5, semente=2))

    def test_benchmark_em_varios_processos_confere_com_o_sequencial(self):
        linhas: list[str] = []
        r = paralelo.benchmark(2, 0.5, lote=paralelo.lote_sintetico(8), saida=linhas.append, janela=0.3)
        self.assertTrue(r["consistente"], "o resultado em paralelo difere do sequencial")
        self.assertEqual(r["processos"], 2)
        self.assertGreater(r["chamadas"], 0)
        self.assertGreater(r["taxa_n"], 0)
        self.assertLess(r["duracao"], 3.0)
        self.assertTrue(any("RESULTADO" in l for l in linhas))

    def test_benchmark_com_um_processo(self):
        r = paralelo.benchmark(1, 0.5, lote=paralelo.lote_sintetico(4), saida=lambda _: None, janela=0.2)
        self.assertTrue(r["consistente"])
        self.assertGreaterEqual(r["tarefas"], 2)
        self.assertLess(r["duracao"], 3.0)  # a duração segue o tempo pedido (0,5 s) e não o número de tarefas

    def test_modo_sem_banco_usa_alunos_ficticios(self):
        from app import create_app

        with tempfile.TemporaryDirectory() as d:
            app = create_app({"DATABASE": os.path.join(d, "inexistente.db"), "DATABASE_URL": ""})
            linhas: list[str] = []
            paralelo.benchmark(1, 0.5, saida=linhas.append, janela=0.2, app=app)
        self.assertTrue(any("fictícios" in l for l in linhas))


class RecalculoEmLote(Base):
    def gravado(self):
        return self.sql("SELECT id_aluno, tipo, prioridade, score, titulo FROM recomendacao_ia ORDER BY id_aluno, score DESC, titulo")

    def test_recalculo_grava_e_paralelo_igual_ao_sequencial(self):
        r1 = paralelo.recalcular_todos(1, saida=lambda _: None, app=self.app)
        sequencial = self.gravado()
        self.assertGreater(r1["alunos"], 50)
        self.assertEqual(r1["itens"], len(sequencial))

        r2 = paralelo.recalcular_todos(2, saida=lambda _: None, app=self.app)
        self.assertEqual(r2["processos"], 2)
        self.assertEqual(self.gravado(), sequencial, "o recálculo paralelo gravou algo diferente do sequencial")

    def test_lote_do_banco_tem_um_documento_por_aluno(self):
        lote = paralelo.lote_do_banco(self.app)
        self.assertGreater(len(lote), 50)
        self.assertTrue(all("disciplinas" in d and "parametros" in d for d in lote))


class PontoDeEntrada(unittest.TestCase):
    def setUp(self):
        import eduvance

        self.eduvance = eduvance

    def rodar(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            codigo = self.eduvance.main(list(args))
        return codigo, buf.getvalue()

    def test_versao_informa_modo_de_execucao(self):
        codigo, saida = self.rodar("--versao")
        self.assertEqual(codigo, 0)
        self.assertIn("código-fonte Python" if not COMPILADO else "compilado", saida)

    def test_numero_de_processos_invalido(self):
        codigo, _ = self.rodar("--benchmark-paralelo", "--processos", "0")
        self.assertEqual(codigo, 2)

    def test_raiz_e_a_do_repositorio_quando_nao_compilado(self):
        self.assertFalse(COMPILADO)
        self.assertTrue((RAIZ / "database" / "schema.sql").is_file())


if __name__ == "__main__":
    unittest.main()
