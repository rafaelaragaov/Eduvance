import { useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../api';
import { dataBR } from '../format';
import { Icon } from '../icons';
import { Link, navigate } from '../router';
import type { Avaliacao, NotasAvaliacao } from '../types';
import { Badge, Card, Empty, ErrorBox, Loading, PageHeader, useApi, useToast } from '../ui';
import { lerNota, rotuloTipo, TdSelect, useTurmaDisciplinas } from './academico';

/** Passo 1: escolher a turma e a avaliação para lançar as notas. */
export function EscolherAvaliacao() {
  const { tds } = useTurmaDisciplinas();
  const [td, setTd] = useState<number | ''>('');
  const { data: lista, erro, carregando, recarregar } = useApi<Avaliacao[]>(`/avaliacoes${td !== '' ? `?idTurmaDisciplina=${td}` : ''}`);

  return (
    <>
      <PageHeader titulo="Lançar Notas" subtitulo="Escolha a avaliação e informe a nota de cada aluno." />
      <div className="toolbar">
        {tds && <TdSelect tds={tds} valor={td} onChange={setTd} todas />}
        <span className="grow" />
        <Link to="/avaliacoes" className="btn btn-secondary"><Icon name="plus" size={18} />Cadastrar avaliação</Link>
      </div>
      {carregando && !lista && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {lista && (
        <Card title="Avaliações">
          <div className="list">
            {lista.map((a) => (
              <div className="row" key={a.id}>
                <div className="row-main">
                  <strong>{a.titulo}</strong>
                  <small>{a.turma} · {a.disciplina} · {a.bimestre}º bimestre · {dataBR(a.dataAvaliacao)} · peso {String(a.peso).replace('.', ',')}</small>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Badge tone={a.notasLancadas === a.totalAlunos ? 'green' : a.notasLancadas ? 'amber' : 'gray'}>{a.notasLancadas}/{a.totalAlunos} notas</Badge>
                  <Link to={`/notas/${a.id}`} className="btn btn-primary btn-sm">Lançar notas</Link>
                </div>
              </div>
            ))}
          </div>
          {!lista.length && <Empty>Nenhuma avaliação cadastrada para esta seleção. <Link to="/avaliacoes" className="card-link">Cadastrar avaliação</Link></Empty>}
        </Card>
      )}
    </>
  );
}

/** Passo 2: grade de notas de uma avaliação (salva todas de uma vez, com validação por aluno). */
export default function Notas({ id }: { id: number }) {
  const toast = useToast();
  const [dados, setDados] = useState<NotasAvaliacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [texto, setTexto] = useState<Record<number, string>>({});
  const [original, setOriginal] = useState<Record<number, string>>({});
  const [erros, setErros] = useState<Record<number, string>>({});
  const [salvando, setSalvando] = useState(false);
  const [avisoGeral, setAvisoGeral] = useState<string | null>(null);

  function aplicar(d: NotasAvaliacao) {
    setDados(d);
    const t = Object.fromEntries(d.alunos.map((a) => [a.idAluno, a.valor === null ? '' : a.valor.toFixed(1).replace('.', ',')]));
    setTexto(t);
    setOriginal(t);
    setErros({});
  }

  useEffect(() => {
    setDados(null);
    setErro(null);
    api<NotasAvaliacao>(`/notas/avaliacao/${id}`).then(aplicar).catch((e: ApiError) => setErro(e.message));
  }, [id]);

  const alteradas = useMemo(() => Object.keys(texto).filter((k) => texto[Number(k)] !== original[Number(k)]).map(Number), [texto, original]);
  const mediaPrevia = useMemo(() => {
    const v = Object.values(texto).map((t) => lerNota(t)).filter((r) => !r.erro && r.valor !== null).map((r) => r.valor as number);
    return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
  }, [texto]);

  function digitar(idAluno: number, valor: string) {
    setTexto((t) => ({ ...t, [idAluno]: valor }));
    const r = lerNota(valor);
    setErros((e) => { const n = { ...e }; if (r.erro) n[idAluno] = r.erro; else delete n[idAluno]; return n; });
    setAvisoGeral(null);
  }

  const irParaOErro = () => setTimeout(() => document.querySelector('.nota-input.erro')?.scrollIntoView({ block: 'center' }), 50);

  async function salvar() {
    if (!dados) return;
    if (Object.keys(erros).length) {
      setAvisoGeral('Corrija as notas destacadas em vermelho antes de salvar.');
      irParaOErro();
      return;
    }
    if (!alteradas.length) {
      toast('Nenhuma alteração para salvar.', 'info');
      return;
    }
    setSalvando(true);
    setAvisoGeral(null);
    try {
      const notas = alteradas.map((idAluno) => ({ idAluno, valor: lerNota(texto[idAluno]!).valor }));
      const r = await api<NotasAvaliacao & { salvas: number; removidas: number }>(`/notas/avaliacao/${id}`, { method: 'PUT', body: { notas } });
      aplicar(r);
      toast(`Notas salvas: ${r.salvas} lançada(s)${r.removidas ? `, ${r.removidas} removida(s)` : ''}.`);
    } catch (e) {
      const err = e as ApiError;
      const porAluno: Record<number, string> = {};
      err.detalhes?.forEach((d) => { const m = /^nota-(\d+)$/.exec(d.campo); if (m) porAluno[Number(m[1])] = d.mensagem.replace(/^.*?: /, ''); });
      setErros(porAluno);
      setAvisoGeral(err.message);
      toast(err.message, 'erro');
      irParaOErro();
    } finally {
      setSalvando(false);
    }
  }

  if (erro) return <><PageHeader titulo="Lançar Notas" /><ErrorBox erro={erro} /><p><Link to="/notas" className="card-link">← Voltar às avaliações</Link></p></>;
  if (!dados) return <><PageHeader titulo="Lançar Notas" /><Loading /></>;
  const av = dados.avaliacao;

  return (
    <>
      <PageHeader titulo={av.titulo} subtitulo={`${av.turma} · ${av.disciplina} · ${av.bimestre}º bimestre · ${rotuloTipo(av.tipo)} · peso ${String(av.peso).replace('.', ',')} · ${dataBR(av.data)}`} />
      <p style={{ margin: '-8px 0 14px' }}><Link to="/notas" className="card-link">← Voltar às avaliações</Link></p>
      <Card
        title={`Notas da turma (${dados.alunos.length} alunos)`}
        action={<span className="muted">Média prévia: <strong>{mediaPrevia === null ? '—' : mediaPrevia.toFixed(1)}</strong></span>}
      >
        {avisoGeral && <div className="alert alert-red" role="alert" style={{ marginBottom: 12 }}><Icon name="alert" size={18} />{avisoGeral}</div>}
        <div className="notas-lista" style={{ maxHeight: 'none' }}>
          {dados.alunos.map((a) => (
            <div className="linha" key={a.idAluno}>
              <div>
                <strong>{a.nome}</strong>
                <small className="muted">Mat. {a.matricula.slice(-4)} · <Link to={`/boletim/${a.idAluno}`} className="card-link">Ver boletim</Link></small>
              </div>
              <div style={{ textAlign: 'right' }}>
                <input
                  className={`nota-input ${erros[a.idAluno] ? 'erro' : texto[a.idAluno] !== original[a.idAluno] ? 'sujo' : ''}`}
                  inputMode="decimal"
                  aria-label={`Nota de ${a.nome}`}
                  aria-invalid={!!erros[a.idAluno]}
                  value={texto[a.idAluno] ?? ''}
                  placeholder="—"
                  onChange={(e) => digitar(a.idAluno, e.target.value)}
                />
                {erros[a.idAluno] && <small className="field-error" style={{ display: 'block' }}>{erros[a.idAluno]}</small>}
              </div>
            </div>
          ))}
        </div>
        <div className="modal-actions" style={{ marginTop: 16, alignItems: 'center' }}>
          {alteradas.length > 0 && <Badge tone="amber">{alteradas.length} alteração(ões) não salva(s)</Badge>}
          <button className="btn btn-secondary" onClick={() => navigate('/notas')}>Concluir</button>
          <button className="btn btn-primary" onClick={salvar} disabled={salvando}>{salvando ? 'Salvando…' : 'Salvar notas'}</button>
        </div>
      </Card>
    </>
  );
}
