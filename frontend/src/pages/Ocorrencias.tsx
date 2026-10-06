import { FormEvent, useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { api, ApiError } from '../api';
import { dataBR, quando } from '../format';
import { Icon } from '../icons';
import { navigate } from '../router';
import type { AlunoCatalogo, GravidadeOcorrencia, Ocorrencia, StatusOcorrencia, TipoOcorrencia } from '../types';
import { avisarNotificacoes, Badge, Card, Empty, ErrorBox, Field, Loading, Modal, PageHeader, Tone, useApi, useToast } from '../ui';
import { hojeISO } from './academico';

const TIPOS: { v: TipoOcorrencia; r: string }[] = [
  { v: 'DISCIPLINAR', r: 'Disciplinar' }, { v: 'PEDAGOGICA', r: 'Pedagógica' }, { v: 'SAUDE', r: 'Saúde' }, { v: 'ELOGIO', r: 'Elogio' },
];
const GRAVIDADES: { v: GravidadeOcorrencia; r: string; t: Tone }[] = [
  { v: 'LEVE', r: 'Leve', t: 'gray' }, { v: 'MEDIA', r: 'Média', t: 'amber' }, { v: 'GRAVE', r: 'Grave', t: 'red' },
];
const STATUS: { v: StatusOcorrencia; r: string; t: Tone; plural: string }[] = [
  { v: 'ABERTA', r: 'Aberta', t: 'amber', plural: 'Abertas' }, { v: 'EM_ANALISE', r: 'Em análise', t: 'blue', plural: 'Em análise' }, { v: 'RESOLVIDA', r: 'Resolvida', t: 'green', plural: 'Resolvidas' },
];
const rotuloTipo = (t: string) => TIPOS.find((x) => x.v === t)?.r ?? t;
const GravBadge = ({ g, tipo }: { g: GravidadeOcorrencia; tipo: TipoOcorrencia }) => tipo === 'ELOGIO' ? <Badge tone="green">Elogio</Badge> : <Badge tone={GRAVIDADES.find((x) => x.v === g)!.t}>{GRAVIDADES.find((x) => x.v === g)!.r}</Badge>;
const StatusBadge = ({ s }: { s: StatusOcorrencia }) => <Badge tone={STATUS.find((x) => x.v === s)!.t}>{STATUS.find((x) => x.v === s)!.r}</Badge>;

function OcorrenciaForm({ inicial, onSalvo, onCancelar }: { inicial?: Ocorrencia; onSalvo: () => void; onCancelar: () => void }) {
  const toast = useToast();
  const [busca, setBusca] = useState('');
  const [alunos, setAlunos] = useState<AlunoCatalogo[]>([]);
  const [idAluno, setIdAluno] = useState<number | ''>(inicial?.idAluno ?? '');
  const [titulo, setTitulo] = useState(inicial?.titulo ?? '');
  const [descricao, setDescricao] = useState(inicial?.descricao ?? '');
  const [tipo, setTipo] = useState<TipoOcorrencia>(inicial?.tipo ?? 'DISCIPLINAR');
  const [gravidade, setGravidade] = useState<GravidadeOcorrencia>(inicial?.gravidade ?? 'LEVE');
  const [data, setData] = useState('');
  const [erro, setErro] = useState<ApiError | null>(null);
  const [local, setLocal] = useState<Record<string, string>>({});
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (inicial) return;
    const t = setTimeout(() => api<AlunoCatalogo[]>(`/catalogo/alunos?busca=${encodeURIComponent(busca)}`).then(setAlunos).catch(() => undefined), 250);
    return () => clearTimeout(t);
  }, [busca, inicial]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    const l: Record<string, string> = {};
    if (!inicial && idAluno === '') l.idAluno = 'Selecione o aluno';
    if (titulo.trim().length < 3) l.titulo = 'Informe um título com ao menos 3 caracteres';
    if (descricao.trim().length < 10) l.descricao = 'Descreva o ocorrido com ao menos 10 caracteres';
    if (tipo === 'ELOGIO' && gravidade !== 'LEVE') l.gravidade = 'Elogios não possuem gravidade';
    if (data && data > hojeISO()) l.dataOcorrencia = 'A data da ocorrência não pode ser futura';
    setLocal(l);
    setErro(null);
    if (Object.keys(l).length) return;
    setEnviando(true);
    try {
      if (inicial) await api(`/ocorrencias/${inicial.id}`, { method: 'PUT', body: { titulo, descricao, tipo, gravidade } });
      else await api('/ocorrencias', { method: 'POST', body: { idAluno, titulo, descricao, tipo, gravidade, ...(data ? { dataOcorrencia: data } : {}) } });
      toast(inicial ? 'Ocorrência atualizada.' : 'Ocorrência registrada! A coordenação foi notificada.');
      avisarNotificacoes();
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
      {inicial ? (
        <p className="muted" style={{ margin: 0 }}>Aluno: <strong>{inicial.aluno}</strong>{inicial.turma ? ` • ${inicial.turma}` : ''}</p>
      ) : (
        <Field label="Aluno" error={msg('idAluno')}>
          <input type="search" placeholder="Buscar por nome ou matrícula…" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Buscar aluno" style={{ marginBottom: 6 }} />
          <select value={idAluno} onChange={(e) => setIdAluno(e.target.value === '' ? '' : Number(e.target.value))} aria-label="Aluno">
            <option value="">Selecione o aluno…</option>
            {alunos.map((a) => <option key={a.id} value={a.id}>{a.nome} — {a.turma ?? 'sem turma'}</option>)}
          </select>
        </Field>
      )}
      <Field label="Título" error={msg('titulo')}>
        <input type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} maxLength={120} placeholder="Ex.: Atraso recorrente" />
      </Field>
      <Field label="Descrição" error={msg('descricao')} hint={`${descricao.length}/2000 caracteres`}>
        <textarea rows={4} value={descricao} onChange={(e) => setDescricao(e.target.value)} maxLength={2000} placeholder="Descreva o que aconteceu, quando e em qual contexto…" />
      </Field>
      <div className="form-row">
        <Field label="Tipo" error={msg('tipo')}>
          <select value={tipo} onChange={(e) => { const t = e.target.value as TipoOcorrencia; setTipo(t); if (t === 'ELOGIO') setGravidade('LEVE'); }}>{TIPOS.map((t) => <option key={t.v} value={t.v}>{t.r}</option>)}</select>
        </Field>
        <Field label="Gravidade" error={msg('gravidade')} hint="Média e grave avisam também os responsáveis">
          <select value={gravidade} disabled={tipo === 'ELOGIO'} onChange={(e) => setGravidade(e.target.value as GravidadeOcorrencia)}>{GRAVIDADES.map((g) => <option key={g.v} value={g.v}>{g.r}</option>)}</select>
        </Field>
      </div>
      {!inicial && (
        <Field label="Data do ocorrido (opcional)" error={msg('dataOcorrencia')} hint="Em branco = hoje">
          <input type="date" value={data} max={hojeISO()} onChange={(e) => setData(e.target.value)} style={{ width: 'auto' }} />
        </Field>
      )}
      <div className="modal-actions">
        <button type="button" className="btn btn-secondary" onClick={onCancelar}>Cancelar</button>
        <button className="btn btn-primary" disabled={enviando}>{enviando ? 'Salvando…' : inicial ? 'Salvar alterações' : 'Registrar ocorrência'}</button>
      </div>
    </form>
  );
}

