import { FormEvent, useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import { diaMesCurto, nota as fmtNota } from '../format';
import { Icon } from '../icons';
import { Link } from '../router';
import type { DashResponsavel, ProvaCalendario, TurmaDisciplina } from '../types';
import { avisarNotificacoes, Badge, Card, Empty, ErrorBox, Field, Loading, Modal, PageHeader, Stat, useApi, useToast } from '../ui';
import { ChipTipo, doISO, hojeISO, MESES } from './agenda-comum';

type Periodo = 'proximas' | 'passadas' | 'todas';
const PERIODOS: { v: Periodo; r: string }[] = [{ v: 'proximas', r: 'Próximas' }, { v: 'passadas', r: 'Realizadas' }, { v: 'todas', r: 'Todas' }];

function contagem(d: number): { texto: string; tone: 'red' | 'amber' | 'gray' | 'blue' } {
  if (d === 0) return { texto: 'Hoje', tone: 'red' };
  if (d === 1) return { texto: 'Amanhã', tone: 'red' };
  if (d > 1 && d <= 3) return { texto: `Em ${d} dias`, tone: 'amber' };
  if (d > 3) return { texto: `Em ${d} dias`, tone: 'blue' };
  return { texto: d === -1 ? 'Ontem' : `Há ${-d} dias`, tone: 'gray' };
}

function Remarcar({ prova, onFechar, onSalvo }: { prova: ProvaCalendario; onFechar: () => void; onSalvo: () => void }) {
  const toast = useToast();
  const [data, setData] = useState(prova.data);
  const [motivo, setMotivo] = useState('');
  const [local, setLocal] = useState<string | undefined>();
  const [erro, setErro] = useState<ApiError | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    const dia = data ? doISO(data).getDay() : -1;
    const l = !data ? 'Informe a nova data' : data === prova.data ? 'Escolha uma data diferente da atual' : dia === 0 || dia === 6 ? 'Avaliações não podem ser marcadas no fim de semana' : undefined;
    setLocal(l);
    if (l) return;
    setEnviando(true);
    try {
      const r = await api<{ notificados: number }>(`/avaliacoes/${prova.id}/data`, { method: 'PATCH', body: { dataAvaliacao: data, ...(motivo.trim() ? { motivo: motivo.trim() } : {}) } });
      toast(`Avaliação remarcada! ${r.notificados} pessoa(s) avisada(s).`);
      avisarNotificacoes();
      onSalvo();
    } catch (err) {
      setErro(err as ApiError);
    } finally {
      setEnviando(false);
    }
  }
  const msg = local ?? erro?.campo('dataAvaliacao');
  return (
    <Modal titulo={`Remarcar: ${prova.titulo}`} onClose={onFechar}>
      <form className="form" onSubmit={enviar} noValidate>
        <p className="muted" style={{ margin: 0 }}>{prova.disciplina} · {prova.turma}. Alunos e responsáveis da turma serão avisados.</p>
        {erro && !erro.campo('dataAvaliacao') && <div className="alert alert-red" role="alert"><Icon name="alert" size={18} />{erro.message}</div>}
        <Field label="Nova data" error={msg}><input type="date" value={data} onChange={(e) => setData(e.target.value)} data-testid="nova-data" /></Field>
        <Field label="Motivo (opcional)" error={erro?.campo('motivo')} hint={`${motivo.length}/200 caracteres`}>
          <input type="text" value={motivo} maxLength={200} onChange={(e) => setMotivo(e.target.value)} placeholder="Ex.: conflito com a feira de ciências" />
        </Field>
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onFechar}>Cancelar</button>
          <button className="btn btn-primary" disabled={enviando}>{enviando ? 'Salvando…' : 'Remarcar avaliação'}</button>
        </div>
      </form>
    </Modal>
  );
}

