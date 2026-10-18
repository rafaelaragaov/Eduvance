import { useMemo, useState } from 'react';
import { useAuth } from '../auth';
import { api } from '../api';
import { useEffect } from 'react';
import { Icon } from '../icons';
import type { DashResponsavel, ItemAgenda, TipoItemAgenda, TurmaDisciplina } from '../types';
import { Badge, Card, Empty, ErrorBox, Loading, PageHeader, useApi } from '../ui';
import { ChipTipo, cobreDia, DetalheItem, DIAS_CURTOS, doISO, hojeISO, infoDe, iso, Legenda, MESES, quandoItem, segunda, semAula, somarDias } from './agenda-comum';

const FILTROS: { tipo: TipoItemAgenda; rot: string }[] = [
  { tipo: 'AULA', rot: 'Aulas' }, { tipo: 'ATIVIDADE', rot: 'Atividades' }, { tipo: 'AVALIACAO', rot: 'Provas' }, { tipo: 'EVENTO', rot: 'Eventos' },
];

function rotuloSemana(ini: Date): string {
  const fim = somarDias(ini, 6);
  if (ini.getMonth() === fim.getMonth()) return `${ini.getDate()} a ${fim.getDate()} de ${MESES[ini.getMonth()]!.toLowerCase()} de ${fim.getFullYear()}`;
  return `${ini.getDate()} de ${MESES[ini.getMonth()]!.slice(0, 3).toLowerCase()} a ${fim.getDate()} de ${MESES[fim.getMonth()]!.slice(0, 3).toLowerCase()} de ${fim.getFullYear()}`;
}

