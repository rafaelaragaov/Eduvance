import { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { diaMes, moeda, nota, quando } from '../format';
import { Icon } from '../icons';
import { Link } from '../router';
import type { DashResponsavel as D, ResumoAluno } from '../types';
import { Avatar, Badge, Card, Empty, ErrorBox, Loading, PageHeader, useApi } from '../ui';

export default function DashResponsavel() {
  const { user } = useAuth();
  const { data: d, erro, carregando, recarregar } = useApi<D>('/dashboard');
  const [sel, setSel] = useState<number | null>(null);
  useEffect(() => { if (d && sel === null && d.alunos[0]) setSel(d.alunos[0].id); }, [d, sel]);
  const { data: r, erro: erroR, carregando: carR } = useApi<ResumoAluno>(sel ? `/alunos/${sel}/resumo` : null);
  const nome = user!.nome.split(' ')[0];
  const aluno = d?.alunos.find((a) => a.id === sel);

  return (
    <>
      <PageHeader titulo={`Olá, ${nome}!`} subtitulo="Gerencie as atividades escolares, boletins e financeiro de seus filhos." />
      {carregando && !d && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {d && (
        <>
          <h2 className="section-title">Alunos Vinculados</h2>
          <div className="grid-2" style={{ marginBottom: 20 }}>
            {d.alunos.map((a) => (
              <button key={a.id} className={`aluno-card ${a.id === sel ? 'on' : ''}`} onClick={() => setSel(a.id)} aria-pressed={a.id === sel}>
                <Avatar nome={a.nome} size={48} />
                <div>
                  <strong>{a.nome}</strong>
                  <small className="muted">{a.turma ?? a.serie} • Turno Matutino</small>
                  <div className="meta"><span className="m1">Média Geral: {nota(a.mediaGeral)}</span><span className="m2">Faltas: {a.faltas}</span></div>
                </div>
                {a.id === sel && <span className="tick"><Icon name="check" size={14} /></span>}
              </button>
            ))}
            {!d.alunos.length && <Card><Empty>Nenhum aluno vinculado à sua conta. Procure a secretaria.</Empty></Card>}
          </div>

          {sel && (
            <>
              {carR && !r && <Loading />}
              {erroR && <ErrorBox erro={erroR} />}
              {r && (
                <div className="grid-2">
                  <Card title={`Boletim Rápido: ${aluno?.nome.split(' ')[0]}`} action={<Link to="/boletim" className="card-link">Histórico Completo</Link>}>
                    <table className="table">
                      <tbody>
                        {r.boletim.map((b) => (
                          <tr key={b.idTurmaDisciplina}>
                            <td style={{ borderTop: 0, borderBottom: '1px solid var(--line)' }}>
                              <strong>{b.materia}</strong><br /><small className="muted">{b.frequencia === null ? '—' : `${b.frequencia}%`} freq.</small>
                            </td>
                            <td className="num" style={{ borderTop: 0, borderBottom: '1px solid var(--line)', fontSize: 16 }}>{nota(b.nota)}</td>
                            <td style={{ borderTop: 0, borderBottom: '1px solid var(--line)' }}><Badge tone={b.status === 'Aprovado' ? 'green' : b.status === 'Recuperação' ? 'red' : 'gray'}>{b.status}</Badge></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </Card>

                  <div className="col">
                    <Card title="Mensalidades & Financeiro">
                      <div className="list">
                        {r.mensalidades.map((m) => {
                          const d = new Date(m.vencimento + 'T00:00:00');
                          const mes = d.toLocaleDateString('pt-BR', { month: 'long' });
                          const paga = m.status === 'PAGA';
                          return (
                            <div className={`mensalidade ${paga ? '' : 'aberta'}`} key={m.id}>
                              <span className="ico"><Icon name={paga ? 'checkCircle' : 'card'} size={22} /></span>
                              <div style={{ flex: 1 }}>
                                <strong>{mes[0]!.toUpperCase() + mes.slice(1)}/{d.getFullYear()}</strong>
                                <small className="muted">{moeda(m.valor)} • {paga ? `Pago via ${m.formaPagamento ?? '—'}` : `Vence em ${diaMes(m.vencimento)}`}</small>
                              </div>
                              <Badge tone={paga ? 'green' : m.status === 'ATRASADA' ? 'red' : 'amber'}>{paga ? 'Paga' : m.status === 'ATRASADA' ? 'Atrasada' : `Vence ${diaMes(m.vencimento)}`}</Badge>
                            </div>
                          );
                        })}
                        {!r.mensalidades.length && <Empty>Sem mensalidades registradas.</Empty>}
                      </div>
                    </Card>
                    <Card title="Ocorrências Recentes">
                      <div className="list">
                        {r.ocorrencias.map((o) => (
                          <div className="ocorrencia" key={o.id} style={o.status === 'RESOLVIDA' ? { background: 'var(--gray-bg)', color: 'var(--gray)' } : undefined}>
                            <Icon name="alert" size={18} />
                            <div><strong style={o.status === 'RESOLVIDA' ? { color: 'var(--gray)' } : undefined}>{o.titulo}</strong><p style={o.status === 'RESOLVIDA' ? { color: 'var(--gray)' } : undefined}>{o.descricao}</p><small>{quando(o.data)}{o.status === 'RESOLVIDA' ? ' • resolvida' : ''}</small></div>
                          </div>
                        ))}
                        {!r.ocorrencias.length && <Empty>Nenhuma ocorrência registrada.</Empty>}
                      </div>
                    </Card>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </>
  );
}
