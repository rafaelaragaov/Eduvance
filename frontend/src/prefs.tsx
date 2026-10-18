import { useSyncExternalStore } from 'react';
import { api, tokenStore } from './api';
import { Icon } from './icons';

/** Preferências de aparência (página Configurações): tamanho do texto e tema.
 *  Valem na hora, ficam no navegador (para a tela de login) e, com a pessoa logada, são salvas na conta. */
export type Fonte = 85 | 100 | 115 | 130 | 150;
export type Tema = 'claro' | 'escuro' | 'auto';
export interface Prefs { fonte: Fonte; tema: Tema }

export const FONTES: { valor: Fonte; rotulo: string }[] = [
  { valor: 85, rotulo: 'Pequeno' },
  { valor: 100, rotulo: 'Padrão' },
  { valor: 115, rotulo: 'Médio' },
  { valor: 130, rotulo: 'Grande' },
  { valor: 150, rotulo: 'Muito grande' },
];
export const PADRAO: Prefs = { fonte: 100, tema: 'auto' };
const CHAVE = 'eduvance:prefs';

const fonteValida = (v: unknown): v is Fonte => FONTES.some((f) => f.valor === v);
const temaValido = (v: unknown): v is Tema => v === 'claro' || v === 'escuro' || v === 'auto';

function lerLocal(): Prefs {
  try {
    const j = JSON.parse(localStorage.getItem(CHAVE) ?? 'null');
    if (j && typeof j === 'object') return { fonte: fonteValida(j.fonte) ? j.fonte : PADRAO.fonte, tema: temaValido(j.tema) ? j.tema : PADRAO.tema };
    const antigo = localStorage.getItem('eduvance:tema'); // versão anterior do modo escuro
    if (antigo === 'dark' || antigo === 'light') return { ...PADRAO, tema: antigo === 'dark' ? 'escuro' : 'claro' };
  } catch { /* storage indisponível */ }
  return { ...PADRAO };
}

const sistemaEscuro = () => !!window.matchMedia?.('(prefers-color-scheme: dark)').matches;
export const temaEfetivo = (t: Tema): 'light' | 'dark' => (t === 'auto' ? (sistemaEscuro() ? 'dark' : 'light') : t === 'escuro' ? 'dark' : 'light');

function aplicar(p: Prefs) {
  const raiz = document.documentElement;
  const efetivo = temaEfetivo(p.tema);
  raiz.setAttribute('data-theme', efetivo);
  raiz.setAttribute('data-fonte', String(p.fonte));
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', efetivo === 'dark' ? '#0c181b' : '#f1f7f7');
}

let atual: Prefs = lerLocal();
const ouvintes = new Set<() => void>();
const avisar = () => ouvintes.forEach((o) => o());

function gravar(p: Prefs) {
  atual = p;
  try { localStorage.setItem(CHAVE, JSON.stringify(p)); } catch { /* vale só nesta sessão */ }
  aplicar(p);
  avisar();
}

aplicar(atual);
// Tema "automático": acompanha o sistema operacional em tempo real.
window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener?.('change', () => { if (atual.tema === 'auto') { aplicar(atual); avisar(); } });

/** Altera preferências. Com a pessoa logada, também salva na conta (falha de rede não desfaz a escolha local). */
export function definirPrefs(parcial: Partial<Prefs>): Promise<void> {
  gravar({ ...atual, ...parcial });
  if (!tokenStore.get()) return Promise.resolve();
  return api('/preferencias', { method: 'PUT', body: parcial }).then(() => undefined, () => undefined);
}

export function restaurarPadrao(): Promise<void> {
  gravar({ ...PADRAO });
  if (!tokenStore.get()) return Promise.resolve();
  return api('/preferencias', { method: 'DELETE' }).then(() => undefined, () => undefined);
}

/** Depois do login: usa as preferências da conta; se a conta ainda não tem, envia as que a pessoa já escolheu. */
export async function sincronizarComConta(): Promise<void> {
  try {
    const r = await api<Prefs & { salvo: boolean }>('/preferencias');
    if (r.salvo) gravar({ fonte: fonteValida(r.fonte) ? r.fonte : PADRAO.fonte, tema: temaValido(r.tema) ? r.tema : PADRAO.tema });
    else if (atual.fonte !== PADRAO.fonte || atual.tema !== PADRAO.tema) await api('/preferencias', { method: 'PUT', body: atual });
  } catch { /* offline: segue com o que está no navegador */ }
}

export function usePrefs(): Prefs {
  return useSyncExternalStore((cb) => { ouvintes.add(cb); return () => { ouvintes.delete(cb); }; }, () => atual);
}

export const indiceFonte = (f: Fonte) => FONTES.findIndex((x) => x.valor === f);

/** Botão rápido: alterna entre claro e escuro (a escolha "Automático" fica na página Configurações). */
export function BotaoTema({ className = 'icon-btn ghost' }: { className?: string }) {
  const p = usePrefs();
  const escuro = temaEfetivo(p.tema) === 'dark';
  const rotulo = escuro ? 'Mudar para o tema claro' : 'Mudar para o tema escuro';
  return (
    <button type="button" className={`${className} tema-btn`} onClick={() => definirPrefs({ tema: escuro ? 'claro' : 'escuro' })}
      aria-label={rotulo} title={rotulo} aria-pressed={escuro} data-testid="tema">
      <Icon name={escuro ? 'sun' : 'moon'} size={18} />
    </button>
  );
}
