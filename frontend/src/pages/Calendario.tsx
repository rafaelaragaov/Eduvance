import { FormEvent, useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import { Icon } from '../icons';
import type { Evento, ItemAgenda, PublicoComunicado, TipoEvento, TurmaDisciplina } from '../types';
import { avisarNotificacoes, Badge, Card, Empty, ErrorBox, Field, Loading, Modal, PageHeader, useApi, useToast } from '../ui';
import { ChipTipo, cobreDia, DetalheItem, DIAS_CURTOS, doISO, hojeISO, infoDe, iso, Legenda, MESES, quandoItem, semAula, somarDias } from './agenda-comum';

const TIPOS: { v: TipoEvento; r: string }[] = [
  { v: 'EVENTO', r: 'Evento' }, { v: 'REUNIAO', r: 'Reunião' }, { v: 'CONSELHO', r: 'Conselho de classe' },
  { v: 'FERIADO', r: 'Feriado (sem aulas)' }, { v: 'RECESSO', r: 'Recesso (sem aulas)' },
];
const PUBLICOS: { v: PublicoComunicado; r: string }[] = [
  { v: 'TODOS', r: 'Toda a comunidade escolar' }, { v: 'ALUNOS', r: 'Somente alunos' }, { v: 'RESPONSAVEIS', r: 'Somente responsáveis' },
  { v: 'PROFESSORES', r: 'Somente professores' }, { v: 'TURMA', r: 'Uma turma específica' },
];

function EventoForm({ inicial, dataInicial, turmas, onSalvo, onCancelar }: {
  inicial?: Evento; dataInicial: string; turmas: { id: number; nome: string }[]; onSalvo: () => void; onCancelar: () => void;
}) {
  const toast = useToast();
  const [titulo, setTitulo] = useState(inicial?.titulo ?? '');
  const [descricao, setDescricao] = useState(inicial?.descricao ?? '');
  const [tipo, setTipo] = useState<TipoEvento>(inicial?.tipo ?? 'EVENTO');
  const [publico, setPublico] = useState<PublicoComunicado>(inicial?.publico ?? 'TODOS');
  const [idTurma, setIdTurma] = useState<number | ''>(inicial?.idTurma ?? turmas[0]?.id ?? '');
  const [data, setData] = useState(inicial?.data ?? dataInicial);
  const [dataFim, setDataFim] = useState(inicial?.dataFim ?? '');
  const [hora, setHora] = useState(inicial?.hora ?? '');
  const [horaFim, setHoraFim] = useState(inicial?.horaFim ?? '');
  const [local, setLocal] = useState<Record<string, string>>({});
  const [erro, setErro] = useState<ApiError | null>(null);
  const [enviando, setEnviando] = useState(false);

  const semAulaTipo = tipo === 'FERIADO' || tipo === 'RECESSO';
  const publicoEfetivo: PublicoComunicado = semAulaTipo ? 'TODOS' : publico;
  const msg = (c: string) => local[c] ?? erro?.campo(c);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    const l: Record<string, string> = {};
    if (titulo.trim().length < 3) l.titulo = 'Informe um título com pelo menos 3 caracteres';
    if (!data) l.data = 'Informe a data';
    if (dataFim && data && dataFim < data) l.dataFim = 'A data final deve ser igual ou posterior à inicial';
    if (publicoEfetivo === 'TURMA' && idTurma === '') l.idTurma = 'Escolha a turma';
    if (horaFim && !hora) l.hora = 'Informe a hora inicial';
    if (hora && horaFim && (!dataFim || dataFim === data) && horaFim <= hora) l.horaFim = 'A hora final deve ser posterior à inicial';
    setLocal(l);
    if (Object.keys(l).length) return;
    setEnviando(true);
    const corpo = {
      titulo: titulo.trim(), tipo, publico: publicoEfetivo, data,
      ...(descricao.trim() ? { descricao: descricao.trim() } : {}),
      ...(publicoEfetivo === 'TURMA' ? { idTurma } : {}),
      ...(dataFim ? { dataFim } : {}),
      ...(!semAulaTipo && hora ? { hora } : {}),
      ...(!semAulaTipo && horaFim ? { horaFim } : {}),
    };
    try {
      const r = inicial
        ? await api<Evento>(`/eventos/${inicial.id}`, { method: 'PUT', body: corpo })
        : await api<Evento>('/eventos', { method: 'POST', body: corpo });
      toast(inicial ? `Evento atualizado${r.notificados ? ` — ${r.notificados} pessoa(s) avisada(s)` : ''}.` : `Evento cadastrado — ${r.notificados ?? 0} pessoa(s) avisada(s).`);
      avisarNotificacoes();
      onSalvo();
    } catch (err) {
      setErro(err as ApiError);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="form" onSubmit={enviar} noValidate>
      {erro && !erro.detalhes?.length && <div className="alert alert-red" role="alert"><Icon name="alert" size={18} />{erro.message}</div>}
      <Field label="Título" error={msg('titulo')}><input value={titulo} maxLength={120} onChange={(e) => setTitulo(e.target.value)} data-testid="ev-titulo" /></Field>
      <div className="form-row">
        <Field label="Tipo" error={msg('tipo')}>
          <select value={tipo} onChange={(e) => setTipo(e.target.value as TipoEvento)} data-testid="ev-tipo">{TIPOS.map((t) => <option key={t.v} value={t.v}>{t.r}</option>)}</select>
        </Field>
        <Field label="Quem vê" error={msg('publico')} hint={semAulaTipo ? 'Feriados e recessos valem para toda a escola.' : inicial ? 'O público não pode ser alterado depois de cadastrado.' : undefined}>
          <select value={publicoEfetivo} disabled={semAulaTipo || !!inicial} onChange={(e) => setPublico(e.target.value as PublicoComunicado)} data-testid="ev-publico">
            {PUBLICOS.map((p) => <option key={p.v} value={p.v}>{p.r}</option>)}
          </select>
        </Field>
      </div>
      {publicoEfetivo === 'TURMA' && (
        <Field label="Turma" error={msg('idTurma')}>
          <select value={idTurma} disabled={!!inicial} onChange={(e) => setIdTurma(e.target.value ? Number(e.target.value) : '')}>
            {inicial && <option value={inicial.idTurma ?? ''}>{inicial.turma}</option>}
            {!inicial && turmas.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
          </select>
        </Field>
      )}
      <div className="form-row">
        <Field label="Data" error={msg('data')}><input type="date" value={data} onChange={(e) => setData(e.target.value)} data-testid="ev-data" /></Field>
        <Field label="Até (opcional)" error={msg('dataFim')}><input type="date" value={dataFim} min={data} onChange={(e) => setDataFim(e.target.value)} data-testid="ev-data-fim" /></Field>
      </div>
      {!semAulaTipo && (
        <div className="form-row">
          <Field label="Hora (vazio = dia todo)" error={msg('hora')}><input type="time" value={hora} onChange={(e) => setHora(e.target.value)} data-testid="ev-hora" /></Field>
          <Field label="Hora final" error={msg('horaFim')}><input type="time" value={horaFim} onChange={(e) => setHoraFim(e.target.value)} /></Field>
        </div>
      )}
      <Field label="Descrição (opcional)" error={msg('descricao')}><textarea rows={3} value={descricao} maxLength={1000} onChange={(e) => setDescricao(e.target.value)} /></Field>
      <div className="modal-actions">
        <button type="button" className="btn btn-secondary" onClick={onCancelar}>Cancelar</button>
        <button className="btn btn-primary" disabled={enviando} data-testid="ev-salvar">{enviando ? 'Salvando…' : inicial ? 'Salvar alterações' : 'Cadastrar evento'}</button>
      </div>
    </form>
  );
}

/** Calendário escolar (PB17): visão mensal; coordenação e administração cadastram eventos, feriados e recessos. */
export default function Calendario() {
  const { user } = useAuth();
  const perfil = user!.perfil;
  const podeEditar = perfil === 'COORDENADOR' || perfil === 'ADMIN';
  const toast = useToast();
  const hoje = hojeISO();
  const [mes, setMes] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const [selecionado, setSelecionado] = useState(hoje);
  const [detalhe, setDetalhe] = useState<ItemAgenda | null>(null);
  const [editando, setEditando] = useState<Evento | 'novo' | null>(null);
  const [excluindo, setExcluindo] = useState<ItemAgenda | null>(null);
  const [erroExcluir, setErroExcluir] = useState<string | null>(null);

  const primeiro = new Date(mes.getFullYear(), mes.getMonth(), 1);
  const gradeIni = somarDias(primeiro, -((primeiro.getDay() + 6) % 7));
  const dias = useMemo(() => Array.from({ length: 42 }, (_, k) => iso(somarDias(gradeIni, k))), [gradeIni.getTime()]); // eslint-disable-line react-hooks/exhaustive-deps
  const semanas = Math.ceil(((primeiro.getDay() + 6) % 7 + new Date(mes.getFullYear(), mes.getMonth() + 1, 0).getDate()) / 7);
  const visiveis = dias.slice(0, semanas * 7);

  const { data, erro, carregando, recarregar } = useApi<{ itens: ItemAgenda[] }>(`/agenda?inicio=${visiveis[0]}&fim=${visiveis[visiveis.length - 1]}&tipos=EVENTO,AVALIACAO,ATIVIDADE`);
  const itens = data?.itens ?? [];

  const [tds, setTds] = useState<TurmaDisciplina[]>([]);
  useEffect(() => { if (podeEditar) api<TurmaDisciplina[]>('/catalogo/turma-disciplinas').then(setTds).catch(() => undefined); }, [podeEditar]);
  const turmas = useMemo(() => { const m = new Map<number, string>(); tds.forEach((t) => m.set(t.idTurma, t.turma)); return [...m].map(([id, nome]) => ({ id, nome })); }, [tds]);

  const doDia = (d: string) => itens.filter((i) => cobreDia(i, d));
  const selecionados = doDia(selecionado);
  const mudarMes = (n: number) => { const novo = new Date(mes.getFullYear(), mes.getMonth() + n, 1); setMes(novo); setSelecionado(hoje.slice(0, 7) === iso(novo).slice(0, 7) ? hoje : iso(novo)); };

  async function abrirEdicao(i: ItemAgenda) {
    try { setEditando(await api<Evento>(`/eventos/${i.refId}`)); } catch (e) { toast((e as ApiError).message, 'erro'); }
  }
  async function confirmarExclusao() {
    if (!excluindo) return;
    setErroExcluir(null);
    try {
      await api(`/eventos/${excluindo.refId}`, { method: 'DELETE' });
      toast('Evento cancelado e público avisado.');
      avisarNotificacoes();
      setExcluindo(null);
      recarregar();
    } catch (e) { setErroExcluir((e as ApiError).message); }
  }

  const proximosEventos = useMemo(() => itens.filter((i) => i.tipo === 'EVENTO' && (i.fim ?? i.inicio).slice(0, 10) >= hoje).sort((a, b) => a.inicio.localeCompare(b.inicio)).slice(0, 4), [itens, hoje]);

  return (
    <>
      <PageHeader titulo="Calendário Escolar" subtitulo={podeEditar ? 'Eventos, reuniões, feriados e recessos da escola. O público é avisado a cada mudança.' : 'Eventos, feriados, provas e entregas do mês.'}
        extra={podeEditar ? <button className="btn btn-primary" onClick={() => setEditando('novo')} data-testid="novo-evento"><Icon name="plus" size={16} />Novo evento</button> : undefined} />

      <Card>
        <div className="toolbar ag-toolbar">
          <div className="ag-nav" role="group" aria-label="Navegar entre os meses">
            <button className="btn btn-secondary btn-sm" onClick={() => mudarMes(-1)} aria-label="Mês anterior" data-testid="mes-ant"><Icon name="left" size={16} /></button>
            <button className="btn btn-secondary btn-sm" onClick={() => { const d = new Date(); setMes(new Date(d.getFullYear(), d.getMonth(), 1)); setSelecionado(hoje); }} data-testid="mes-hoje">Hoje</button>
            <button className="btn btn-secondary btn-sm" onClick={() => mudarMes(1)} aria-label="Próximo mês" data-testid="mes-prox"><Icon name="right" size={16} /></button>
          </div>
          <h2 className="ag-titulo" aria-live="polite" data-testid="mes-titulo">{MESES[mes.getMonth()]} de {mes.getFullYear()}</h2>
          <span className="grow" />
          <Legenda />
        </div>

        {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
        {carregando && !data && <Loading />}

        <div className="cal-layout">
          <div className="cal" role="grid" aria-label={`${MESES[mes.getMonth()]} de ${mes.getFullYear()}`} data-testid="mes">
            <div className="cal-cab" role="row">{DIAS_CURTOS.map((d) => <span key={d} role="columnheader">{d}</span>)}</div>
            <div className="cal-corpo">
              {visiveis.map((d) => {
                const dt = doISO(d);
                const lista = doDia(d);
                const folga = lista.find(semAula);
                const fora = dt.getMonth() !== mes.getMonth();
                const fds = dt.getDay() === 0 || dt.getDay() === 6;
                return (
                  <button key={d} role="gridcell" aria-selected={d === selecionado}
                    className={`cal-dia ${fora ? 'fora' : ''} ${fds ? 'fds' : ''} ${d === hoje ? 'hoje' : ''} ${d === selecionado ? 'sel' : ''} ${folga ? 'folga' : ''}`}
                    onClick={() => setSelecionado(d)} data-dia={d}
                    aria-label={`${dt.getDate()} de ${MESES[dt.getMonth()]!.toLowerCase()}${lista.length ? `, ${lista.length} compromisso(s)` : ''}${folga ? `, ${folga.titulo}` : ''}`}>
                    <span className="cal-num">{dt.getDate()}</span>
                    <span className="cal-pontos" aria-hidden="true">
                      {[...new Set(lista.map((i) => infoDe(i.categoria).cls))].map((cls) => <span key={cls} className={`ag-ponto ${cls}`} />)}
                      {lista.length > 1 && <small>{lista.length}</small>}
                    </span>
                    {folga && <small className="cal-folga">{folga.titulo}</small>}
                  </button>
                );
              })}
            </div>
          </div>

          <aside className="cal-lateral" aria-live="polite" data-testid="painel-dia">
            <h3>{doISO(selecionado).getDate()} de {MESES[doISO(selecionado).getMonth()]!.toLowerCase()}{selecionado === hoje && <> <Badge tone="teal">Hoje</Badge></>}</h3>
            {!selecionados.length && <Empty>Nada marcado neste dia.</Empty>}
            <ul className="list">
              {selecionados.map((i) => (
                <li className="row" key={i.id} data-testid="item-dia">
                  <button className="row-main link-btn" style={{ textAlign: 'left' }} onClick={() => setDetalhe(i)}>
                    <strong>{i.titulo}</strong>
                    <small>{quandoItem(i)}{i.turma ? ` · ${i.turma}` : ''}</small>
                  </button>
                  <ChipTipo categoria={i.categoria} />
                  {podeEditar && i.tipo === 'EVENTO' && (
                    <span className="row-acoes">
                      <button className="btn btn-secondary btn-sm" onClick={() => abrirEdicao(i)} aria-label={`Editar ${i.titulo}`} data-testid="editar-evento"><Icon name="edit" size={14} /></button>
                      <button className="btn btn-secondary btn-sm" onClick={() => { setErroExcluir(null); setExcluindo(i); }} aria-label={`Cancelar ${i.titulo}`} data-testid="excluir-evento"><Icon name="trash" size={14} /></button>
                    </span>
                  )}
                </li>
              ))}
            </ul>
            {podeEditar && <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }} onClick={() => setEditando('novo')}><Icon name="plus" size={14} />Cadastrar neste mês</button>}
            {proximosEventos.length > 0 && (
              <>
                <h4 className="cal-sub">Próximos eventos do mês</h4>
                <ul className="cal-prox">{proximosEventos.map((e) => <li key={e.id}><button className="link-btn" onClick={() => { setSelecionado(e.inicio.slice(0, 10)); setDetalhe(e); }}>{e.inicio.slice(8, 10)}/{e.inicio.slice(5, 7)} · {e.titulo}</button></li>)}</ul>
              </>
            )}
          </aside>
        </div>
      </Card>

      {detalhe && <DetalheItem item={detalhe} onClose={() => setDetalhe(null)} />}
      {editando && (
        <Modal titulo={editando === 'novo' ? 'Novo evento' : 'Editar evento'} onClose={() => setEditando(null)}>
          <EventoForm inicial={editando === 'novo' ? undefined : editando} dataInicial={selecionado} turmas={turmas} onCancelar={() => setEditando(null)} onSalvo={() => { setEditando(null); recarregar(); }} />
        </Modal>
      )}
      {excluindo && (
        <Modal titulo="Cancelar evento" onClose={() => setExcluindo(null)}>
          <p>Cancelar <strong>{excluindo.titulo}</strong>? O público-alvo será avisado do cancelamento.</p>
          {erroExcluir && <div className="alert alert-red" role="alert"><Icon name="alert" size={18} />{erroExcluir}</div>}
          <div className="modal-actions">
            <button className="btn btn-secondary" onClick={() => setExcluindo(null)}>Manter evento</button>
            <button className="btn btn-danger" onClick={confirmarExclusao} data-testid="confirmar-exclusao">Cancelar evento</button>
          </div>
        </Modal>
      )}
    </>
  );
}
