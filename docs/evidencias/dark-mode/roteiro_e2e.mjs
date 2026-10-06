import { chromium } from '/opt/npm-tools/node_modules/playwright/index.mjs';
const out = '/home/claude/Eduvance/docs/evidencias/dark-mode';
const base = 'http://localhost:5058';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox'] });
const falhas = [];
const ok = (c, m) => { console.log(c ? '  ✔' : '  ✖', m); if (!c) falhas.push(m); };
const tema = (p) => p.evaluate(() => document.documentElement.getAttribute('data-theme'));
const bg = (p) => p.evaluate(() => getComputedStyle(document.body).backgroundColor);
async function ctxNovo(opts = {}) { const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, ...opts }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', (e) => errs.push(e.message)); return { ctx, p, errs }; }
async function entrar(p, ident, senha = 'senha123') { await p.fill('input[type=text]', ident); await p.fill('input[type=password]', senha); await p.click('button.btn-primary'); await p.waitForSelector('.main h1'); }

console.log('LOGIN — tema do sistema e botão');
{
  const { ctx, p } = await ctxNovo({ colorScheme: 'light' });
  await p.goto(base); await p.waitForSelector('.login-card');
  ok(await tema(p) === 'light', 'sistema claro → tema claro por padrão');
  ok((await bg(p)) === 'rgb(241, 247, 247)', 'fundo claro');
  await p.screenshot({ path: `${out}/login-claro.png` });
  await p.click('[data-testid=tema]');
  ok(await tema(p) === 'dark', 'botão no login alterna para escuro');
  ok((await bg(p)) === 'rgb(12, 24, 27)', 'fundo escuro aplicado');
  await p.screenshot({ path: `${out}/login-escuro.png` });
  await p.reload(); await p.waitForSelector('.login-card');
  ok(await tema(p) === 'dark', 'escolha persiste após recarregar');
  ok(await p.evaluate(() => localStorage.getItem('eduvance:tema')) === 'dark', 'preferência salva no navegador');
  await ctx.close();
}
{
  const { ctx, p } = await ctxNovo({ colorScheme: 'dark' });
  await p.goto(base); await p.waitForSelector('.login-card');
  ok(await tema(p) === 'dark', 'sistema escuro → tema escuro sem escolha salva');
  await p.emulateMedia({ colorScheme: 'light' }); await p.waitForTimeout(150);
  ok(await tema(p) === 'light', 'acompanha o sistema quando não há escolha salva');
  await p.click('[data-testid=tema]'); await p.emulateMedia({ colorScheme: 'dark' }); await p.waitForTimeout(150);
  ok(await tema(p) === 'dark', 'após escolher, a preferência manda (escuro)');
  await p.click('[data-testid=tema]'); await p.emulateMedia({ colorScheme: 'dark' }); await p.waitForTimeout(150);
  ok(await tema(p) === 'light', 'escolha manual (claro) vence o sistema escuro');
  await ctx.close();
}

