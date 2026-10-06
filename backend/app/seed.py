"""Dados de demonstração. Senhas gravadas como hash (nunca em texto puro).
Datas são relativas a "hoje" para a agenda/prazos fazerem sentido no dia da apresentação."""
import unicodedata
from datetime import date, datetime, timedelta

from .security import hash_senha

SENHA_PADRAO = "senha123"
SENHA_ADMIN = "admin123"

NOMES = ["Ana", "Bruno", "Camila", "Daniel", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela", "João",
         "Karina", "Leonardo", "Marcos", "Natália", "Otávio", "Paula", "Rafael", "Sofia", "Tiago", "Vitória"]
SOBRENOMES = ["Almeida", "Barbosa", "Cardoso", "Dias", "Ferreira", "Gomes", "Lopes", "Martins",
              "Nogueira", "Oliveira", "Pereira", "Queiroz", "Rocha", "Santos", "Teixeira", "Vasconcelos"]

# turma, disciplina, início, fim, sala  (repetidos de segunda a sexta)
HORARIOS = [
    ("8º Ano B", "Português", "08:00", "08:50", "104"), ("8º Ano B", "Matemática", "09:00", "09:50", "105"),
    ("8º Ano B", "História", "10:00", "10:50", "302"), ("8º Ano B", "Ciências", "11:00", "11:50", "210"),
    ("8º Ano B", "Geografia", "13:00", "13:50", "212"),
    ("8º Ano A", "Matemática", "08:00", "08:50", "201"), ("8º Ano A", "Português", "09:00", "09:50", "106"),
    ("8º Ano A", "História", "11:00", "11:50", "303"), ("8º Ano A", "Ciências", "14:00", "14:50", "211"),
    ("8º Ano A", "Geografia", "15:00", "15:50", "213"),
    ("9º Ano A", "Ciências", "08:00", "08:50", "308"), ("9º Ano A", "História", "09:00", "09:50", "307"),
    ("9º Ano A", "Português", "10:00", "10:50", "301"), ("9º Ano A", "Matemática", "11:00", "11:50", "302"),
    ("9º Ano A", "Redação", "13:00", "13:50", "305"),
    ("5º Ano A", "Matemática", "13:00", "13:50", "101"), ("5º Ano A", "Português", "14:00", "14:50", "102"),
    ("5º Ano A", "Ciências", "16:00", "16:50", "103"),
]


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def _dt(d: date | datetime, h: int = 0, m: int = 0) -> str:
    return datetime(d.year, d.month, d.day, h, m).strftime("%Y-%m-%dT%H:%M:%S")


def _dias_uteis(n: int, hoje: date) -> list[str]:
    out, d = [], hoje
    while len(out) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            out.append(d.isoformat())
    return out


