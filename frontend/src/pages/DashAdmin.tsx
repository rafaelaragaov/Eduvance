import { Link } from '../router';
import type { DashAdmin as D } from '../types';
import { Card, ErrorBox, Loading, PageHeader, Stat, useApi } from '../ui';

export default function DashAdmin() {
  const { data: d, erro, carregando, recarregar } = useApi<D>('/dashboard');
  const p = d?.usuariosPorPerfil ?? {};
  const total = Object.values(p).reduce((a, b) => a + b, 0);
  return (
    <>
      <PageHeader titulo="Olá, Administrador!" subtitulo="Visão geral do sistema e gerenciamento de usuários." />
      {carregando && !d && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {d && (
        <>
          <div className="grid-3">
            <Stat label="Usuários" value={total} badge="Cadastrados" tone="teal" icon="users" />
            <Stat label="Turmas" value={d.turmas} badge={`${d.disciplinas} disciplinas`} tone="blue" icon="book" />
            <Stat label="Atividades" value={d.atividades} badge="Publicadas" tone="green" icon="file" />
          </div>
          <div className="grid-2">
            <Card title="Usuários por perfil" action={<Link to="/usuarios" className="card-link">Gerenciar</Link>}>
              <div className="list">
                {[['ALUNO', 'Alunos'], ['RESPONSAVEL', 'Responsáveis'], ['PROFESSOR', 'Professores'], ['COORDENADOR', 'Coordenadores'], ['ADMIN', 'Administradores']].map(([k, rot]) => (
                  <div className="row" key={k}><strong>{rot}</strong><span className="chip">{p[k!] ?? 0}</span></div>
                ))}
              </div>
            </Card>
            <Card title="Atalhos">
              <div className="list">
                <Link to="/usuarios" className="btn btn-secondary">Cadastrar / editar usuários</Link>
                <Link to="/atividades" className="btn btn-secondary">Gerenciar atividades</Link>
                <Link to="/notas" className="btn btn-secondary">Consultar notas por turma</Link>
              </div>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
