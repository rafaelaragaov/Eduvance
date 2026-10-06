import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import { Link } from '../router';
import type { NotasTurma, TurmaDisciplina } from '../types';
import { Card, Empty, ErrorBox, Loading, useToast } from '../ui';

/** Lançamento de notas (PB11) - grava no banco ao sair do campo (blur) ou ao pressionar Enter. */
export default function NotasRapido({ completo = false, titulo = 'Lançamento de Notas Rápido' }: { completo?: boolean; titulo?: string }) {
  const toast = useToast();
  const [tds, setTds] = useState<TurmaDisciplina[]>([]);
  const [td, setTd] = useState<number | null>(null);
  const [dados, setDados] = useState<NotasTurma | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [estado, setEstado] = useState<Record<number, 'salvo' | 'erro'>>({});
  const original = useRef<Record<number, number | null>>({});

  useEffect(() => {
    api<TurmaDisciplina[]>('/catalogo/turma-disciplinas')
      .then((r) => {
        setTds(r);
        if (r[0]) setTd(r.reduce((m, t) => (t.notasLancadas > m.notasLancadas ? t : m), r[0]).id);
        else setCarregando(false);
      })
      .catch((e: ApiError) => { setErro(e.message); setCarregando(false); });
  }, []);

  useEffect(() => {
    if (td === null) return;
    setCarregando(true);
    setEstado({});
    api<NotasTurma>(`/notas/turma-disciplina/${td}`)
      .then((r) => {
        setDados(r);
        original.current = Object.fromEntries(r.alunos.map((a) => [a.idAluno, a.valor]));
        setErro(null);
      })
      .catch((e: ApiError) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [td]);

  async function salvar(idAluno: number, texto: string) {
    if (!dados?.avaliacao) return;
    const limpo = texto.trim().replace(',', '.');
    const valor = limpo === '' ? null : Number(limpo);
    if (valor === original.current[idAluno]) return;
    if (valor !== null && (Number.isNaN(valor) || valor < 0 || valor > 10)) {
      setEstado((s) => ({ ...s, [idAluno]: 'erro' }));
      toast('A nota deve estar entre 0 e 10.', 'erro');
      return;
    }
    try {
      await api('/notas', { method: 'PUT', body: { idAvaliacao: dados.avaliacao.id, idAluno, valor } });
      original.current[idAluno] = valor;
      setEstado((s) => ({ ...s, [idAluno]: 'salvo' }));
    } catch (e) {
      setEstado((s) => ({ ...s, [idAluno]: 'erro' }));
      toast((e as ApiError).message, 'erro');
    }
  }

  const seletor = tds.length > 0 && (
    <select value={td ?? ''} onChange={(e) => setTd(Number(e.target.value))} aria-label="Turma e disciplina" style={{ width: 'auto', minHeight: 34, padding: '4px 34px 4px 12px' }}>
      {tds.map((t) => <option key={t.id} value={t.id}>{completo ? `${t.turma} · ${t.disciplina}` : t.turma}{!completo && tds.filter((x) => x.turma === t.turma).length > 1 ? ` · ${t.disciplina}` : ''}</option>)}
    </select>
  );

  return (
    <Card title={titulo} action={<span style={{ display: 'flex', gap: 12, alignItems: 'center' }}>{seletor || undefined}<Link to="/notas" className="card-link">Todas as avaliações</Link></span>}>
      {erro && <ErrorBox erro={erro} />}
      {carregando && <Loading />}
      {!carregando && !erro && !tds.length && <Empty>Nenhuma turma vinculada ao seu perfil.</Empty>}
      {!carregando && dados && !dados.avaliacao && <Empty>Nenhuma avaliação cadastrada para esta turma.</Empty>}
      {!carregando && dados?.avaliacao && (
        <>
          <p className="muted" style={{ margin: '-6px 0 8px' }}>{dados.avaliacao.titulo} • {dados.alunos.length} alunos • salvo automaticamente</p>
          <div className="notas-lista" style={completo ? { maxHeight: 'none' } : undefined}>
            {dados.alunos.map((a) => (
              <div className="linha" key={a.idAluno}>
                <div><strong>{a.nome}</strong><small className="muted">Mat. {a.matricula.slice(-4)}</small></div>
                <input
                  className={`nota-input ${estado[a.idAluno] ?? ''}`}
                  inputMode="decimal"
                  aria-label={`Nota de ${a.nome}`}
                  defaultValue={a.valor === null ? '' : a.valor.toFixed(1)}
                  placeholder="—"
                  onBlur={(e) => salvar(a.idAluno, e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.currentTarget as HTMLInputElement).blur()}
                />
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
