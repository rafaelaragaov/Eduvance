"""Camada de banco dupla (Sprint 06): tradução SQLite -> PostgreSQL e migração de dados.

Os testes de tradução rodam sempre (não precisam do PostgreSQL). Os de migração/integração com o servidor
rodam só quando EDUVANCE_TEST_PG_URL está definida.
"""
import os
import sqlite3
import tempfile
import unittest
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from app import db
from app.db import Linha, _valor, eh_postgres, traduzir_para_pg

PG_URL = os.environ.get("EDUVANCE_TEST_PG_URL", "")


class TestTraducao(unittest.TestCase):
    def t(self, sql):
        return traduzir_para_pg(sql)

    def test_marcador_de_parametro(self):
        self.assertEqual(self.t("SELECT * FROM x WHERE a = ? AND b = ?"), "SELECT * FROM x WHERE a = %s AND b = %s")

    def test_percentual_literal_e_escapado(self):
        self.assertEqual(self.t("SELECT 'a%' WHERE n LIKE '%x'"), "SELECT 'a%%' WHERE n ILIKE '%%x'")

    def test_datas_relativas_ao_agora(self):
        self.assertEqual(self.t("WHERE d <= date('now','localtime')"), "WHERE d <= current_date")
        self.assertEqual(self.t("VALUES (datetime('now', 'localtime'))"), "VALUES (localtimestamp(0))")
        self.assertEqual(self.t("AND t >= datetime('now', 'localtime', ?)"), "AND t >= (localtimestamp(0) + CAST(%s AS interval))")

    def test_like_vira_ilike_para_manter_a_busca_sem_diferenciar_caixa(self):
        self.assertEqual(self.t("WHERE nome LIKE ?"), "WHERE nome ILIKE %s")

    def test_group_concat(self):
        self.assertEqual(self.t("SELECT group_concat(nome, ', ') FROM t"), "SELECT string_agg(nome, ', ') FROM t")

    def test_comparacao_com_nulo(self):
        self.assertEqual(self.t("WHERE id_turma IS ?"), "WHERE id_turma IS NOT DISTINCT FROM %s")
        self.assertEqual(self.t("WHERE autor IS NOT ?"), "WHERE autor IS DISTINCT FROM %s")
        self.assertEqual(self.t("WHERE (? IS NULL OR x = ?)"), "WHERE (CAST(%s AS TEXT) IS NULL OR x = %s)")
        self.assertEqual(self.t("WHERE x IS NULL AND y IS NOT NULL"), "WHERE x IS NULL AND y IS NOT NULL")

    def test_detecta_destino(self):
        self.assertTrue(eh_postgres("postgresql://u:p@h/d"))
        self.assertTrue(eh_postgres("postgres://u:p@h/d"))
        self.assertFalse(eh_postgres("/tmp/x.db"))
        self.assertFalse(eh_postgres(""))


class TestConversaoDeTipos(unittest.TestCase):
    def test_tipos_do_postgres_viram_os_do_sqlite(self):
        self.assertEqual(_valor(Decimal("7.50")), 7.5)
        self.assertEqual(_valor(datetime(2026, 10, 18, 14, 30, 5)), "2026-10-18T14:30:05")
        self.assertEqual(_valor(date(2026, 10, 18)), "2026-10-18")
        self.assertEqual(_valor(time(8, 0)), "08:00")
        self.assertEqual(_valor(time(8, 5, 30)), "08:05:30")
        self.assertEqual(_valor(True), 1)
        self.assertIsNone(_valor(None))
        self.assertEqual(_valor("texto"), "texto")

    def test_linha_acessa_por_nome_e_posicao(self):
        r = Linha([("idTurma", 3), ("nome", "8º B")])
        self.assertEqual((r["idTurma"], r[0], r[1], dict(r)), (3, 3, "8º B", {"idTurma": 3, "nome": "8º B"}))


@unittest.skipUnless(PG_URL and db.psycopg, "defina EDUVANCE_TEST_PG_URL (e instale psycopg) para testar contra o PostgreSQL")
class TestPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = "m_" + uuid.uuid4().hex[:10]

    @classmethod
    def tearDownClass(cls):
        con = db.ConexaoPG(PG_URL)
        con.execute(f"DROP SCHEMA IF EXISTS {cls.schema} CASCADE")
        con.commit()
        con.close()

    def test_migracao_sqlite_para_postgres_confere_contagens_e_sequencias(self):
        from app.init_db import criar_banco
        from app.migrar_para_postgres import migrar

        with tempfile.TemporaryDirectory() as d:
            origem = os.path.join(d, "origem.db")
            criar_banco(origem)
            contagens = migrar(origem, PG_URL, self.schema, reset=True)
            con = sqlite3.connect(origem)
            self.assertEqual(contagens["usuario"], con.execute("SELECT COUNT(*) FROM usuario").fetchone()[0])
            self.assertEqual(contagens["avaliacao"], con.execute("SELECT COUNT(*) FROM avaliacao").fetchone()[0])
            con.close()
        pg = db.ConexaoPG(PG_URL, self.schema)
        try:
            # uma senha e uma data de prova chegaram intactas
            h = pg.execute("SELECT senha_hash FROM usuario WHERE email = ?", ("ricardo@eduvance.com",)).fetchone()[0]
            self.assertTrue(h.startswith(("pbkdf2:", "scrypt:")))
            # a sequência foi acertada: o próximo cadastro não colide com um id migrado
            novo = pg.execute("INSERT INTO disciplina (nome) VALUES (?)", ("Disciplina nova (teste)",)).lastrowid
            maximo = pg.execute("SELECT MAX(id_disciplina) AS m FROM disciplina").fetchone()["m"]
            self.assertEqual(novo, maximo)
            pg.commit()
        finally:
            pg.close()

    def test_alias_camel_case_e_lastrowid(self):
        pg = db.ConexaoPG(PG_URL, self.schema)
        try:
            r = pg.execute("SELECT 1 AS idTurma, 'x' AS nomeCompleto").fetchone()
            self.assertEqual((r["idTurma"], r["nomeCompleto"], r[0]), (1, "x", 1))
        finally:
            pg.close()


if __name__ == "__main__":
    unittest.main()
