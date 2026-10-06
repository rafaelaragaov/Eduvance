import { FormEvent, useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import { dataBR } from '../format';
import { Icon } from '../icons';
import { Link } from '../router';
import type { Avaliacao, TurmaDisciplina } from '../types';
import { Badge, Card, Empty, ErrorBox, Field, Loading, Modal, PageHeader, useApi, useToast } from '../ui';
import { rotuloTipo, TdSelect, TIPOS, useTurmaDisciplinas } from './academico';

const anoAtual = new Date().getFullYear();

function AvaliacaoForm({ tds, inicial, onSalvo, onCancelar }: { tds: TurmaDisciplina[]; inicial?: Avaliacao; onSalvo: () => void; onCancelar: () => void }) {
  const toast = useToast();
  const [titulo, setTitulo] = useState(inicial?.titulo ?? '');
  const [tipo, setTipo] = useState(inicial?.tipo ?? 'PROVA');
  const [bimestre, setBimestre] = useState(inicial?.bimestre ?? 3);
  const [data, setData] = useState(inicial?.dataAvaliacao ?? '');
  const [peso, setPeso] = useState(String(inicial?.peso ?? 1).replace('.', ','));
  const [td, setTd] = useState<number | ''>(inicial?.idTurmaDisciplina ?? tds[0]?.id ?? '');
  const [erro, setErro] = useState<ApiError | null>(null);
  const [local, setLocal] = useState<Record<string, string>>({});
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    // validação no navegador (o servidor valida de novo)
    const l: Record<string, string> = {};
    if (titulo.trim().length < 3) l.titulo = 'Informe um título com ao menos 3 caracteres';
    if (!data) l.dataAvaliacao = 'Informe a data da avaliação';
    else if (Number(data.slice(0, 4)) !== anoAtual && !inicial) l.dataAvaliacao = `A data deve estar em ${anoAtual} (ano letivo)`;
    const p = Number(peso.replace(',', '.'));
    if (Number.isNaN(p) || p < 0.5 || p > 5) l.peso = 'O peso deve estar entre 0,5 e 5';
    if (td === '') l.idTurmaDisciplina = 'Selecione a turma e a disciplina';
    setLocal(l);
    setErro(null);
    if (Object.keys(l).length) return;

    setEnviando(true);
    try {
      const corpo = { titulo, tipo, bimestre, dataAvaliacao: data, peso: p, idTurmaDisciplina: td };
      if (inicial) await api(`/avaliacoes/${inicial.id}`, { method: 'PUT', body: corpo });
      else await api('/avaliacoes', { method: 'POST', body: corpo });
      toast(inicial ? 'Avaliação atualizada.' : 'Avaliação cadastrada!');
      onSalvo();
    } catch (err) {
      setErro(err as ApiError);
    } finally {
      setEnviando(false);
    }
  }

  const msg = (c: string) => local[c] ?? erro?.campo(c);
  return (
    <form className="form" onSubmit={enviar} noValidate>
      {erro && !erro.detalhes && <div className="alert alert-red" role="alert"><Icon name="alert" size={18} />{erro.message}</div>}
      <Field label="Título da avaliação" error={msg('titulo')}>
        <input type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Ex.: Prova Mensal de Funções" maxLength={120} />
      </Field>
      <div className="form-row">
        <Field label="Tipo" error={msg('tipo')}>
          <select value={tipo} onChange={(e) => setTipo(e.target.value as typeof tipo)}>{TIPOS.map((t) => <option key={t.v} value={t.v}>{t.r}</option>)}</select>
        </Field>
        <Field label="Bimestre" error={msg('bimestre')}>
          <select value={bimestre} onChange={(e) => setBimestre(Number(e.target.value))}>{[1, 2, 3, 4].map((b) => <option key={b} value={b}>{b}º bimestre</option>)}</select>
        </Field>
      </div>
      <div className="form-row">
        <Field label="Data" error={msg('dataAvaliacao')}>
          <input type="date" value={data} onChange={(e) => setData(e.target.value)} />
        </Field>
        <Field label="Peso na média" error={msg('peso')} hint="De 0,5 a 5 (padrão 1)">
          <input type="text" inputMode="decimal" value={peso} onChange={(e) => setPeso(e.target.value)} />
        </Field>
      </div>
      <Field label="Turma / disciplina" error={msg('idTurmaDisciplina')}>
        <select value={td} onChange={(e) => setTd(Number(e.target.value))}>{tds.map((t) => <option key={t.id} value={t.id}>{t.turma} — {t.disciplina}</option>)}</select>
      </Field>
      <div className="modal-actions">
        <button type="button" className="btn btn-secondary" onClick={onCancelar}>Cancelar</button>
        <button className="btn btn-primary" disabled={enviando}>{enviando ? 'Salvando…' : inicial ? 'Salvar alterações' : 'Cadastrar avaliação'}</button>
      </div>
    </form>
  );
}