console.log('APP — páginas em tema escuro');
const { ctx, p, errs } = await ctxNovo({ colorScheme: 'light' });
await p.goto(base); await entrar(p, 'maria@eduvance.com');
ok(await tema(p) === 'light', 'responsável entra no tema claro');
await p.click('.sidebar [data-testid=tema]');
ok(await tema(p) === 'dark', 'botão da barra lateral alterna');
ok(await p.locator('.sidebar [data-testid=tema]').getAttribute('aria-pressed') === 'true', 'aria-pressed refletido');
ok((await p.evaluate(() => getComputedStyle(document.querySelector('.sidebar')).backgroundColor)) === 'rgb(19, 36, 40)', 'sidebar escura');
ok((await p.evaluate(() => getComputedStyle(document.querySelector('.card')).backgroundColor)) === 'rgb(19, 36, 40)', 'cards escuros');
await p.waitForTimeout(300); await p.screenshot({ path: `${out}/dashboard-responsavel-escuro.png` });
for (const [rota, nome] of [['/comunicados', 'comunicados'], ['/ocorrencias', 'ocorrencias'], ['/boletim', 'boletim']]) {
  await p.goto(base + rota); await p.waitForSelector('.main h1'); await p.waitForTimeout(500);
  ok(await tema(p) === 'dark', `${nome}: tema mantido ao navegar`);
  await p.screenshot({ path: `${out}/${nome}-escuro.png` });
}
// notificações (sino aberto) e modal
await p.goto(base + '/ocorrencias'); await p.waitForSelector('.main h1');
await p.click('.page-header-tools .sino .icon-btn'); await p.waitForTimeout(400);
await p.screenshot({ path: `${out}/sino-escuro.png` });
await p.keyboard.press('Escape');
// Cores ilegíveis: texto de badges/controles tem contraste mínimo 4.5 contra o fundo efetivo?
const lum = (c) => { const [r, g, b] = c.match(/[\d.]+/g).slice(0, 3).map(Number).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };
async function contraste(sel) {
  return p.evaluate((s) => {
    const el = document.querySelector(s); if (!el) return null;
    let bgc = 'rgba(0, 0, 0, 0)', n = el;
    while (n && /rgba\(0, 0, 0, 0\)|transparent/.test(bgc)) { bgc = getComputedStyle(n).backgroundColor; n = n.parentElement; }
    return [getComputedStyle(el).color, bgc];
  }, sel);
}
await p.goto(base + '/comunicados'); await p.waitForSelector('.com-card');
for (const sel of ['.badge', '.btn-primary', '.nav-item.on', '.muted', '.card-link', '.com-card h2', '.sino-badge']) {
  const r = await contraste(sel); if (!r) continue; const c = ratio(r[0], r[1]);
  ok(c >= 4.5, `contraste ${sel} = ${c.toFixed(1)}:1`);
}
await p.goto(base + '/ocorrencias'); await p.waitForSelector('.main h1');
for (const sel of ['.badge-red', '.badge-green', '.badge-amber', '.badge-blue', '.badge-gray', '.ocorrencia strong', '.alert-red']) {
  const r = await contraste(sel); if (!r) continue; const c = ratio(r[0], r[1]);
  ok(c >= 4.5, `contraste ${sel} = ${c.toFixed(1)}:1`);
}
// volta ao claro
await p.click('.sidebar [data-testid=tema]');
ok(await tema(p) === 'light', 'alterna de volta para o claro');
ok((await bg(p)) === 'rgb(241, 247, 247)', 'fundo volta ao claro');
await p.screenshot({ path: `${out}/ocorrencias-claro.png` });
await p.click('.sidebar [data-testid=tema]');
ok(errs.length === 0, 'sem erros JS: ' + errs.join('|'));
await ctx.close();

console.log('PROFESSOR — formulários e notas no escuro');
{
  const { ctx, p, errs } = await ctxNovo({ colorScheme: 'dark' });
  await p.goto(base); await entrar(p, 'ricardo@eduvance.com');
  await p.goto(base + '/notas'); await p.waitForSelector('.main h1'); await p.waitForTimeout(600);
  await p.screenshot({ path: `${out}/notas-escuro.png` });
  await p.goto(base + '/ocorrencias'); await p.waitForSelector('.main h1');
  await p.click('button:has-text("Nova ocorrência")'); await p.waitForSelector('.modal'); await p.waitForTimeout(300);
  ok((await p.evaluate(() => getComputedStyle(document.querySelector('.modal')).backgroundColor)) === 'rgb(19, 36, 40)', 'modal escuro');
  ok((await p.evaluate(() => getComputedStyle(document.querySelector('.modal input, .modal textarea')).backgroundColor)) === 'rgb(19, 36, 40)', 'campos do formulário escuros');
  await p.screenshot({ path: `${out}/modal-escuro.png` });
  ok(errs.length === 0, 'sem erros JS (professor)');
  await ctx.close();
}

console.log('MOBILE');
{
  const { ctx, p } = await ctxNovo({ colorScheme: 'dark', viewport: { width: 390, height: 844 } });
  await p.goto(base); await entrar(p, 'maria@eduvance.com'); await p.waitForTimeout(500);
  ok(await tema(p) === 'dark', 'mobile segue o tema do sistema');
  ok(await p.locator('.mobile-top [data-testid=tema]').isVisible(), 'botão de tema no topo do celular');
  await p.screenshot({ path: `${out}/mobile-escuro.png` });
  await p.click('.mobile-top [data-testid=tema]');
  ok(await tema(p) === 'light', 'botão mobile alterna');
  await p.screenshot({ path: `${out}/mobile-claro.png` });
  await ctx.close();
}
await browser.close();
console.log(falhas.length ? '\nFALHAS: ' + falhas.join('; ') : '\nTODOS OS CHECKS OK');
