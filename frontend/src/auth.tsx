import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, tokenStore } from './api';
import type { Usuario } from './types';

interface AuthCtx {
  user: Usuario | null;
  carregando: boolean;
  login: (identificador: string, senha: string) => Promise<Usuario>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(!!tokenStore.get());

  useEffect(() => {
    if (!tokenStore.get()) return;
    api<{ usuario: Usuario }>('/auth/me')
      .then((r) => setUser(r.usuario))
      .catch(() => tokenStore.clear())
      .finally(() => setCarregando(false));
  }, []);

  useEffect(() => {
    const f = () => setUser(null);
    window.addEventListener('eduvance:logout', f);
    return () => window.removeEventListener('eduvance:logout', f);
  }, []);

  const login = useCallback(async (identificador: string, senha: string) => {
    const r = await api<{ token: string; usuario: Usuario }>('/auth/login', { method: 'POST', body: { identificador, senha } });
    tokenStore.set(r.token);
    setUser(r.usuario);
    return r.usuario;
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, carregando, login, logout }), [user, carregando, login, logout]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAuth fora do AuthProvider');
  return c;
}