/** Agenda escolar (PB13): aulas, atividades, provas e eventos da semana, no recorte de cada perfil. */
export default function Agenda() {
  const { user } = useAuth();
  const perfil = user!.perfil;
  const [ref, setRef] = useState(() => segunda(new Date()));
  const [tipos, setTipos] = useState<Set<TipoItemAgenda>>(new Set(['AULA', 'ATIVIDADE', 'AVALIACAO', 'EVENTO']));
  const [idAluno, setIdAluno] = useState('');
  const [idTurma, setIdTurma] = useState('');
  const [aberto, setAberto] = useState<ItemAgenda | null>(null);

  const dash = useApi<DashResponsavel>(perfil === 'RESPONSAVEL' ? '/dashboard' : null);
  const [tds, setTds] = useState<TurmaDisciplina[]>([]);
  useEffect(() => { if (perfil !== 'ALUNO' && perfil !== 'RESPONSAVEL') api<TurmaDisciplina[]>('/catalogo/turma-disciplinas').then(setTds).catch(() => undefined); }, [perfil]);
  const turmas = useMemo(() => { const m = new Map<number, string>(); tds.forEach((t) => m.set(t.idTurma, t.turma)); return [...m]; }, [tds]);

  const inicio = iso(ref);
  const fim = iso(somarDias(ref, 6));
  const qs = `inicio=${inicio}&fim=${fim}${idAluno ? `&idAluno=${idAluno}` : ''}${idTurma ? `&idTurma=${idTurma}` : ''}`;
  const { data, erro, carregando, recarregar } = useApi<{ itens: ItemAgenda[] }>(`/agenda?${qs}`);

  const itens = useMemo(() => (data?.itens ?? []).filter((i) => tipos.has(i.tipo)), [data, tipos]);
  const dias = useMemo(() => Array.from({ length: 7 }, (_, k) => iso(somarDias(ref, k))), [ref]);
  // Sábado e domingo só aparecem quando há algo marcado
  const visiveis = dias.filter((d, k) => k < 5 || itens.some((i) => cobreDia(i, d)));
  const hoje = hojeISO();
  const total = (t: TipoItemAgenda) => itens.filter((i) => i.tipo === t).length;

  function alternar(t: TipoItemAgenda) {
    setTipos((s) => { const n = new Set(s); if (n.has(t)) { if (n.size > 1) n.delete(t); } else n.add(t); return n; });
  }

  const subtitulo = perfil === 'ALUNO' ? 'Suas aulas, atividades, provas e eventos da semana.'
    : perfil === 'RESPONSAVEL' ? 'A semana escolar dos seus filhos: aulas, entregas, provas e eventos.'
    : perfil === 'PROFESSOR' ? 'Suas aulas, entregas, provas e os eventos da escola.' : 'A semana de toda a escola: aulas, entregas, provas e eventos.';

  return (
    <>
      <PageHeader titulo="Agenda Escolar" subtitulo={subtitulo} />

      <Card>
        <div className="toolbar ag-toolbar">
          <div className="ag-nav" role="group" aria-label="Navegar entre as semanas">
            <button className="btn btn-secondary btn-sm" onClick={() => setRef(somarDias(ref, -7))} aria-label="Semana anterior" data-testid="sem-ant"><Icon name="left" size={16} /></button>
            <button className="btn btn-secondary btn-sm" onClick={() => setRef(segunda(new Date()))} data-testid="sem-hoje">Hoje</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setRef(somarDias(ref, 7))} aria-label="Próxima semana" data-testid="sem-prox"><Icon name="right" size={16} /></button>
          </div>
          <h2 className="ag-titulo" aria-live="polite" data-testid="sem-titulo">{rotuloSemana(ref)}</h2>
          <span className="grow" />
          {perfil === 'RESPONSAVEL' && (dash.data?.alunos.length ?? 0) > 1 && (
            <select value={idAluno} onChange={(e) => setIdAluno(e.target.value)} aria-label="Aluno" style={{ width: 'auto' }}>
              <option value="">Todos os filhos</option>
              {dash.data!.alunos.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
            </select>
          )}
          {turmas.length > 1 && (
            <select value={idTurma} onChange={(e) => setIdTurma(e.target.value)} aria-label="Turma" style={{ width: 'auto' }}>
              <option value="">Todas as turmas</option>
              {turmas.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
            </select>
          )}
        </div>
        <div className="toolbar" style={{ marginBottom: 12 }}>
          <div className="tabs" role="group" aria-label="Mostrar na agenda">
            {FILTROS.map((f) => <button key={f.tipo} className={`tab ${tipos.has(f.tipo) ? 'on' : ''}`} aria-pressed={tipos.has(f.tipo)} onClick={() => alternar(f.tipo)} data-testid={`filtro-${f.tipo}`}>{f.rot}{!carregando && <> · {total(f.tipo)}</>}</button>)}
          </div>
          <span className="grow" />
          <Legenda />
        </div>

        {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
        {carregando && !data && <Loading />}
        {data && (
          <div className="ag-semana" style={{ gridTemplateColumns: `repeat(${visiveis.length}, minmax(0, 1fr))` }} data-testid="semana">
            {visiveis.map((d) => {
              const doDia = itens.filter((i) => cobreDia(i, d));
              const folga = doDia.find(semAula);
              const dt = doISO(d);
              return (
                <section key={d} className={`ag-dia ${d === hoje ? 'hoje' : ''} ${folga ? 'folga' : ''}`} aria-label={`${DIAS_CURTOS[(dt.getDay() + 6) % 7]} ${dt.getDate()}`} data-dia={d}>
                  <header>
                    <strong>{DIAS_CURTOS[(dt.getDay() + 6) % 7]}</strong>
                    <span className="ag-num">{dt.getDate()}</span>
                    {d === hoje && <Badge tone="teal">Hoje</Badge>}
                  </header>
                  {folga && <p className="ag-folga-txt">{infoDe(folga.categoria).rot}: {folga.titulo}<br /><small>Sem aulas</small></p>}
                  {!doDia.length && !folga && <p className="ag-vazio">Nada marcado</p>}
                  <ul>
                    {doDia.filter((i) => !semAula(i)).map((i) => (
                      <li key={i.id}>
                        <button className={`ag-item ${infoDe(i.categoria).cls} ${i.status === 'ENTREGUE' || i.status === 'CORRIGIDA' ? 'feito' : ''}`} onClick={() => setAberto(i)} data-tipo={i.tipo}>
                          <span className="ag-hora">{quandoItem(i)}</span>
                          <strong>{i.titulo}</strong>
                          <small>{[i.tipo === 'AULA' ? (perfil === 'ALUNO' || perfil === 'RESPONSAVEL' ? i.sala && `Sala ${i.sala}` : [i.turma, i.sala && `Sala ${i.sala}`].filter(Boolean).join(' · ')) : i.turma, i.aluno].filter(Boolean).join(' · ')}</small>
                          {i.tipo !== 'AULA' && <ChipTipo categoria={i.categoria} />}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>
        )}
        {data && !itens.length && <Empty>Nada marcado nesta semana para os filtros escolhidos.</Empty>}
      </Card>

      {aberto && <DetalheItem item={aberto} onClose={() => setAberto(null)} />}
    </>
  );
}
