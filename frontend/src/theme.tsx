import { useEffect, useState } from 'react';
import { Icon } from './icons';

export type Tema = 'light' | 'dark';
const CHAVE = 'eduvance:tema';

function guardado(): Tema | null {
  try {
    const t = localStorage.getItem(CHAVE);
    return t === 'dark' || t === 'light' ? t : null;
  } catch {
    return null;
  }
}

function doSistema(): Tema {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function aplicar(t: Tema) {
  document.documentElement.setAttribute('data-theme', t);
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', t === 'dark' ? '#0c181b' : '#f1f7f7');
  window.dispatchEvent(new CustomEvent('eduvance:tema', { detail: t }));
}

/** Tema atual: o escolhido pela pessoa (salvo no navegador) ou, na falta dele, o do sistema operacional. */
export function useTema(): [Tema, () => void] {
  const [tema, setTema] = useState<Tema>(() => (document.documentElement.getAttribute('data-theme') as Tema) || guardado() || doSistema());

  useEffect(() => {
    const aoMudar = (e: Event) => setTema((e as CustomEvent<Tema>).detail);
    window.addEventListener('eduvance:tema', aoMudar);
    // Sem escolha salva, acompanha o tema do sistema em tempo real.
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)');
    const aoMudarSistema = () => { if (!guardado()) aplicar(doSistema()); };
    mq?.addEventListener?.('change', aoMudarSistema);
    return () => { window.removeEventListener('eduvance:tema', aoMudar); mq?.removeEventListener?.('change', aoMudarSistema); };
  }, []);

  function alternar() {
    const novo: Tema = tema === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem(CHAVE, novo); } catch { /* navegador sem armazenamento: vale só nesta sessão */ }
    aplicar(novo);
  }
  return [tema, alternar];
}

/** Botão que alterna entre o tema claro e o escuro. */
export function BotaoTema({ className = 'icon-btn ghost' }: { className?: string }) {
  const [tema, alternar] = useTema();
  const escuro = tema === 'dark';
  const rotulo = escuro ? 'Mudar para o tema claro' : 'Mudar para o tema escuro';
  return (
    <button type="button" className={`${className} tema-btn`} onClick={alternar} aria-label={rotulo} title={rotulo} aria-pressed={escuro} data-testid="tema">
      <Icon name={escuro ? 'sun' : 'moon'} size={18} />
    </button>
  );
}