def popular(con) -> None:
    hoje = date.today()
    ano = hoje.year
    h_padrao, h_admin = hash_senha(SENHA_PADRAO), hash_senha(SENHA_ADMIN)

    def ins(sql, p=()):
        return con.execute(sql, p).lastrowid

    def usuario(nome, email, perfil, h=None):
        return ins("INSERT INTO usuario (nome,email,senha_hash,perfil) VALUES (?,?,?,?)", (nome, email, h or h_padrao, perfil))

    # ---- administração / coordenação / professores
    usuario("Administrador do Sistema", "admin@eduvance.com", "ADMIN", h_admin)
    paula = usuario("Paula Ramos", "paula@eduvance.com", "COORDENADOR")
    ins("INSERT INTO coordenador (id_coordenador, cargo) VALUES (?,?)", (paula, "Coordenadora Geral"))

    prof = {}
    for chave, nome, email, esp in [
        ("ricardo", "Ricardo Ramos", "ricardo@eduvance.com", "Matemática"),
        ("ana", "Ana Guimarães", "ana.guimaraes@eduvance.com", "Português"),
        ("carlos", "Carlos Silveira", "carlos@eduvance.com", "História"),
        ("marcelo", "Marcelo Tavares", "marcelo@eduvance.com", "Ciências e Geografia"),
        ("roberta", "Roberta Lima", "roberta@eduvance.com", "Redação"),
    ]:
        prof[chave] = usuario(nome, email, "PROFESSOR")
        ins("INSERT INTO professor (id_professor, especialidade) VALUES (?,?)", (prof[chave], esp))

    # ---- turmas e disciplinas
    turma = {n: ins("INSERT INTO turma (nome, ano_letivo) VALUES (?,?)", (n, ano)) for n in ["8º Ano A", "8º Ano B", "9º Ano A", "5º Ano A"]}
    disc = {n: ins("INSERT INTO disciplina (nome) VALUES (?)", (n,)) for n in ["Matemática", "Português", "História", "Ciências", "Geografia", "Redação"]}

    td = {}

    def vincula(t, d, p):
        td[(t, d)] = ins("INSERT INTO turma_disciplina (id_turma,id_disciplina,id_professor) VALUES (?,?,?)", (turma[t], disc[d], prof[p]))

    for t in ("8º Ano A", "8º Ano B"):
        for d, p in [("Matemática", "ricardo"), ("Português", "ana"), ("História", "carlos"), ("Ciências", "marcelo"), ("Geografia", "marcelo")]:
            vincula(t, d, p)
    for d, p in [("Matemática", "ricardo"), ("Português", "ana"), ("História", "carlos"), ("Ciências", "marcelo"), ("Redação", "roberta")]:
        vincula("9º Ano A", d, p)
    for d, p in [("Matemática", "ricardo"), ("Português", "ana"), ("Ciências", "marcelo")]:
        vincula("5º Ano A", d, p)

    for t, d, ini, fim, sala in HORARIOS:
        for dia in range(1, 6):
            ins("INSERT INTO horario (id_turma_disciplina,dia_semana,hora_inicio,hora_fim,sala) VALUES (?,?,?,?,?)", (td[(t, d)], dia, ini, fim, sala))

    # ---- alunos
    seq = 0

    def aluno(nome, email, t, serie, nasc):
        nonlocal seq
        seq += 1
        id_ = usuario(nome, email, "ALUNO")
        ins("INSERT INTO aluno (id_aluno,matricula,data_nascimento,serie,id_turma) VALUES (?,?,?,?,?)", (id_, f"{ano}{seq:04d}", nasc, serie, turma[t]))
        return id_

    lucas = aluno("Lucas Silva", "lucas.silva@aluno.eduvance.com", "8º Ano B", "8º Ano", "2011-03-14")
    mariana = aluno("Mariana Costa", "mariana.costa@aluno.eduvance.com", "8º Ano B", "8º Ano", "2011-07-02")
    thiago = aluno("Thiago Ramos", "thiago.ramos@aluno.eduvance.com", "8º Ano B", "8º Ano", "2011-11-21")
    ana = aluno("Ana Silva", "ana.silva@aluno.eduvance.com", "5º Ano A", "5º Ano", "2015-05-09")

    ja = {"8º Ano B": 3, "5º Ano A": 1}
    n = 0
    for t, total in {"8º Ano A": 32, "8º Ano B": 28, "9º Ano A": 30, "5º Ano A": 20}.items():
        for _ in range(ja.get(t, 0), total):
            nome = f"{NOMES[n % len(NOMES)]} {SOBRENOMES[(n * 7 + 3) % len(SOBRENOMES)]}"
            serie = t.split(" ")[0]
            aluno(nome, f"{_sem_acento(nome).replace(' ', '.')}.{n + 1}@aluno.eduvance.com", t, f"{serie} Ano", "2011-01-01")
            n += 1

    # ---- responsáveis
    maria = usuario("Maria Silva", "maria@eduvance.com", "RESPONSAVEL")
    joao = usuario("João Silva", "joao.silva@eduvance.com", "RESPONSAVEL")
    ins("INSERT INTO responsavel (id_responsavel, telefone) VALUES (?,?)", (maria, "(81) 99999-0001"))
    ins("INSERT INTO responsavel (id_responsavel, telefone) VALUES (?,?)", (joao, "(81) 99999-0002"))
    for a, r, g in [(lucas, maria, "Mãe"), (lucas, joao, "Pai"), (ana, maria, "Mãe")]:
        ins("INSERT INTO aluno_responsavel (id_aluno,id_responsavel,grau_parentesco) VALUES (?,?,?)", (a, r, g))

    # ---- avaliações, notas e frequência
    aval = {k: ins("INSERT INTO avaliacao (id_turma_disciplina,titulo,data_avaliacao,tipo,bimestre) VALUES (?,?,?,?,2)",
                   (v, "Prova B2", (hoje - timedelta(days=14)).isoformat(), "PROVA")) for k, v in td.items()}
    notas = [
        (lucas, "8º Ano B", {"Matemática": 7.5, "Português": 8.0, "História": 9.0, "Ciências": 8.5, "Geografia": 7.8}),
        (mariana, "8º Ano B", {"Matemática": 9.0, "Português": 8.5, "História": 8.0, "Ciências": 9.2, "Geografia": 8.8}),
        (thiago, "8º Ano B", {"Matemática": 6.2, "Português": 7.0, "História": 6.5, "Ciências": 7.1, "Geografia": 6.0}),
        (ana, "5º Ano A", {"Matemática": 9.0, "Português": 9.5, "Ciências": 8.8}),
    ]
    for a, t, por in notas:
        for d, v in por.items():
            ins("INSERT INTO nota (id_avaliacao,id_aluno,valor) VALUES (?,?,?)", (aval[(t, d)], a, v))

    # 1º bimestre: prova (peso 1) e trabalho (peso 0,5), para o boletim completo (Sprint 04)
    ajuste = {lucas: -0.5, mariana: 0.3, thiago: 0.4, ana: 0.0}
    for (t, d), id_td in td.items():
        p1 = ins("INSERT INTO avaliacao (id_turma_disciplina,titulo,data_avaliacao,tipo,bimestre,peso) VALUES (?,?,?,?,1,1)",
                 (id_td, "Prova B1", (hoje - timedelta(days=75)).isoformat(), "PROVA"))
        tr = ins("INSERT INTO avaliacao (id_turma_disciplina,titulo,data_avaliacao,tipo,bimestre,peso) VALUES (?,?,?,?,1,0.5)",
                 (id_td, "Trabalho B1", (hoje - timedelta(days=60)).isoformat(), "TRABALHO"))
        for a, tt, por in notas:
            if tt == t and d in por:
                ins("INSERT INTO nota (id_avaliacao,id_aluno,valor) VALUES (?,?,?)", (p1, a, round(min(10, max(0, por[d] + ajuste[a])), 1)))
                ins("INSERT INTO nota (id_avaliacao,id_aluno,valor) VALUES (?,?,?)", (tr, a, round(min(10, por[d] + 0.5), 1)))

    dias = _dias_uteis(20, hoje)
    faltas = [
        (lucas, "8º Ano B", {"Matemática": [3], "História": [7], "Geografia": [12]}),
        (mariana, "8º Ano B", {"Português": [5]}),
        (thiago, "8º Ano B", {"Matemática": [2], "Português": [2], "Ciências": [9], "Geografia": [15]}),
        (ana, "5º Ano A", {"Ciências": [4]}),
    ]
    for a, t, faltou in faltas:
        for (tt, d), id_td in td.items():
            if tt != t:
                continue
            for i, dia in enumerate(dias):
                ins("INSERT INTO frequencia (id_aluno,id_turma_disciplina,data,presente) VALUES (?,?,?,?)",
                    (a, id_td, dia, 0 if i in faltou.get(d, []) else 1))

    # ---- atividades
    def prazo(dias_, h, m=0):
        return _dt(hoje + timedelta(days=dias_), h, m)

    for t, d, titulo, desc, data in [
        ("8º Ano B", "Matemática", "Exercícios de Trigonometria", "Resolver a lista de exercícios do capítulo 4.", prazo(0, 23, 59)),
        ("8º Ano B", "Português", "Redação: Inteligência Artificial", "Texto dissertativo-argumentativo sobre o uso de IA na sociedade.", prazo(1, 12)),
        ("8º Ano B", "Ciências", "Maquete do Sistema Solar", "Maquete em grupo com legenda dos planetas.", prazo(10, 12)),
        ("8º Ano B", "História", "Resumo: Revolução Industrial", "Resumo de duas páginas sobre causas e consequências.", prazo(4, 18)),
        ("8º Ano B", "Geografia", "Mapa dos Biomas Brasileiros", "Mapa colorido com legenda dos biomas.", prazo(6, 18)),
        ("8º Ano A", "Matemática", "Lista de Equações do 2º Grau", None, prazo(3, 18)),
        ("5º Ano A", "Matemática", "Problemas de Frações", None, prazo(2, 12)),
    ]:
        ins("INSERT INTO atividade (id_turma_disciplina,titulo,descricao,data_entrega) VALUES (?,?,?,?)", (td[(t, d)], titulo, desc, data))

    # ---- comunicados, eventos, ocorrências, mensalidades
    ins("INSERT INTO comunicado (titulo,mensagem,data_publicacao,id_usuario_autor) VALUES (?,?,?,?)",
        (f"Feira de Ciências {ano}", "Os grupos devem enviar os temas de maquetes até a próxima sexta-feira.", _dt(hoje - timedelta(days=2), 9), paula))
    ins("INSERT INTO comunicado (titulo,mensagem,data_publicacao,id_usuario_autor) VALUES (?,?,?,?)",
        ("Reunião de Pais e Mestres", "Convocamos os responsáveis para a reunião bimestral que ocorrerá no auditório.", _dt(hoje - timedelta(days=4), 9), paula))

    for titulo, desc, dias_, h, tipo in [
        ("Reunião de Pais e Mestres", "Entrega de boletins do 3º Bimestre", 10, 19, "REUNIAO"),
        ("Conselho de Classe Geral", "Alinhamento pedagógico e notas baixas", 15, 14, "CONSELHO"),
        (f"Feira de Ciências {ano}", "Exposição de projetos no pátio central", 20, 9, "EVENTO"),
    ]:
        ins("INSERT INTO evento (titulo,descricao,inicio,tipo) VALUES (?,?,?,?)", (titulo, desc, _dt(hoje + timedelta(days=dias_), h), tipo))

    for a, p, titulo, desc, quando, status in [
        (lucas, prof["marcelo"], "Conversa Paralela em Sala",
         f"Lucas foi advertido por conversar excessivamente durante a aula de Geografia em {hoje:%d/%m}.", _dt(hoje, 10, 30), "ABERTA"),
        (mariana, prof["ana"], "Atraso recorrente no primeiro tempo", "Chegou atrasado pela terceira vez na semana.", _dt(hoje - timedelta(days=1), 8, 15), "ABERTA"),
        (thiago, prof["marcelo"], "Esquecimento de material", "Sem o material de Geografia pela segunda vez.", _dt(hoje - timedelta(days=3), 13, 10), "ABERTA"),
        (thiago, prof["ana"], "Uso de celular em aula", "Advertido verbalmente pelo uso do celular durante a explicação.", _dt(hoje - timedelta(days=5), 8, 20), "ABERTA"),
        (lucas, prof["carlos"], "Atraso na entrega de trabalho", "Trabalho de História entregue com atraso; já regularizado.", _dt(hoje - timedelta(days=20), 10, 0), "RESOLVIDA"),
    ]:
        ins("INSERT INTO ocorrencia (id_aluno,id_professor,titulo,descricao,data_ocorrencia,status) VALUES (?,?,?,?,?,?)", (a, p, titulo, desc, quando, status))

    mes_ant = (hoje.replace(day=1) - timedelta(days=1)).replace(day=10)
    for a in (lucas, ana):
        ins("INSERT INTO mensalidade (id_aluno,valor,vencimento,status,forma_pagamento) VALUES (?,?,?,?,?)", (a, 1200, mes_ant.isoformat(), "PAGA", "PIX"))
        ins("INSERT INTO mensalidade (id_aluno,valor,vencimento,status,forma_pagamento) VALUES (?,?,?,?,?)", (a, 1200, hoje.replace(day=10).isoformat(), "ABERTA", None))

    # ---- vestibular
    s1 = ins("INSERT INTO simulado (titulo,data_aplicacao,vestibular) VALUES (?,?,?)", ("Simulado Nacional ENEM #3", (hoje - timedelta(days=23)).isoformat(), "ENEM"))
    s2 = ins("INSERT INTO simulado (titulo,data_aplicacao,vestibular) VALUES (?,?,?)", ("Simulado Geral Unicamp #2", (hoje - timedelta(days=30)).isoformat(), "Unicamp"))
    for s, a, pts, pct in [(s1, lucas, 720, 72), (s2, lucas, 685, 68.5), (s1, mariana, 810, 81)]:
        ins("INSERT INTO resultado_simulado (id_simulado,id_aluno,pontuacao,percentual) VALUES (?,?,?,?)", (s, a, pts, pct))

    ins("INSERT INTO redacao (id_aluno,tema,texto,nota,id_professor,status,enviada_em) VALUES (?,?,?,?,?,?,?)", (
        lucas, "Impactos da Saúde Mental na Sociedade Moderna",
        "A saúde mental tornou-se um dos temas centrais do debate contemporâneo, pois afeta a produtividade, "
        "as relações sociais e a qualidade de vida das pessoas. Diante disso, é necessário ampliar o acesso ao cuidado psicológico e combater o estigma.",
        840, prof["roberta"], "CORRIGIDA", _dt(hoje - timedelta(days=10), 15)))

    ins("INSERT INTO material (titulo,tipo,detalhe,url,vestibular,id_disciplina) VALUES (?,?,?,?,?,?)", ("Análise Combinatória Avançada", "Videoaula", "24 mins", "#", "ENEM", disc["Matemática"]))
    ins("INSERT INTO material (titulo,tipo,detalhe,url,vestibular,id_disciplina) VALUES (?,?,?,?,?,?)", ("Guia de Redação Nota 1000", "eBook PDF", "4.2 MB", "#", None, disc["Redação"]))

    f1 = ins("INSERT INTO forum (titulo,descricao,id_disciplina,data_criacao) VALUES (?,?,?,?)",
             ("Dúvida sobre função quadrática composta", "Como resolver f(g(x)) quando ambas são quadráticas?", disc["Matemática"], _dt(hoje - timedelta(days=3), 10)))
    f2 = ins("INSERT INTO forum (titulo,descricao,id_disciplina,data_criacao) VALUES (?,?,?,?)",
             ("Discussão: Principais causas da Revolução Industrial", "Quais fatores foram decisivos para o início da industrialização?", disc["História"], _dt(hoje - timedelta(days=5), 10)))
    autores = [lucas, mariana, thiago, prof["ricardo"]]
    for i in range(12):
        ins("INSERT INTO post_forum (id_forum,id_usuario,conteudo,data_publicacao) VALUES (?,?,?,?)",
            (f1, autores[i % 4], f"Resposta {i + 1}: aplique a composição substituindo g(x) em f e organize os termos.", _dt(hoje - timedelta(days=3 - i // 4), 11)))
    for i in range(8):
        ins("INSERT INTO post_forum (id_forum,id_usuario,conteudo,data_publicacao) VALUES (?,?,?,?)",
            (f2, autores[(i + 1) % 4], f"Comentário {i + 1}: a máquina a vapor e a mão de obra barata foram fatores decisivos.", _dt(hoje - timedelta(days=4 - i // 4), 11)))
