"""Testa a camada HTTP (FastAPI). Roda só se `fastapi` estiver instalado (pip install -r recomendacao/requirements.txt)."""
import unittest

try:
    from fastapi.testclient import TestClient
    from recomendacao.servico import app
except Exception:  # fastapi/httpx ausentes
    TestClient = None


@unittest.skipIf(TestClient is None, "fastapi não instalado")
class TestServico(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(app)

    def test_health(self):
        r = self.c.get("/health")
        self.assertEqual((r.status_code, r.json()["status"]), (200, "ok"))

    def test_recomendar(self):
        r = self.c.post("/recomendar", json={"disciplinas": [{"nome": "Matemática", "media": 4.5}], "faltas": 3})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["itens"][0]["tipo"], "REFORCO")

    def test_validacao_rejeita_nota_fora_da_faixa(self):
        r = self.c.post("/recomendar", json={"disciplinas": [{"nome": "Matemática", "media": 14}]})
        self.assertEqual(r.status_code, 422)

    def test_openapi_documenta_o_contrato(self):
        self.assertIn("/recomendar", self.c.get("/openapi.json").json()["paths"])


if __name__ == "__main__":
    unittest.main()
