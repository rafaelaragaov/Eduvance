import { useAuth } from '../auth';
import { diaMesCurto, nota, quando } from '../format';
import { Link } from '../router';
import type { DashAluno as D, Urgencia } from '../types';
import { Badge, Card, Empty, ErrorBox, Loading, PageHeader, Stat, Tone, useApi } from '../ui';

export const urgenciaBadge: Record<Urgencia, { tone: Tone; texto: string }> = {
  ATRASADA: { tone: 'red', texto: 'Atrasada' },
  URGENTE: { tone: 'red', texto: 'Urgente' },
  PENDENTE: { tone: 'amber', texto: 'Pendente' },
  PLANEJADA: { tone: 'blue', texto: 'Planejado' },
  ENTREGUE: { tone: 'green', texto: 'Entregue' },
};

const statusTone = (s: string): Tone => (s === 'Aprovado' ? 'green' : s === 'Recuperação' ? 'red' : 'gray');

export default function DashAluno() {
  const { user } = useAuth();
  const { data: d, erro, carregando, recarregar } = useApi<D>('/dashboard');
  const primeiro = user!.nome.split(' ')[0];

  return (
    <>
      <PageHeader titulo={`Olá, ${primeiro}!`} subtitulo="Acompanhe o seu progresso escolar, notas e tarefas para hoje." />
      {carregando && !d && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {d && (
        <>
          <div className="grid-3">
            <Stat label="Média Geral" value={nota(d.mediaGeral)} badge={d.classificacaoMedia} tone={d.classificacaoMedia === 'Excelente' ? 'green' : d.classificacaoMedia === 'Atenção' ? 'red' : 'amber'} icon="award" />
            <Stat label="Faltas Acumuladas" value={d.faltas} badge={d.faltasStatus} tone={d.faltasStatus === 'Dentro do limite' ? 'teal' : 'red'} icon="info" />
            <Stat label="Atividades Pendentes" value={d.atividadesPendentes} badge={d.atividadesStatus} tone={d.atividadesStatus === 'Em dia' ? 'green' : 'amber'} icon="clock" />
          </div>

          <div className="grid-2">
            <div className="col">
              <Card title="Boletim Resumido" action={<Link to="/boletim" className="card-link">Ver Boletim Completo</Link>}>
                <div className="table-scroll">
                  <table className="table">
                    <thead><tr><th>Matéria</th><th className="num">Nota (B{d.bimestre})</th><th>Status</th></tr></thead>
                    <tbody>
                      {d.boletim.map((b) => (
                        <tr key={b.idTurmaDisciplina}>
                          <td>{b.materia}</td>
                          <td className="num">{nota(b.nota)}</td>
                          <td><Badge tone={statusTone(b.status)}>{b.status}</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!d.boletim.length && <Empty>Nenhuma disciplina vinculada à sua turma.</Empty>}
              </Card>

              <Card title="Atividades Pendentes" action={<Link to="/atividades" className="card-link">Ver todas</Link>}>
                <div className="list">
                  {d.atividades.map((a) => {
                    const b = urgenciaBadge[a.urgencia];
                    return (
                      <div className="row" key={a.id}>
                        <div className="row-main">
                          <strong>{a.titulo}</strong>
                          <small>{a.disciplina} • Prazo: {quando(a.dataEntrega)}</small>
                        </div>
                        <Badge tone={b.tone}>{b.texto}</Badge>
                      </div>
                    );
                  })}
                  {!d.atividades.length && <Empty>Você não tem atividades pendentes. 🎉</Empty>}
                </div>
              </Card>
            </div>

            <div className="col">
              <Card title="Agenda do Dia">
                {d.agendaHoje.map((a) => (
                  <div className="agenda-item" key={a.idHorario}>
                    <span className="time">{a.inicio} - {a.fim}</span>
                    <div><strong>{a.disciplina}</strong><small className="muted">Sala {a.sala} • Prof. {a.professor?.split(' ')[0]}</small></div>
                  </div>
                ))}
                {!d.agendaHoje.length && <Empty>Sem aulas hoje.</Empty>}
              </Card>

              <Card title="Comunicados Recentes" action={<Link to="/comunicados" className="card-link">Ver todos</Link>}>
                <div className="list">
                  {d.comunicados.map((c) => {
                    const { dia, mes } = diaMesCurto(c.data);
                    return (
                      <div className="evento" key={c.id}>
                        <span className="date-chip big"><span>{dia}</span><small>{mes}</small></span>
                        <div><strong>{c.titulo}</strong><br /><small className="muted">{c.mensagem}</small></div>
                      </div>
                    );
                  })}
                  {!d.comunicados.length && <Empty>Nenhum comunicado.</Empty>}
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
    </>
  );
}