function Detalhe({ id, onFechar, onMudou, onEditar }: { id: number; onFechar: () => void; onMudou: () => void; onEditar: (o: Ocorrencia) => void }) {
  const { user } = useAuth();
  const toast = useToast();
  const { data: o, erro, recarregar } = useApi<Ocorrencia>(`/ocorrencias/${id}`);
  const [parecer, setParecer] = useState('');
  const [resolvendo, setResolvendo] = useState(false);
  const [erroAcao, setErroAcao] = useState<ApiError | null>(null);
  const [excluindo, setExcluindo] = useState(false);

  async function mudar(status: StatusOcorrencia) {
    setErroAcao(null);
    if (status === 'RESOLVIDA' && parecer.trim().length < 10) {
      setErroAcao(new ApiError(400, 'Dados inválidos', [{ campo: 'parecer', mensagem: 'Descreva o parecer da coordenação (mínimo de 10 caracteres)' }]));
      return;
    }
    try {
      await api(`/ocorrencias/${id}/status`, { method: 'PUT', body: { status, ...(status === 'RESOLVIDA' ? { parecer } : {}) } });
      toast(status === 'RESOLVIDA' ? 'Ocorrência resolvida. Professor e responsáveis foram avisados.' : 'Ocorrência colocada em análise.');
      setResolvendo(false);
      setParecer('');
      avisarNotificacoes();
      recarregar();
      onMudou();
    } catch (e) {
      setErroAcao(e as ApiError);
    }
  }

  async function excluir() {
    try {
      await api(`/ocorrencias/${id}`, { method: 'DELETE' });
      toast('Ocorrência excluída.');
      onMudou();
      onFechar();
    } catch (e) {
      setErroAcao(e as ApiError);
      setExcluindo(false);
    }
  }

  const podeExcluir = o && (user!.perfil === 'ADMIN' || (user!.perfil === 'PROFESSOR' && o.podeEditar));
  return (
    <Modal titulo="Detalhes da ocorrência" onClose={onFechar} largo>
      {erro && <ErrorBox erro={erro} />}
      {!o && !erro && <Loading />}
      {o && (
        <div className="oc-det">
          <div className="oc-top">
            <div><h3>{o.titulo}</h3><small className="muted">{o.aluno}{o.turma ? ` • ${o.turma}` : ''} • Mat. {o.matricula}</small></div>
            <span className="com-tags"><GravBadge g={o.gravidade} tipo={o.tipo} /><StatusBadge s={o.status} /></span>
          </div>
          <p className="com-msg">{o.descricao}</p>
          <p className="muted" style={{ margin: 0 }}>{rotuloTipo(o.tipo)} • registrada em {dataBR(o.data)}{o.professor ? ` por ${o.professor}` : ' pela coordenação'}</p>
          {o.parecer && <div className="alert alert-blue"><Icon name="info" size={18} /><span><strong>Parecer da coordenação:</strong> {o.parecer}</span></div>}

          <h4>Histórico</h4>
          <ol className="timeline">
            {o.historico?.map((h) => (
              <li key={h.id}>
                <strong>{STATUS.find((s) => s.v === h.statusNovo)!.r}</strong> <small className="muted">• {quando(h.data)} • {h.usuario}</small>
                {h.comentario && <p>{h.comentario}</p>}
              </li>
            ))}
          </ol>

          {erroAcao && !erroAcao.detalhes && <div className="alert alert-red" role="alert"><Icon name="alert" size={18} />{erroAcao.message}</div>}
          {o.podeAlterarStatus && (
            <div className="oc-acoes">
              {resolvendo ? (
                <>
                  <Field label="Parecer da coordenação" error={erroAcao?.campo('parecer')} hint="Obrigatório para resolver (mínimo 10 caracteres)">
                    <textarea rows={3} value={parecer} onChange={(e) => setParecer(e.target.value)} maxLength={1000} placeholder="Descreva as providências tomadas…" />
                  </Field>
                  <div className="modal-actions"><button className="btn btn-secondary" onClick={() => { setResolvendo(false); setErroAcao(null); }}>Cancelar</button><button className="btn btn-primary" onClick={() => mudar('RESOLVIDA')}><Icon name="check" size={16} />Confirmar resolução</button></div>
                </>
              ) : (
                <div className="modal-actions">
                  {o.status === 'ABERTA' && <button className="btn btn-secondary" onClick={() => mudar('EM_ANALISE')}>Colocar em análise</button>}
                  <button className="btn btn-primary" onClick={() => setResolvendo(true)}><Icon name="checkCircle" size={16} />Resolver…</button>
                </div>
              )}
            </div>
          )}
          {!resolvendo && (o.podeEditar || podeExcluir) && (
            <div className="modal-actions" style={{ marginTop: 8 }}>
              {podeExcluir && !excluindo && <button className="btn btn-secondary" onClick={() => setExcluindo(true)}><Icon name="trash" size={14} />Excluir</button>}
              {excluindo && <><span className="muted">Excluir definitivamente?</span><button className="btn btn-secondary" onClick={() => setExcluindo(false)}>Não</button><button className="btn btn-danger" onClick={excluir}>Sim, excluir</button></>}
              {o.podeEditar && !excluindo && <button className="btn btn-secondary" onClick={() => onEditar(o)}><Icon name="edit" size={14} />Editar</button>}
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

/** Ocorrências escolares: registro pelo professor, análise e resolução pela coordenação, consulta por alunos e responsáveis. */
export default function Ocorrencias({ id }: { id?: number }) {
  const { user } = useAuth();
  const podeRegistrar = ['PROFESSOR', 'COORDENADOR', 'ADMIN'].includes(user!.perfil);
  const [status, setStatus] = useState<StatusOcorrencia | ''>('');
  const [gravidade, setGravidade] = useState('');
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  useEffect(() => { const t = setTimeout(() => setBuscaAplicada(busca), 250); return () => clearTimeout(t); }, [busca]);
  const qs = [status && `status=${status}`, gravidade && `gravidade=${gravidade}`, buscaAplicada && `busca=${encodeURIComponent(buscaAplicada)}`].filter(Boolean).join('&');
  const { data: lista, erro, carregando, recarregar } = useApi<Ocorrencia[]>(`/ocorrencias${qs ? `?${qs}` : ''}`);
  const resumo = useApi<Record<StatusOcorrencia, number>>('/ocorrencias/resumo');

  const [detalhe, setDetalhe] = useState<number | null>(id ?? null);
  useEffect(() => { setDetalhe(id ?? null); }, [id]);
  const [form, setForm] = useState<Ocorrencia | 'nova' | null>(null);

  const atualizar = () => { recarregar(); resumo.recarregar(); };
  const fecharDetalhe = () => { setDetalhe(null); if (id) navigate('/ocorrencias'); };

  return (
    <>
      <PageHeader titulo="Ocorrências" subtitulo={podeRegistrar ? 'Registre ocorrências dos alunos; a coordenação analisa e resolve com parecer.' : 'Acompanhe as ocorrências registradas pela escola.'} />
      <div className="grid-3" style={{ marginBottom: 16 }}>
        {STATUS.map((s) => (
          <button key={s.v} className={`card stat stat-btn ${status === s.v ? 'on' : ''}`} onClick={() => setStatus(status === s.v ? '' : s.v)} aria-pressed={status === s.v}>
            <div className="stat-top"><span className="stat-label">{s.plural}</span></div>
            <div className="stat-value"><strong>{resumo.data?.[s.v] ?? '—'}</strong><Badge tone={s.t}>{s.r}</Badge></div>
          </button>
        ))}
      </div>
      <div className="toolbar">
        <select value={gravidade} onChange={(e) => setGravidade(e.target.value)} aria-label="Gravidade" style={{ width: 'auto' }}>
          <option value="">Todas as gravidades</option>{GRAVIDADES.map((g) => <option key={g.v} value={g.v}>{g.r}</option>)}
        </select>
        <input type="search" placeholder="Buscar por aluno ou título…" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Buscar ocorrência" style={{ width: 'auto', minWidth: 240 }} />
        <span className="grow" />
        {podeRegistrar && <button className="btn btn-primary" onClick={() => setForm('nova')}><Icon name="plus" size={18} />Nova ocorrência</button>}
      </div>

      {carregando && !lista && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {lista && (
        <Card>
          <div className="table-scroll">
            <table className="table">
              <thead><tr><th>Aluno</th><th>Ocorrência</th><th>Gravidade</th><th>Situação</th><th>Data</th><th>Ações</th></tr></thead>
              <tbody>
                {lista.map((o) => (
                  <tr key={o.id}>
                    <td style={{ textAlign: 'left' }}><strong>{o.aluno}</strong><br /><small className="muted">{o.turma}</small></td>
                    <td style={{ textAlign: 'left' }}>{o.titulo}<br /><small className="muted">{rotuloTipo(o.tipo)}{o.professor ? ` • ${o.professor}` : ''}</small></td>
                    <td><GravBadge g={o.gravidade} tipo={o.tipo} /></td>
                    <td><StatusBadge s={o.status} /></td>
                    <td style={{ textAlign: 'left' }}>{dataBR(o.data)}</td>
                    <td className="actions"><button className="btn btn-secondary btn-sm" onClick={() => setDetalhe(o.id)} aria-label={`Detalhes: ${o.titulo}`}>Detalhes</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!lista.length && <Empty>{qs ? 'Nenhuma ocorrência encontrada com esses filtros.' : 'Nenhuma ocorrência registrada.'}</Empty>}
        </Card>
      )}

      {detalhe !== null && <Detalhe id={detalhe} onFechar={fecharDetalhe} onMudou={atualizar} onEditar={(o) => { setForm(o); }} />}
      {form && (
        <Modal titulo={form === 'nova' ? 'Nova ocorrência' : 'Editar ocorrência'} onClose={() => setForm(null)} largo>
          <OcorrenciaForm inicial={form === 'nova' ? undefined : form} onCancelar={() => setForm(null)} onSalvo={() => { setForm(null); atualizar(); if (detalhe !== null) setDetalhe(null); }} />
        </Modal>
      )}
    </>
  );
}
