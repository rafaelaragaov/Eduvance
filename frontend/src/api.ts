const TOKEN_KEY = 'eduvance.token';

export const tokenStore = {
  get: () => {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set: (t: string) => {
    try { localStorage.setItem(TOKEN_KEY, t); } catch { /* sem storage */ }
  },
  clear: () => {
    try { localStorage.removeItem(TOKEN_KEY); } catch { /* sem storage */ }
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string, public detalhes?: { campo: string; mensagem: string }[]) {
    super(message);
  }
  /** Mensagem de um campo específico (validação do servidor). */
  campo(nome: string): string | undefined {
    return this.detalhes?.find((d) => d.campo === nome)?.mensagem;
  }
}

type Opts = { method?: string; body?: unknown };

export async function api<T = unknown>(path: string, { method = 'GET', body }: Opts = {}): Promise<T> {
  const token = tokenStore.get();
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'Não foi possível conectar ao servidor. Verifique se a API está em execução.');
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && token && !path.startsWith('/auth/login')) {
      tokenStore.clear();
      window.dispatchEvent(new Event('eduvance:logout'));
    }
    throw new ApiError(res.status, data.erro ?? 'Erro inesperado', data.detalhes);
  }
  return data as T;
}
