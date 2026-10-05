import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { api, ApiError } from './api';
import { iniciais, mesAno } from './format';
import { Icon } from './icons';

// ---------- Marca ----------------------------------------------------------
export function Logo({ size = 32, texto = true }: { size?: number; texto?: boolean }) {
  return (
    <div className="logo">
      <span className="logo-mark" style={{ width: size, height: size }}>
        <Icon name="cap" size={Math.round(size * 0.6)} />
      </span>
      {texto && <span className="logo-text">Eduvance</span>}
    </div>
  );
}

// ---------- Blocos ---------------------------------------------------------
export function Card({ title, action, children, className = '', id }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string; id?: string }) {
  return (
    <section className={`card ${className}`} id={id}>
      {(title || action) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export type Tone = 'green' | 'amber' | 'red' | 'blue' | 'gray' | 'teal';
export function Badge({ tone = 'gray', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function Stat({ label, value, badge, tone, icon }: { label: string; value: ReactNode; badge?: string; tone?: Tone; icon: Parameters<typeof Icon>[0]['name'] }) {
  return (
    <div className="card stat">
      <div className="stat-top">
        <span className="stat-label">{label}</span>
        <span className="stat-icon"><Icon name={icon} size={16} /></span>
      </div>
      <div className="stat-value">
        <strong>{value}</strong>
        {badge && <Badge tone={tone}>{badge}</Badge>}
      </div>
    </div>
  );
}

export function Avatar({ nome, size = 40 }: { nome: string; size?: number }) {
  return (
    <span className="avatar" style={{ width: size, height: size, fontSize: size * 0.38 }} aria-hidden="true">
      {iniciais(nome)}
    </span>
  );
}

export function PageHeader({ titulo, subtitulo, extra }: { titulo: string; subtitulo?: string; extra?: ReactNode }) {
  const toast = useToast();
  return (
    <header className="page-header">
      <div>
        <h1>{titulo}</h1>
        {subtitulo && <p>{subtitulo}</p>}
      </div>
      <div className="page-header-tools">
        {extra}
        <button className="icon-btn" aria-label="Notificações" title="Notificações" onClick={() => toast('Central de notificações prevista para uma próxima Sprint (PB21).', 'info')}>
          <Icon name="bell" size={18} />
        </button>
        <span className="date-pill"><Icon name="calendar" size={16} />{mesAno()}</span>
      </div>
    </header>
  );
}

export function Loading({ texto = 'Carregando…' }: { texto?: string }) {
  return <div className="loading" role="status"><span className="spinner" />{texto}</div>;
}

export function ErrorBox({ erro, onRetry }: { erro: string; onRetry?: () => void }) {
  return (
    <div className="alert alert-red" role="alert">
      <Icon name="alert" size={18} />
      <span>{erro}</span>
      {onRetry && <button className="link-btn" onClick={onRetry}>Tentar novamente</button>}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}

// ---------- Formulários ----------------------------------------------------
export function Field({ label, error, hint, children }: { label: string; error?: string; hint?: string; children: ReactNode }) {
  return (
    <label className={`field ${error ? 'has-error' : ''}`}>
      <span className="field-label">{label}</span>
      {children}
      {error ? <span className="field-error">{error}</span> : hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  );
}

export function Modal({ titulo, onClose, children, largo }: { titulo: string; onClose: () => void; children: ReactNode; largo?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    ref.current?.querySelector<HTMLElement>('input,select,textarea,button')?.focus();
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${largo ? 'modal-lg' : ''}`} role="dialog" aria-modal="true" aria-label={titulo} ref={ref}>
        <header>
          <h2>{titulo}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Fechar"><Icon name="x" size={18} /></button>
        </header>
        {children}
      </div>
    </div>
  );
}

// ---------- Toasts ---------------------------------------------------------
type ToastKind = 'ok' | 'erro' | 'info';
const ToastCtx = createContext<(msg: string, kind?: ToastKind) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [itens, setItens] = useState<{ id: number; msg: string; kind: ToastKind }[]>([]);
  const seq = useRef(0);
  const push = useCallback((msg: string, kind: ToastKind = 'ok') => {
    const id = ++seq.current;
    setItens((x) => [...x, { id, msg, kind }]);
    setTimeout(() => setItens((x) => x.filter((i) => i.id !== id)), 4200);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts" aria-live="polite">
        {itens.map((i) => (
          <div key={i.id} className={`toast toast-${i.kind}`}>
            <Icon name={i.kind === 'erro' ? 'alert' : i.kind === 'info' ? 'info' : 'checkCircle'} size={18} />
            {i.msg}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

// ---------- Dados ----------------------------------------------------------
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(path !== null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let vivo = true;
    setCarregando(true);
    api<T>(path)
      .then((d) => vivo && (setData(d), setErro(null)))
      .catch((e: ApiError) => vivo && setErro(e.message))
      .finally(() => vivo && setCarregando(false));
    return () => { vivo = false; };
  }, [path, tick]);

  const recarregar = useCallback(() => setTick((t) => t + 1), []);
  return { data, setData, erro, carregando, recarregar };
}
