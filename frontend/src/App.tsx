import { ReactNode } from 'react';
import { useAuth } from './auth';
import { Icon } from './icons';
import { casa, Link, usePath } from './router';
import { NAV, Shell } from './Shell';
import type { Perfil } from './types';
import { Loading } from './ui';
import Atividades from './pages/Atividades';
import Boletim from './pages/Boletim';
import Frequencia from './pages/Frequencia';
import Avaliacoes from './pages/Avaliacoes';
import DashAdmin from './pages/DashAdmin';
import DashAluno from './pages/DashAluno';
import DashCoordenador from './pages/DashCoordenador';
import DashProfessor from './pages/DashProfessor';
import DashResponsavel from './pages/DashResponsavel';
import Login from './pages/Login';
import Notas, { EscolherAvaliacao } from './pages/Notas';
import Usuarios from './pages/Usuarios';
import Vestibular from './pages/Vestibular';

function Home({ perfil }: { perfil: Perfil }) {
  switch (perfil) {
    case 'ALUNO': return <DashAluno />;
    case 'PROFESSOR': return <DashProfessor />;
    case 'COORDENADOR': return <DashCoordenador />;
    case 'RESPONSAVEL': return <DashResponsavel />;
    default: return <DashAdmin />;
  }
}

function Mensagem({ icone, titulo, texto, pb }: { icone: 'hourglass' | 'lock' | 'search'; titulo: string; texto: string; pb?: string }) {
  return (
    <div className="card soon">
      <div className="ico"><Icon name={icone} size={30} /></div>
      <h2>{titulo}</h2>
      <p>{texto}{pb && <> <span className="chip">{pb}</span></>}</p>
      <Link to="/" className="btn btn-secondary">Voltar ao Dashboard</Link>
    </div>
  );
}

/** Rotas implementadas, com os perfis autorizados (controle de acesso também na interface). */
const ROTAS: { path: string; perfis: Perfil[]; el: (p: Perfil, params: Record<string, string>) => ReactNode }[] = [
  { path: '/', perfis: ['ADMIN', 'COORDENADOR', 'PROFESSOR', 'ALUNO', 'RESPONSAVEL'], el: (p) => <Home perfil={p} /> },
  { path: '/atividades', perfis: ['ADMIN', 'COORDENADOR', 'PROFESSOR', 'ALUNO', 'RESPONSAVEL'], el: () => <Atividades /> },
  { path: '/usuarios', perfis: ['ADMIN'], el: () => <Usuarios /> },
  { path: '/professores', perfis: ['COORDENADOR'], el: () => <Usuarios somenteProfessores /> },
  { path: '/avaliacoes', perfis: ['ADMIN', 'COORDENADOR', 'PROFESSOR'], el: () => <Avaliacoes /> },
  { path: '/frequencia', perfis: ['ADMIN', 'COORDENADOR', 'PROFESSOR'], el: () => <Frequencia /> },
  { path: '/boletim', perfis: ['ADMIN', 'COORDENADOR', 'PROFESSOR', 'ALUNO', 'RESPONSAVEL'], el: () => <Boletim /> },
  { path: '/boletim/:id', perfis: ['ADMIN', 'COORDENADOR', 'PROFESSOR', 'RESPONSAVEL'], el: (_p, r) => <Boletim id={Number(r.id)} /> },
  { path: '/notas', perfis: ['ADMIN', 'COORDENADOR', 'PROFESSOR'], el: () => <EscolherAvaliacao /> },
  { path: '/notas/:id', perfis: ['ADMIN', 'COORDENADOR', 'PROFESSOR'], el: (_p, r) => <Notas id={Number(r.id)} /> },
  { path: '/vestibular', perfis: ['ALUNO'], el: () => <Vestibular /> },
];

export default function App() {
  const { user, carregando } = useAuth();
  const path = usePath();

  if (carregando) return <div style={{ padding: 48 }}><Loading texto="Entrando…" /></div>;
  if (!user) return <Login />;

  let params: Record<string, string> = {};
  const rota = ROTAS.find((r) => { const m = casa(r.path, path); if (m) params = m; return !!m; });
  let conteudo: ReactNode;
  if (rota) {
    conteudo = rota.perfis.includes(user.perfil)
      ? rota.el(user.perfil, params)
      : <Mensagem icone="lock" titulo="Acesso restrito" texto="Seu perfil não tem permissão para acessar esta página." />;
  } else {
    const item = NAV[user.perfil].find((i) => i.to === path);
    conteudo = item
      ? <Mensagem icone="hourglass" titulo={`${item.label} — em desenvolvimento`} texto="Esta funcionalidade está prevista no backlog para as próximas Sprints." pb={item.pb} />
      : <Mensagem icone="search" titulo="Página não encontrada" texto="O endereço acessado não existe ou não está disponível para o seu perfil." />;
  }

  return <Shell>{conteudo}</Shell>;
}
