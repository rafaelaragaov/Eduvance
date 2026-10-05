import { useEffect, useState } from 'react';
import { api } from '../api';
import { useAuth } from '../auth';
import { navigate } from '../router';
import type { DashProfessor as D, TurmaDisciplina } from '../types';
import { Badge, Card, Empty, ErrorBox, Loading, PageHeader, Tone, useApi } from '../ui';
import AtividadeForm from './AtividadeForm';
import NotasRapido from './NotasRapido';

const aulaTone: Record<string, Tone> = { 'Concluída': 'green', 'Em andamento': 'amber', 'Próxima': 'blue' };

export default function DashProfessor() {
  const { user } = useAuth();
  const { data: d, erro, carregando, recarregar } = useApi<D>('/dashboard');
  const [tds, setTds] = useState<TurmaDisciplina[]>([]);
  useEffect(() => { api<TurmaDisciplina[]>('/catalogo/turma-disciplinas').then(setTds).catch(() => setTds([])); }, []);
  const nome = user!.nome.replace(/^Prof(\.|essor|essora)?\s+/i, '').split(' ')[0];

  return (
    <>
      <PageHeader titulo={`Olá, Prof. ${nome}!`} subtitulo="Acompanhe suas aulas de hoje, publique notas e atividades rapidamente." />
      {carregando && !d && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {d && (
        <>
          <h2 className="section-title">Minhas Turmas</h2>
          <div className="turmas">
            {d.turmas.map((t) => (
              <div className="card turma-card" key={t.id}>
                <header><h3>{t.turma}</h3><span className="chip">{t.disciplina}</span></header>
                <p>{t.alunos} alunos</p>
                <p className="muted">Próxima Aula: {t.proximaAula ?? 'sem horário'}</p>
              </div>
            ))}
            {!d.turmas.length && <Card><Empty>Você ainda não está vinculado a nenhuma turma.</Empty></Card>}
          </div>

          <div className="grid-2">
            <div className="col">
              <NotasRapido />
              <Card title="Nova Atividade / Tarefa">
                <AtividadeForm tds={tds} compacto onSalvo={() => { recarregar(); navigate('/atividades'); }} />
              </Card>
            </div>
            <div className="col">
              <Card title="Aulas de Hoje (Cronograma)">
                {d.aulasHoje.map((a) => (
                  <div className="agenda-item" key={a.idHorario}>
                    <span className="time">{a.inicio} - {a.fim}</span>
                    <div style={{ flex: 1 }}><strong>{a.turma}</strong><small className="muted">{a.disciplina} • Sala {a.sala}</small></div>
                    <Badge tone={aulaTone[a.status]}>{a.status}</Badge>
                  </div>
                ))}
                {!d.aulasHoje.length && <Empty>Sem aulas programadas para hoje.</Empty>}
              </Card>
            </div>
          </div>
        </>
      )}
    </>
  );
}
