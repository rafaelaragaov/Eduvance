// Roteiro E2E da Sprint 03 — versão ESTÁVEL (Sprint 06).
// Uso:  node roteiro_e2e.mjs [URL_BASE] [PASTA_DE_SAIDA]     (precisa de: npm i playwright)
// O que mudou em relação à primeira versão, apontada como instável na correção da Sprint 05:
//  1. nenhuma espera por tempo fixo: toda espera é por elemento/estado (waitForSelector/waitForFunction);
//  2. dados únicos por execução (sufixo de tempo) — o roteiro roda quantas vezes quiser no mesmo banco;
//  3. seletores por papel/texto/atributo, sem depender da ordem das linhas;
//  4. cada bloco abre o seu próprio contexto de navegador (sem estado compartilhado) e é limpo no fim;
//  5. falha mostra a mensagem e sai com código 1 (serve para CI).
import { chromium } from 'playwright';
const base = process.argv[2] ?? 'http://localhost:5058';
const out = process.argv[3] ?? new URL('.', import.meta.url).pathname;
const ano = new Date().getFullYear();
const sufixo = Date.now().toString().slice(-7);
const browser = await chromium.launch({ args: ['--no-sandbox'], ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
const falhas = []; let total = 0;
const ok = (c, m) => { total++; console.log(c ? '  ✔' : '  ✖', m); if (!c) falhas.push(m); };
const shot = (p, f) => p.screenshot({ path: `${out}/${f}.png` });

async function sessao(vp = { width: 1440, height: 900 }) {
  const ctx = await browser.newContext({ viewport: vp, locale: 'pt-BR' });
  const p = await ctx.newPage(); const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  return { ctx, p, errs };
}
async function login(p, ident, senha = 'senha123') {
  await p.goto(base);
  await p.fill('input[type=text]', ident); await p.fill('input[type=password]', senha);
  await p.click('button.btn-primary');
}
async function entrar(ident, senha) { const s = await sessao(); await login(s.p, ident, senha); await s.p.waitForSelector('.main h1'); return s; }
const toast = async (p) => { const t = p.locator('.toast').last(); await t.waitFor(); return (await t.textContent()) ?? ''; };

console.log('LOGIN — mensagem genérica e entrada por matrícula');
let s = await sessao();
await login(s.p, 'ricardo@eduvance.com', 'senha-errada');
await s.p.waitForSelector('.alert-red');
const msg = (await s.p.textContent('.alert-red')) ?? '';
ok(/inválid|incorret/i.test(msg) && !/não existe|não encontrado/i.test(msg), 'credenciais erradas: mensagem genérica — "' + msg.trim() + '"');
await s.ctx.close();
s = await entrar(`${ano}0001`);
ok((await s.p.textContent('.main h1')).includes('Lucas'), 'aluno entra com a matrícula e vê o próprio dashboard');
ok(s.errs.length === 0, 'sem erros de JavaScript');
await s.ctx.close();

console.log('ADMIN — cadastra um aluno pela interface e o aluno entra com a matrícula nova');
const matricula = `9${sufixo}`;
s = await entrar('admin@eduvance.com', 'admin123');
await s.p.click('nav >> text=Usuários'); await s.p.waitForSelector('table');
await s.p.click('button:has-text("Novo usuário")'); await s.p.waitForSelector('.modal');
await s.p.click('.modal button.btn-primary'); await s.p.waitForSelector('.modal .field-error');
ok((await s.p.locator('.modal .field-error').count()) >= 2, 'validação: formulário vazio mostra erros nos campos');
await s.p.fill('.modal input[type=text] >> nth=0', `Aluno Teste ${sufixo}`);
await s.p.fill('.modal input[type=email]', `aluno.${sufixo}@aluno.eduvance.com`);
await s.p.fill('.modal input[type=password]', 'senha1234');
await s.p.selectOption('.modal select >> nth=0', 'ALUNO');
await s.p.fill('.modal input[placeholder*="8º"]', '8º Ano');
await s.p.fill('.modal label:has-text("Matrícula") input', matricula);
await s.p.fill('.modal input[type=date]', '2012-05-20');
await s.p.click('.modal button.btn-primary');
ok(/cadastrado/i.test(await toast(s.p)), 'CREATE: usuário cadastrado');
await s.p.fill('input[type=search]', matricula);
await s.p.waitForSelector(`tr:has-text("Aluno Teste ${sufixo}")`);
ok(true, 'READ: aluno novo aparece na lista (busca por matrícula)');
await shot(s.p, 's03e2e_01_usuario_criado');
await s.ctx.close();
s = await sessao(); await login(s.p, matricula, 'senha1234'); await s.p.waitForSelector('.main h1');
ok((await s.p.textContent('.main h1')).includes('Aluno'), 'aluno recém-cadastrado entra com a própria matrícula');
await s.p.goto(base + '/usuarios'); await s.p.waitForSelector('.soon');
ok((await s.p.textContent('.soon')).includes('Acesso restrito'), 'RBAC na interface: aluno em /usuarios vê "Acesso restrito"');
await s.ctx.close();

console.log('PROFESSOR — CRUD de atividades (criar, validar, editar, persistir, excluir)');
const titulo = `Lista de exercícios ${sufixo}`;
s = await entrar('ricardo@eduvance.com');
await s.p.click('nav >> text=Atividades'); await s.p.waitForSelector('table');
await s.p.click('button:has-text("Nova atividade")'); await s.p.waitForSelector('.modal');
await s.p.click('.modal button.btn-primary'); await s.p.waitForSelector('.modal .field-error');
ok(true, 'validação: título obrigatório — "' + (await s.p.textContent('.modal .field-error')).trim() + '"');
await s.p.fill('.modal input[type=text]', titulo);
await s.p.click('.modal button.btn-primary');
ok(/publicada/i.test(await toast(s.p)), 'CREATE: atividade publicada');
await s.p.waitForSelector(`tr:has-text("${titulo}")`);
await s.p.locator(`tr:has-text("${titulo}") button:has-text("Editar")`).click(); await s.p.waitForSelector('.modal');
await s.p.fill('.modal input[type=text]', titulo + ' (revisada)');
await s.p.click('.modal button.btn-primary');
await s.p.waitForSelector(`tr:has-text("${titulo} (revisada)")`);
await s.p.reload(); await s.p.waitForSelector(`tr:has-text("${titulo} (revisada)")`);
ok(true, 'UPDATE: a edição permanece após recarregar a página (persistência)');
await s.p.locator(`tr:has-text("(revisada)") button[aria-label^="Excluir"]`).click(); await s.p.waitForSelector('.modal');
await shot(s.p, 's03e2e_02_excluir_confirmacao');
await s.p.click('.modal button.btn-danger');
await s.p.waitForSelector(`tr:has-text("${titulo}")`, { state: 'detached' });
ok(true, 'DELETE: atividade excluída depois da confirmação');
ok(s.errs.length === 0, 'sem erros de JavaScript');
await s.ctx.close();

console.log('ALUNO e RESPONSÁVEL — papéis na mesma tela de atividades');
s = await entrar(`${ano}0001`);
await s.p.click('nav >> text=Atividades'); await s.p.waitForSelector('.row');
ok((await s.p.locator('button:has-text("Nova atividade")').count()) === 0, 'aluno não vê "Nova atividade"');
const botao = s.p.locator('.row button:has-text("Marcar como entregue")').first();
const rotulo = await botao.locator('xpath=ancestor::div[contains(@class,"row")][1]').locator('strong').first().textContent();
await botao.click();
await s.p.waitForSelector(`.row:has(strong:text-is("${rotulo}")) button:has-text("Desfazer entrega")`);
ok(true, 'aluno marca a entrega de "' + rotulo + '"');
await s.p.locator(`.row:has(strong:text-is("${rotulo}")) button:has-text("Desfazer entrega")`).click();
await s.p.waitForSelector(`.row:has(strong:text-is("${rotulo}")) button:has-text("Marcar como entregue")`);
ok(true, 'e desfaz a entrega (estado restaurado)');
await s.ctx.close();
s = await entrar('maria@eduvance.com');
await s.p.click('nav >> text=Atividades'); await s.p.waitForSelector('.row');
ok((await s.p.locator('button:has-text("Marcar como entregue"), button:has-text("Nova atividade")').count()) === 0, 'responsável só consulta (sem botões de ação)');
await s.ctx.close();

await browser.close();
console.log(`\n${total - falhas.length}/${total} verificações aprovadas`);
if (falhas.length) { console.log('FALHAS:\n - ' + falhas.join('\n - ')); process.exit(1); }
