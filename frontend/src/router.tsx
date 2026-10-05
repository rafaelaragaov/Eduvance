import { AnchorHTMLAttributes, MouseEvent, useEffect, useState } from 'react';

/** Roteador mínimo baseado na History API (sem dependências externas). */
const listeners = new Set<() => void>();

export function navigate(to: string, replace = false) {
  if (replace) history.replaceState({}, '', to);
  else history.pushState({}, '', to);
  listeners.forEach((l) => l());
  window.scrollTo(0, 0);
}

export function usePath(): string {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const f = () => setPath(window.location.pathname);
    listeners.add(f);
    window.addEventListener('popstate', f);
    return () => {
      listeners.delete(f);
      window.removeEventListener('popstate', f);
    };
  }, []);
  return path;
}

export function Link({ to, onClick, ...rest }: { to: string } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  const click = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    e.preventDefault();
    navigate(to);
  };
  return <a href={to} onClick={click} {...rest} />;
}