/** Calendário de provas (PB16): avaliações marcadas, com contagem regressiva e remarcação por quem leciona. */
export default function Provas() {
  const { user } = useAuth();
  const perfil = user!.perfil;
  const staff = perfil !== 'ALUNO' && perfil !== 'RESPONSAVEL';
  const [periodo, setPeriodo] = useState<Periodo>('proximas');
  const [bimestre, setBimestre] = useState('');
  const [idAluno, setIdAluno] = useState('');
  const [idTd, setIdTd] = useState('');
  const [remarcando, setRemarcando] = useState<ProvaCalendario | null>(null);

  const dash = useApi<DashResponsavel>(perfil === 'RESPONSAVEL' ? '/dashboard' : null);
  const [tds, setTds] = useState<TurmaDisciplina[]>([]);
  useEffect(() => { if (staff) api<TurmaDisciplina[]>('/catalogo/turma-disciplinas').then(setTds).catch(() => undefined); }, [staff]);

  const filtros = `${bimestre ? `&bimestre=${bimestre}` : ''}${idAluno ? `&idAluno=${idAluno}` : ''}${idTd ? `&idTurmaDisciplina=${idTd}` : ''}`;
  const lista = useApi<ProvaCalendario[]>(`/agenda/provas?periodo=${periodo}${filtros}`);
  const proximas = useApi<ProvaCalendario[]>(`/agenda/provas?periodo=proximas${filtros}`);

  const grupos = useMemo(() => {
    const m = new Map<string, ProvaCalendario[]>();
    (lista.data ?? []).forEach((p) => { const k = p.data.slice(0, 7); m.set(k, [...(m.get(k) ?? []), p]); });
    return [...m];
  }, [lista.data]);

  const prox = proximas.data ?? [];
  const hoje = hojeISO();
  const naSemana = prox.filter((p) => p.diasRestantes <= 7).length;
  const primeira = prox[0];
  const recarregar = () => { lista.recarregar(); proximas.recarregar(); };

  return (
    <>
      <PageHeader titulo="Calendário de Provas" subtitulo={staff ? 'Acompanhe as avaliações das turmas e remarque quando necessário.' : 'Veja as próximas avaliações, com quantos dias faltam para cada uma.'} />

      <div className="grid-3">
        <Stat label="Próximas avaliações" value={proximas.data ? prox.length : '—'} badge={prox.length ? 'Agendadas' : 'Nenhuma'} tone={prox.length ? 'blue' : 'gray'} icon="bookmark" />
        <Stat label="Nos próximos 7 dias" value={proximas.data ? naSemana : '—'} badge={naSemana ? 'Atenção' : 'Tranquilo'} tone={naSemana ? 'amber' : 'green'} icon="clock" />
        <Stat label="Próxima avaliação" value={primeira ? (primeira.diasRestantes === 0 ? 'Hoje' : `${primeira.diasRestantes} d`) : '—'} badge={primeira ? primeira.disciplina : 'Sem datas'} tone={primeira && primeira.diasRestantes <= 3 ? 'red' : 'gray'} icon="calendar" />
      </div>

      <Card>
        <div className="toolbar">
          <div className="tabs" role="tablist" aria-label="Período">
            {PERIODOS.map((p) => <button key={p.v} role="tab" aria-selected={periodo === p.v} className={`tab ${periodo === p.v ? 'on' : ''}`} onClick={() => setPeriodo(p.v)} data-testid={`periodo-${p.v}`}>{p.r}</button>)}
          </div>
          <span className="grow" />
          {perfil === 'RESPONSAVEL' && (dash.data?.alunos.length ?? 0) > 1 && (
            <select value={idAluno} onChange={(e) => setIdAluno(e.target.value)} aria-label="Aluno" style={{ width: 'auto' }}>
              <option value="">Todos os filhos</option>
              {dash.data!.alunos.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
            </select>
          )}
          {staff && tds.length > 0 && (
            <select value={idTd} onChange={(e) => setIdTd(e.target.value)} aria-label="Turma e disciplina" style={{ width: 'auto' }}>
              <option value="">Todas as turmas e disciplinas</option>
              {tds.map((t) => <option key={t.id} value={t.id}>{t.turma} · {t.disciplina}</option>)}
            </select>
          )}
          <select value={bimestre} onChange={(e) => setBimestre(e.target.value)} aria-label="Bimestre" style={{ width: 'auto' }}>
            <option value="">Todos os bimestres</option>
            {[1, 2, 3, 4].map((b) => <option key={b} value={b}>{b}º bimestre</option>)}
          </select>
          {staff && <Link to="/avaliacoes" className="card-link">Cadastrar avaliação</Link>}
        </div>

        {lista.erro && <ErrorBox erro={lista.erro} onRetry={lista.recarregar} />}
        {lista.carregando && !lista.data && <Loading />}
        {lista.data && !lista.data.length && <Empty>{periodo === 'proximas' ? 'Nenhuma avaliação marcada para os próximos dias.' : 'Nenhuma avaliação encontrada com estes filtros.'}</Empty>}

        {grupos.map(([mes, provas]) => (
          <section key={mes} className="provas-mes" aria-label={mes}>
            <h3 className="provas-mes-titulo">{MESES[Number(mes.slice(5, 7)) - 1]} de {mes.slice(0, 4)}</h3>
            <div className="list">
              {provas.map((p) => {
                const c = contagem(p.diasRestantes);
                const d = diaMesCurto(p.data);
                return (
                  <div className="row prova" key={`${p.id}-${p.idAluno ?? 0}`} data-testid="prova" data-id={p.id}>
                    <div className="evento">
                      <span className="date-chip big" aria-label={`${d.dia} de ${MESES[Number(p.data.slice(5, 7)) - 1]}`}>{d.dia}<small>{d.mes}</small></span>
                      <div className="row-main">
                        <strong>{p.titulo}</strong>
                        <small>{p.disciplina} · {p.turma} · {p.bimestre}º bimestre · peso {p.peso}{p.professor && staff ? ` · ${p.professor}` : ''}{p.aluno ? ` · ${p.aluno}` : ''}</small>
                      </div>
                    </div>
                    <div className="prova-lado">
                      <ChipTipo categoria={p.tipo} />
                      {p.nota !== null ? <Badge tone="green">Nota {fmtNota(p.nota)}</Badge> : <Badge tone={c.tone}>{c.texto}</Badge>}
                      {p.podeRemarcar && p.data >= hoje && <button className="btn btn-secondary btn-sm" onClick={() => setRemarcando(p)} data-testid="remarcar"><Icon name="calendar" size={14} />Remarcar</button>}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </Card>

      {remarcando && <Remarcar prova={remarcando} onFechar={() => setRemarcando(null)} onSalvo={() => { setRemarcando(null); recarregar(); }} />}
    </>
  );
}
