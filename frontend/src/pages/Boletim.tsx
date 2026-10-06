import { Fragment, useEffect, useState } from 'react';
import { api } from '../api';
import { useAuth } from '../auth';
import { dataBR, nota } from '../format';
import { Icon } from '../icons';
import { Link, navigate } from '../router';
import type { AlunoCatalogo, BoletimCompleto, DashResponsavel } from '../types';
import { Badge, Card, Empty, ErrorBox, Loading, PageHeader, Stat, useApi } from '../ui';
import { rotuloTipo, situacaoTone } from './academico';

function SeletorDeAluno() {
  const [busca, setBusca] = useState('');
  const [lista, setLista] = useState<AlunoCatalogo[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  useEffect(() => {
    const t = setTimeout(() => api<AlunoCatalogo[]>(`/catalogo/alunos?busca=${encodeURIComponent(busca)}`).then(setLista).catch((e) => setErro(e.message)), 250);
    return () => clearTimeout(t);
  }, [busca]);
  return (
    <Card title="Selecione um aluno">
      <div className="toolbar"><input className="grow" type="search" placeholder="Buscar por nome ou matrícula…" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Buscar aluno" /></div>
      {erro && <ErrorBox erro={erro} />}
      {!lista && !erro && <Loading />}
      <div className="list" style={{ maxHeight: 420, overflowY: 'auto' }}>
        {lista?.map((a) => (
          <button key={a.id} className="row" style={{ width: '100%', textAlign: 'left', background: 'none', border: 0, cursor: 'pointer' }} onClick={() => navigate(`/boletim/${a.id}`)}>
            <div className="row-main"><strong>{a.nome}</strong><small>Mat. {a.matricula} · {a.turma ?? 'sem turma'}</small></div>
            <Icon name="eye" size={16} />
          </button>
        ))}
      </div>
      {lista && !lista.length && <Empty>Nenhum aluno encontrado.</Empty>}
    </Card>
  );
}

function Detalhe({ id }: { id: number }) {
  const { data: b, erro, carregando, recarregar } = useApi<BoletimCompleto>(`/boletim/${id}`);
  const [aberta, setAberta] = useState<number | null>(null);
  if (carregando && !b) return <Loading />;
  if (erro) return <ErrorBox erro={erro} onRetry={recarregar} />;
  if (!b) return null;
  const freqOk = b.frequenciaGeral === null || b.frequenciaGeral >= b.frequenciaMinima;
  return (
    <>
      <h2 className="section-title">{b.aluno.nome}{b.aluno.turma ? ` — ${b.aluno.turma}` : ''}</h2>
      <div className="grid-3">
        <Stat label="Média Geral" value={nota(b.mediaGeral)} badge={b.mediaGeral === null ? 'Sem notas' : b.mediaGeral >= b.mediaAprovacao ? 'Acima da média' : 'Atenção'} tone={b.mediaGeral === null ? 'gray' : b.mediaGeral >= b.mediaAprovacao ? 'green' : 'red'} icon="award" />
        <Stat label="Frequência Geral" value={b.frequenciaGeral === null ? '—' : `${b.frequenciaGeral.toFixed(0)}%`} badge={freqOk ? 'Regular' : `Mínimo ${b.frequenciaMinima.toFixed(0)}%`} tone={freqOk ? 'teal' : 'red'} icon="checkCircle" />
        <Stat label="Faltas Acumuladas" value={b.faltasTotal} icon="info" />
      </div>
      <Card title="Notas por disciplina" action={<button className="link-btn no-print" onClick={() => window.print()}>Imprimir boletim</button>}>
        <div className="table-scroll">
          <table className="table bol-table">
            <thead><tr><th>Disciplina</th>{[1, 2, 3, 4].map((n) => <th key={n} className="num">{n}º B</th>)}<th className="num">Média</th><th className="num">Frequência</th><th>Situação</th></tr></thead>
            <tbody>
              {b.disciplinas.map((d) => (
                <Fragment key={d.idTurmaDisciplina}>
                  <tr>
                    <td><button className="expand-btn" onClick={() => setAberta(aberta === d.idTurmaDisciplina ? null : d.idTurmaDisciplina)} aria-expanded={aberta === d.idTurmaDisciplina}>{d.materia}</button><br /><small className="muted">{d.professor ? `Prof. ${d.professor.split(' ')[0]}` : ''}</small></td>
                    {[1, 2, 3, 4].map((n) => <td key={n} className="num">{nota(d.bimestres[String(n)])}</td>)}
                    <td className="num"><strong>{nota(d.mediaParcial)}</strong></td>
                    <td className="num">{d.frequencia === null ? '—' : `${d.frequencia.toFixed(0)}%`}<br /><small className="muted">{d.faltas} falta(s)</small></td>
                    <td><Badge tone={situacaoTone[d.situacao]}>{d.situacao}</Badge></td>
                  </tr>
                  {aberta === d.idTurmaDisciplina && (
                    <tr className="det-row"><td colSpan={8}>
                      {d.avaliacoes.length ? (
                        <ul>{d.avaliacoes.map((a) => (
                          <li key={a.id}><strong>{a.titulo}</strong> ({rotuloTipo(a.tipo)}, {a.bimestre}º bimestre, {dataBR(a.data)}, peso {String(a.peso).replace('.', ',')}): <strong>{a.nota === null ? 'sem nota' : a.nota.toFixed(1)}</strong></li>
                        ))}</ul>
                      ) : 'Nenhuma avaliação cadastrada nesta disciplina.'}
                    </td></tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        {!b.disciplinas.length && <Empty>Nenhuma disciplina vinculada à turma do aluno.</Empty>}
        <p className="muted" style={{ marginTop: 12, fontSize: 12.5 }}>Média parcial = média dos bimestres com nota; cada bimestre é a média ponderada pelo peso das avaliações. Aprovação com média ≥ {b.mediaAprovacao.toFixed(1)} e frequência ≥ {b.frequenciaMinima.toFixed(0)}%. Clique no nome da disciplina para ver as avaliações.</p>
      </Card>
    </>
  );
}

/** Boletim completo: aluno (o próprio), responsável (filhos vinculados) e gestão (qualquer aluno permitido). */
export default function Boletim({ id }: { id?: number }) {
  const { user } = useAuth();
  const perfil = user!.perfil;
  const resp = useApi<DashResponsavel>(perfil === 'RESPONSAVEL' ? '/dashboard' : null);

  let alvo: number | null = null;
  if (perfil === 'ALUNO') alvo = user!.id;
  else if (perfil === 'RESPONSAVEL') alvo = id ?? resp.data?.alunos[0]?.id ?? null;
  else alvo = id ?? null;
  const gestao = perfil !== 'ALUNO' && perfil !== 'RESPONSAVEL';

  return (
    <>
      <PageHeader titulo="Boletim" subtitulo={perfil === 'ALUNO' ? 'Suas notas por bimestre, frequência e situação em cada disciplina.' : perfil === 'RESPONSAVEL' ? 'Desempenho do aluno selecionado em cada disciplina.' : 'Consulte o boletim completo de um aluno.'} />
      {perfil === 'RESPONSAVEL' && resp.data && resp.data.alunos.length > 1 && (
        <div className="tabs" style={{ marginBottom: 16 }}>
          {resp.data.alunos.map((a) => <button key={a.id} className={`tab ${a.id === alvo ? 'on' : ''}`} onClick={() => navigate(`/boletim/${a.id}`)}>{a.nome}</button>)}
        </div>
      )}
      {gestao && alvo !== null && <p className="no-print" style={{ margin: '-8px 0 14px' }}><Link to="/boletim" className="card-link">← Escolher outro aluno</Link></p>}
      {perfil === 'RESPONSAVEL' && resp.carregando && !resp.data && <Loading />}
      {perfil === 'RESPONSAVEL' && resp.data && !resp.data.alunos.length && <Card><Empty>Nenhum aluno vinculado à sua conta.</Empty></Card>}
      {gestao && alvo === null && <SeletorDeAluno />}
      {alvo !== null && <Detalhe id={alvo} />}
    </>
  );
}
