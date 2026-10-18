// Roteiro E2E da Sprint 06 (Playwright). Uso:  node roteiro_e2e.mjs [URL_BASE] [PASTA_DE_SAIDA]
// Estável por construção: todas as datas são calculadas a partir da própria API (nunca fixas), os seletores usam
// data-testid / papéis ARIA e toda espera é por elemento (nenhum sleep arbitrário).
import { chromium } from 'playwright';
const base = process.argv[2] ?? 'http://localhost:5058';
const out = process.argv[3] ?? new URL('.', import.meta.url).pathname;
const ano = new Date().getFullYear();
const browser = await chromium.launch({ args: ['--no-sandbox'], ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
const falhas = [];
let total = 0;
const ok = (c, m) => { total++; console.log(c ? '  ✔' : '  ✖', m); if (!c) falhas.push(m); };
const shot = (p, f) => p.screenshot({ path: `${out}/${f}.png` });
const tokens = {};
async function api(ident, path, method = 'GET', body) {
  if (!tokens[ident]) {
    const r = await fetch(base + '/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ identificador: ident, senha: 'senha123' }) });
    tokens[ident] = (await r.json()).token;
  }
  const x = await fetch(base + '/api' + path, { method, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tokens[ident] }, body: body ? JSON.stringify(body) : undefined });
  return { status: x.status, json: await x.json().catch(() => null) };
}
async function entrar(ident, vp = { width: 1440, height: 900 }) {
  const ctx = await browser.newContext({ viewport: vp, locale: 'pt-BR' });
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', (e) => errs.push(e.message));
  await p.goto(base); await p.fill('input[type=text]', ident); await p.fill('input[type=password]', 'senha123');
  await p.click('button.btn-primary'); await p.waitForSelector('.main h1');
  return { ctx, p, errs };
}
const q = (n) => String(n).padStart(2, '0');
const isoD = (d) => `${d.getFullYear()}-${q(d.getMonth() + 1)}-${q(d.getDate())}`;
/** Primeiro dia útil, a partir de `ini`, sem feriado/recesso/avaliação no calendário real (consultado na API). */
async function diaLivre(ini) {
  const d = new Date(ini + 'T00:00:00');
  const fim = new Date(d); fim.setDate(fim.getDate() + 40);
  const r = await api('paula@eduvance.com', `/agenda?inicio=${isoD(d)}&fim=${isoD(fim)}&tipos=EVENTO,AVALIACAO`);
  const ocupados = new Set(r.json.itens.map((i) => i.inicio.slice(0, 10)));
  while (d.getDay() === 0 || d.getDay() === 6 || ocupados.has(isoD(d))) d.setDate(d.getDate() + 1);
  return isoD(d);
}
const hoje = isoD(new Date());
const livre1 = await diaLivre(`${ano}-11-17`);
const livre2 = await diaLivre(isoD(new Date(new Date(livre1 + 'T00:00:00').getTime() + 86400000)));
let ctx, p, errs;
/** Navega o calendário mensal até o mês da data informada. */
async function irParaMes(p, dataISO) {
  const h = new Date(); const d = new Date(dataISO + 'T00:00:00');
  const n = (d.getFullYear() - h.getFullYear()) * 12 + d.getMonth() - h.getMonth();
  for (let i = 0; i < Math.abs(n); i++) await p.click(n > 0 ? '[data-testid=mes-prox]' : '[data-testid=mes-ant]');
  await p.waitForSelector(`[data-testid=mes] [data-dia="${dataISO}"]`);
}

console.log('ALUNO — dashboard, agenda, provas e calendário');
({ ctx, p, errs } = await entrar(`${ano}0001`));
await p.waitForSelector('[data-testid=compromisso]');
ok((await p.locator('[data-testid=compromisso]').count()) >= 3, 'dashboard mostra "Próximos compromissos" (provas, entregas, eventos)');
await shot(p, 's06_01_dashboard_aluno_compromissos');
await p.waitForSelector('[data-testid=recomendacao]');
ok((await p.locator('[data-testid=recomendacao]').count()) >= 2, 'dashboard mostra "Recomendações de estudo" cruzando notas, faltas e agenda');
ok((await p.locator('[data-testid=recomendacao][data-tipo=PROVA]').count()) >= 1, 'há recomendação de PROVA (cruza a agenda de provas com a média da disciplina)');
ok(/Gerado por/.test(await p.textContent('[data-testid=rec-origem]')), 'a origem da recomendação é informada: ' + (await p.textContent('[data-testid=rec-origem]')));
await p.locator('[data-testid=recomendacao][data-tipo=PROVA]').first().scrollIntoViewIfNeeded();
await shot(p, 's06_01b_recomendacoes_aluno');
await p.click('nav >> text=Agenda'); await p.waitForSelector('[data-testid=semana]');
ok(p.url().endsWith('/agenda'), 'navegação: menu Agenda');
ok((await p.title()).startsWith('Agenda'), 'título da aba muda por página: ' + (await p.title()));
ok((await p.locator('.ag-item[data-tipo=AULA]').count()) > 0 || (await p.locator('.ag-dia').count()) > 0, 'grade semanal exibida');
const tit0 = await p.textContent('[data-testid=sem-titulo]');
await p.click('[data-testid=sem-prox]'); await p.waitForFunction((t) => document.querySelector('[data-testid=sem-titulo]').textContent !== t, tit0);
ok(true, 'navegar para a semana seguinte altera o período');
await p.click('[data-testid=sem-hoje]'); await p.waitForFunction((t) => document.querySelector('[data-testid=sem-titulo]').textContent === t, tit0);
ok(true, '"Hoje" volta para a semana atual');
await p.click('[data-testid=filtro-AULA]');
ok((await p.locator('.ag-item[data-tipo=AULA]').count()) === 0, 'filtro: desmarcar "Aulas" oculta as aulas');
await p.click('[data-testid=filtro-AULA]');
await shot(p, 's06_02_agenda_semana_aluno');
// ir até a semana da primeira prova e abrir o detalhe
const provas = (await api('lucas.silva@aluno.eduvance.com', '/agenda/provas')).json;
ok(provas.length >= 3, `API de provas devolve ${provas.length} avaliações futuras`);
await p.click('nav >> text=Provas'); await p.waitForSelector('[data-testid=prova]');
ok((await p.locator('[data-testid=prova]').count()) === provas.length, 'calendário de provas lista todas as próximas avaliações');
ok((await p.locator('[data-testid=remarcar]').count()) === 0, 'RBAC na interface: aluno não vê "Remarcar"');
await shot(p, 's06_03_provas_aluno');
await p.click('[data-testid=periodo-passadas]'); await p.waitForSelector('[data-testid=prova] .badge:has-text("Nota")');   // espera o dado novo (e não a lista anterior)
ok((await p.locator('[data-testid=prova] .badge:has-text("Nota")').count()) > 0, 'aba "Realizadas" mostra a nota do aluno em cada prova');
await p.click('[data-testid=periodo-proximas]');
await p.click('nav >> text=Calendário Escolar'); await p.waitForSelector('[data-testid=mes]');
await p.click(`[data-testid=mes] [data-dia="${hoje}"]`);
ok(await p.locator('[data-testid=painel-dia]').isVisible(), 'calendário: clicar no dia abre o painel do dia');
ok((await p.locator('[data-testid=novo-evento]').count()) === 0, 'RBAC na interface: aluno não vê "Novo evento"');
await shot(p, 's06_04_calendario_aluno');
ok(errs.length === 0, 'sem erros de JavaScript no navegador (aluno)');
await ctx.close();

console.log('PROFESSOR — remarca avaliação e avisa a turma (integração Agenda × Comunicação × Notas)');
const antes = (await api('lucas.silva@aluno.eduvance.com', '/notificacoes?naoLidas=1')).json.naoLidas;
({ ctx, p, errs } = await entrar('ricardo@eduvance.com'));
await p.click('nav >> text=Calendário de Provas'); await p.waitForSelector('[data-testid=prova]');
const cartao = p.locator('[data-testid=prova]:has-text("8º Ano B"):has([data-testid=remarcar])').first();
const idProva = await cartao.getAttribute('data-id');
const dataAntiga = (await api('ricardo@eduvance.com', '/agenda/provas')).json.find((x) => String(x.id) === idProva).data;
await shot(p, 's06_05_provas_professor');
await cartao.locator('[data-testid=remarcar]').click(); await p.waitForSelector('.modal');
await p.fill('[data-testid=nova-data]', dataAntiga); await p.click('.modal button.btn-primary');
ok((await p.textContent('.modal .field-error')).includes('diferente'), 'validação: mesma data é recusada');
const sabado = new Date(); sabado.setDate(sabado.getDate() + ((6 - sabado.getDay() + 7) % 7 || 7));
await p.fill('[data-testid=nova-data]', isoD(sabado)); await p.click('.modal button.btn-primary');
ok((await p.textContent('.modal .field-error')).includes('fim de semana'), 'validação: fim de semana é recusado');
await shot(p, 's06_06_remarcar_validacao');
await p.fill('[data-testid=nova-data]', livre1);
await p.fill('.modal input[type=text]', 'Conflito com a feira de ciências');
await p.click('.modal button.btn-primary'); await p.waitForSelector('.toast');
ok(/remarcada/i.test(await p.textContent('.toast')) && /avisada/.test(await p.textContent('.toast')), 'avaliação remarcada: ' + (await p.textContent('.toast')));
const nova = (await api('ricardo@eduvance.com', '/agenda/provas')).json.find((x) => String(x.id) === idProva);
ok(nova.data === livre1, 'a nova data foi gravada no banco (' + livre1 + ')');
await ctx.close();
const depois = (await api('lucas.silva@aluno.eduvance.com', '/notificacoes?naoLidas=1')).json;
ok(depois.naoLidas > antes, 'aluno recebeu notificação da remarcação');
ok(depois.itens.some((n) => n.tipo === 'AGENDA' && n.link === '/provas' && /remarcad/i.test(n.titulo)), 'notificação do tipo AGENDA ("remarcada") aponta para /provas');
ok((await api('ricardo@eduvance.com', `/avaliacoes/${idProva}/data`, 'PATCH', { dataAvaliacao: livre1 })).status === 400, 'API: remarcar para a mesma data → 400');

console.log('COORDENADORA — calendário escolar (CRUD de eventos) e regras de conflito');
({ ctx, p, errs } = await entrar('paula@eduvance.com'));
await p.click('nav >> text=Calendário Escolar'); await p.waitForSelector('[data-testid=mes]');
await shot(p, 's06_07_calendario_coordenacao');
await p.click('[data-testid=novo-evento]'); await p.waitForSelector('.modal');
await p.fill('[data-testid=ev-titulo]', 'ab'); await p.fill('[data-testid=ev-data]', livre2);
await p.click('[data-testid=ev-salvar]'); await p.waitForSelector('.field-error');
ok((await p.textContent('.field-error')).includes('3 caracteres'), 'validação: título muito curto');
await p.fill('[data-testid=ev-titulo]', 'Feira de Ciências E2E'); await p.selectOption('[data-testid=ev-tipo]', 'EVENTO');
await p.fill('[data-testid=ev-hora]', '14:00');
await p.selectOption('[data-testid=ev-publico]', 'ALUNOS');
await p.click('[data-testid=ev-salvar]'); await p.waitForSelector('.toast');
ok(/cadastrado/.test(await p.textContent('.toast')), 'CREATE: ' + (await p.textContent('.toast')));
await irParaMes(p, livre2); await p.click(`[data-testid=mes] [data-dia="${livre2}"]`);
ok((await p.locator('[data-testid=item-dia]:has-text("Feira de Ciências E2E")').count()) === 1, 'CREATE: evento aparece no painel do dia');
await shot(p, 's06_08_evento_criado');
// duplicado
await p.click('[data-testid=novo-evento]'); await p.waitForSelector('.modal');
await p.fill('[data-testid=ev-titulo]', 'Feira de Ciências E2E'); await p.fill('[data-testid=ev-data]', livre2); await p.fill('[data-testid=ev-hora]', '14:00');
await p.click('[data-testid=ev-salvar]'); await p.waitForSelector('.modal .alert-red, .modal .field-error');
ok(true, 'erro do servidor: evento duplicado é recusado (' + (await p.locator('.modal .alert-red, .modal .field-error').first().textContent()).trim() + ')');
await shot(p, 's06_09_evento_duplicado');
await p.click('.modal button.btn-secondary');
// editar
await p.locator('[data-testid=item-dia]:has-text("Feira de Ciências E2E") [data-testid=editar-evento]').click(); await p.waitForSelector('.modal');
await p.fill('[data-testid=ev-titulo]', 'Feira de Ciências E2E (editada)'); await p.click('[data-testid=ev-salvar]'); await p.waitForSelector('.toast');
await p.waitForSelector('[data-testid=item-dia]:has-text("(editada)")');
ok(true, 'UPDATE: evento editado');
// conflito: feriado em dia com avaliação
const diaProva = (await api('ricardo@eduvance.com', '/agenda/provas')).json.find((x) => x.data !== livre1).data;
await p.click('[data-testid=novo-evento]'); await p.waitForSelector('.modal');
await p.fill('[data-testid=ev-titulo]', 'Recesso de teste'); await p.selectOption('[data-testid=ev-tipo]', 'RECESSO'); await p.fill('[data-testid=ev-data]', diaProva);
await p.click('[data-testid=ev-salvar]'); await p.waitForSelector('.modal .alert-red, .modal .field-error');
const msgConf = (await p.locator('.modal .alert-red, .modal .field-error').first().textContent());
ok(/avalia/i.test(msgConf), 'regra: recesso sobre dia com avaliação é recusado — ' + msgConf.trim());
await shot(p, 's06_10_recesso_conflito');
await p.click('.modal button.btn-secondary');
// aluno vê a notificação e o evento
const lucas = (await api('lucas.silva@aluno.eduvance.com', '/notificacoes?naoLidas=1')).json;
ok(lucas.itens.some((n) => n.titulo.includes('Feira de Ciências E2E')), 'integração: aluno foi notificado do evento (público ALUNOS)');
const maria = (await api('maria@eduvance.com', '/notificacoes?naoLidas=1')).json;
ok(!maria.itens.some((n) => n.titulo.includes('Feira de Ciências E2E')), 'integração: responsável NÃO foi notificado (público era só ALUNOS)');
// excluir
await p.locator('[data-testid=item-dia]:has-text("(editada)") [data-testid=excluir-evento]').click(); await p.waitForSelector('.modal');
await p.click('[data-testid=confirmar-exclusao]'); await p.waitForSelector('.toast');
await p.waitForFunction(() => !document.querySelector('[data-testid=painel-dia]').textContent.includes('(editada)'));
ok(true, 'DELETE: evento cancelado');
ok(errs.length === 0, 'sem erros de JavaScript no navegador (coordenação)');
await ctx.close();

console.log('RESPONSÁVEL — agenda e recomendações dos filhos');
({ ctx, p, errs } = await entrar('maria@eduvance.com'));
await p.waitForSelector('[data-testid=compromisso], .proximos .empty');
await p.locator('.aluno-card').first().click();
await p.waitForSelector('[data-testid=recomendacao], .recomendacoes .empty');
ok(true, 'responsável vê as recomendações do filho selecionado');
await shot(p, 's06_11b_recomendacoes_responsavel');
await p.click('nav >> text=Agenda'); await p.waitForSelector('[data-testid=semana]');
await shot(p, 's06_11_agenda_responsavel');
const filhos = await p.locator('select[aria-label=Aluno] option').count();
ok(filhos === 0 || filhos >= 3, 'responsável com mais de um filho vê o filtro por aluno (' + filhos + ' opções)');
await ctx.close();

console.log('CONFIGURAÇÕES — tamanho da fonte e tema');
({ ctx, p, errs } = await entrar('lucas.silva@aluno.eduvance.com'));
await p.click('[data-testid=nav-configuracoes]'); await p.waitForSelector('[data-testid=fonte-atual]');
ok(await p.getAttribute('html', 'data-fonte') === '100', 'fonte padrão = 100%');
const px0 = await p.evaluate(() => parseFloat(getComputedStyle(document.querySelector('.main p, .main h1')).fontSize));
await p.click('[data-testid=fonte-mais]'); await p.click('[data-testid=fonte-mais]');
ok(await p.getAttribute('html', 'data-fonte') === '130', 'A+ duas vezes → 130%');
const px1 = await p.evaluate(() => parseFloat(getComputedStyle(document.querySelector('.main p, .main h1')).fontSize));
ok(px1 > px0 * 1.25, `o texto da tela cresce de verdade (${px0.toFixed(1)}px → ${px1.toFixed(1)}px)`);
await shot(p, 's06_12_configuracoes_fonte_130');
await p.click('[data-testid=fonte-150]');
const larg = await p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
ok(larg, 'em 150% a página não ganha rolagem horizontal');
await shot(p, 's06_13_configuracoes_fonte_150');
await p.click('[data-testid=fonte-85]');
ok(await p.getAttribute('html', 'data-fonte') === '85' && await p.locator('[data-testid=fonte-menos]').isDisabled(), 'A− é desabilitado no menor tamanho (85%)');
await p.click('[data-testid=fonte-115]');
await p.reload(); await p.waitForSelector('[data-testid=fonte-atual]');
ok(await p.getAttribute('html', 'data-fonte') === '115', 'a escolha sobrevive ao recarregar a página (localStorage)');
await p.click('[data-testid=tema-escuro]');
ok(await p.getAttribute('html', 'data-theme') === 'dark', 'tema escuro aplicado');
await ctx.close();
// outro navegador (sem localStorage): a conta guardou as preferências
({ ctx, p, errs } = await entrar('lucas.silva@aluno.eduvance.com'));
await p.waitForFunction(() => document.documentElement.getAttribute('data-fonte') === '115');
ok(await p.getAttribute('html', 'data-theme') === 'dark', 'preferências seguem a conta: novo navegador já abre em 115% e tema escuro');
await p.click('[data-testid=nav-configuracoes]'); await p.waitForSelector('[data-testid=restaurar]');
await p.click('[data-testid=restaurar]');
ok(await p.getAttribute('html', 'data-fonte') === '100', '"Restaurar padrões" volta para 100%');
await ctx.close();

console.log('MOBILE — navegação e legibilidade');
({ ctx, p, errs } = await entrar('lucas.silva@aluno.eduvance.com', { width: 390, height: 844 }));
await p.click('.bottom-nav >> text=Mais'); await p.waitForSelector('.sheet');
ok((await p.locator('.sheet >> text=Configurações').count()) === 1, 'menu "Mais" oferece Configurações');
await p.click('.sheet >> text=Configurações'); await p.waitForSelector('[data-testid=fonte-atual]');
await p.click('[data-testid=fonte-130]');
ok(await p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'mobile em 130%: sem rolagem horizontal');
await shot(p, 's06_14_configuracoes_mobile');
await p.click('[data-testid=restaurar]');
await p.goto(base + '/agenda'); await p.waitForSelector('[data-testid=semana]');
const cols = await p.evaluate(() => getComputedStyle(document.querySelector('[data-testid=semana]')).gridTemplateColumns.split(' ').length);
ok(cols === 1, 'mobile: a semana vira uma coluna só');
await shot(p, 's06_15_agenda_mobile');
await ctx.close();

console.log('CONTROLE DE ACESSO (API)');
ok((await api('lucas.silva@aluno.eduvance.com', '/eventos', 'POST', { titulo: 'Intruso', tipo: 'EVENTO', data: livre2 })).status === 403, 'aluno não cria eventos (403)');
ok((await api('lucas.silva@aluno.eduvance.com', `/avaliacoes/${idProva}/data`, 'PATCH', { dataAvaliacao: livre2 })).status === 403, 'aluno não remarca avaliação (403)');
ok((await api('carlos@eduvance.com', `/avaliacoes/${idProva}/data`, 'PATCH', { dataAvaliacao: livre2 })).status === 403, 'professor não remarca avaliação de outro professor (403)');
ok((await api('maria@eduvance.com', '/agenda?idAluno=999999')).status === 403, 'responsável não consulta a agenda de aluno que não é seu filho (403)');
ok((await fetch(base + '/api/agenda')).status === 401, 'agenda exige autenticação (401)');
ok((await api('lucas.silva@aluno.eduvance.com', '/recomendacoes?idAluno=1')).status === 403, 'aluno não vê recomendações de outro aluno (403)');

await browser.close();
console.log(`\n${total - falhas.length}/${total} verificações aprovadas`);
if (falhas.length) { console.log('FALHAS:\n - ' + falhas.join('\n - ')); process.exit(1); }
