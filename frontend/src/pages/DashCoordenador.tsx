import { useAuth } from '../auth';
import { diaMes, quando } from '../format';
import { Icon } from '../icons';
import { Link } from '../router';
import type { DashCoordenador as D } from '../types';
import { Badge, Card, Empty, ErrorBox, Loading, PageHeader, Tone, useApi } from '../ui';

export default function DashCoordenador() {
  const { user } = useAuth();
  const { data: d, erro, carregando, recarregar } = useApi<D>('/dashboard');
  const nome = user!.nome.split(' ')[0];
  const k = d?.kpis;
  const meta = k && k.taxaFrequencia !== null && k.taxaFrequencia >= k.metaFrequencia;

  const kpi = (label: string, valor: string | number, badge: string, tone: Tone) => (
    <div className="card stat" key={label}>
      <div className="stat-top"><span className="stat-label">{label}</span><span className="stat-icon"><Icon name="award" size={16} /></span></div>
      <div className="stat-value"><strong>{valor}</strong><Badge tone={tone}>{badge}</Badge></div>
    </div>
  );

  return (
    <>
      <PageHeader titulo={`Olá, Coordenadora ${nome}!`} subtitulo="Acompanhe o rendimento geral da instituição, grade de professores e ocorrências ativas." />
      {carregando && !d && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {d && k && (
        <>
          <div className="grid-3">
            {kpi('Professores Ativos', k.professoresAtivos, 'Completo', 'green')}
            {kpi('Ocorrências em Aberto', k.ocorrenciasAbertas, k.ocorrenciasAbertas ? 'Ação Necessária' : 'Em dia', k.ocorrenciasAbertas ? 'amber' : 'green')}
            {kpi('Taxa de Frequência', k.taxaFrequencia === null ? '—' : `${k.taxaFrequencia.toFixed(1)}%`, meta ? 'Meta Batida' : `Meta ${k.metaFrequencia}%`, meta ? 'green' : 'amber')}
          </div>

          <div className="grid-2">
            <div className="col">
              <Card title="Gerenciar Professores" action={<Link to="/professores" className="card-link">Ver Todos</Link>}>
                <table className="table">
                  <thead><tr><th>Professor</th><th>Disciplina</th><th>Ações</th></tr></thead>
                  <tbody>
                    {d.professores.map((p) => (
                      <tr key={p.id}>
                        <td>Prof. {p.nome}</td>
                        <td className="muted" style={{ textAlign: 'left' }}>{p.disciplina}</td>
                        <td><Link to="/professores" className="card-link">Editar</Link></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
              <Card title="Horários das Turmas (Hoje)">
                <div className="list" style={{ maxHeight: 300, overflowY: 'auto' }}>
                  {d.horariosHoje.map((a) => (
                    <div className="agenda-box" key={a.idHorario}>
                      <span className="time">{a.inicio} - {a.fim}</span>
                      <div><strong>{a.turma}</strong><br /><small className="muted">{a.disciplina} - Prof. {a.professor?.split(' ')[0]}</small></div>
                    </div>
                  ))}
                  {!d.horariosHoje.length && <Empty>Sem aulas programadas para hoje.</Empty>}
                </div>
              </Card>
            </div>
            <div className="col">
              <Card title="Agenda Escolar">
                <div className="list">
                  {d.eventos.map((e) => (
                    <div className="evento" key={e.id}>
                      <span className="date-chip">{diaMes(e.inicio)}</span>
                      <div><strong>{e.titulo}</strong><br /><small className="muted">{e.descricao}</small></div>
                    </div>
                  ))}
                  {!d.eventos.length && <Empty>Nenhum evento futuro cadastrado.</Empty>}
                </div>
              </Card>
              <Card title="Notificações de Ocorrências" action={<Link to="/ocorrencias" className="card-link">Ver todas</Link>}>
                <div className="list">
                  {d.ocorrencias.map((o) => (
                    <Link to={`/ocorrencias/${o.id}`} className="ocorrencia" key={o.id}>
                      <Icon name="alert" size={18} />
                      <div>
                        <strong>{o.aluno}{o.turma ? ` (${o.turma.replace('º Ano ', 'º ')})` : ''}</strong>
                        <p>{o.titulo}</p>
                        <small>{quando(o.data)}</small>
                      </div>
                    </Link>
                  ))}
                  {!d.ocorrencias.length && <Empty>Nenhuma ocorrência em aberto.</Empty>}
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
    </>
  );
}