/** CRUD de avaliações (provas, trabalhos, testes e projetos). */
export default function Avaliacoes() {
  const toast = useToast();
  const { tds } = useTurmaDisciplinas();
  const [td, setTd] = useState<number | ''>('');
  const [bim, setBim] = useState<number | ''>('');
  const qs = [td !== '' ? `idTurmaDisciplina=${td}` : '', bim !== '' ? `bimestre=${bim}` : ''].filter(Boolean).join('&');
  const { data: lista, erro, carregando, recarregar } = useApi<Avaliacao[]>(`/avaliacoes${qs ? `?${qs}` : ''}`);

  const [editando, setEditando] = useState<Avaliacao | 'nova' | null>(null);
  const [excluindo, setExcluindo] = useState<Avaliacao | null>(null);
  const [erroExcluir, setErroExcluir] = useState<string | null>(null);
  const [apagando, setApagando] = useState(false);
  useEffect(() => { setErroExcluir(null); }, [excluindo]);

  async function excluir() {
    if (!excluindo) return;
    setApagando(true);
    try {
      await api(`/avaliacoes/${excluindo.id}`, { method: 'DELETE' });
      toast('Avaliação excluída.');
      setExcluindo(null);
      recarregar();
    } catch (e) {
      setErroExcluir((e as ApiError).message);
    } finally {
      setApagando(false);
    }
  }

  return (
    <>
      <PageHeader titulo="Avaliações" subtitulo="Cadastre provas, trabalhos, testes e projetos; depois lance as notas de cada turma." />
      <div className="toolbar">
        {tds && <TdSelect tds={tds} valor={td} onChange={setTd} todas />}
        <select value={bim} onChange={(e) => setBim(e.target.value === '' ? '' : Number(e.target.value))} aria-label="Bimestre" style={{ width: 'auto' }}>
          <option value="">Todos os bimestres</option>{[1, 2, 3, 4].map((b) => <option key={b} value={b}>{b}º bimestre</option>)}
        </select>
        <span className="grow" />
        <button className="btn btn-primary" onClick={() => setEditando('nova')} disabled={!tds?.length}><Icon name="plus" size={18} />Nova avaliação</button>
      </div>

      {carregando && !lista && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {lista && (
        <Card>
          <div className="table-scroll">
            <table className="table">
              <thead><tr><th>Avaliação</th><th>Turma / disciplina</th><th>Data</th><th className="num">Bim.</th><th className="num">Peso</th><th>Notas</th><th>Ações</th></tr></thead>
              <tbody>
                {lista.map((a) => (
                  <tr key={a.id}>
                    <td style={{ textAlign: 'left' }}><strong>{a.titulo}</strong><br /><Badge tone="blue">{rotuloTipo(a.tipo)}</Badge></td>
                    <td style={{ textAlign: 'left' }}>{a.turma}<br /><small className="muted">{a.disciplina}</small></td>
                    <td style={{ textAlign: 'left' }}>{dataBR(a.dataAvaliacao)}</td>
                    <td className="num">{a.bimestre}º</td>
                    <td className="num">{String(a.peso).replace('.', ',')}</td>
                    <td style={{ textAlign: 'left' }}>
                      {a.notasLancadas} / {a.totalAlunos}
                      {a.mediaTurma !== null && <><br /><small className="muted">média {a.mediaTurma.toFixed(1)}</small></>}
                    </td>
                    <td className="actions">
                      <Link to={`/notas/${a.id}`} className="btn btn-primary btn-sm"><Icon name="edit" size={14} />Lançar notas</Link>{' '}
                      <button className="btn btn-secondary btn-sm" onClick={() => setEditando(a)}>Editar</button>{' '}
                      <button className="btn btn-secondary btn-sm" onClick={() => setExcluindo(a)} aria-label={`Excluir ${a.titulo}`}><Icon name="trash" size={14} />Excluir</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!lista.length && <Empty>Nenhuma avaliação encontrada. Use “Nova avaliação” para cadastrar a primeira.</Empty>}
        </Card>
      )}

      {editando && tds && (
        <Modal titulo={editando === 'nova' ? 'Nova avaliação' : 'Editar avaliação'} onClose={() => setEditando(null)} largo>
          <AvaliacaoForm tds={tds} inicial={editando === 'nova' ? undefined : editando} onCancelar={() => setEditando(null)} onSalvo={() => { setEditando(null); recarregar(); }} />
        </Modal>
      )}
      {excluindo && (
        <Modal titulo="Excluir avaliação?" onClose={() => setExcluindo(null)}>
          <p>Você está prestes a excluir <strong>{excluindo.titulo}</strong> ({excluindo.turma} — {excluindo.disciplina}). Esta ação não pode ser desfeita.</p>
          {erroExcluir && <div className="alert alert-red" role="alert"><Icon name="alert" size={18} />{erroExcluir}</div>}
          <div className="modal-actions">
            <button className="btn btn-secondary" onClick={() => setExcluindo(null)}>{erroExcluir ? 'Fechar' : 'Cancelar'}</button>
            {!erroExcluir && <button className="btn btn-danger" onClick={excluir} disabled={apagando}>{apagando ? 'Excluindo…' : 'Excluir'}</button>}
          </div>
        </Modal>
      )}
    </>
  );
}
