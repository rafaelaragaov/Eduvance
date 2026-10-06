import { ReactNode, useState } from 'react';
import { useAuth } from './auth';
import { rotuloPerfil } from './format';
import { Icon, IconName } from './icons';
import { Link, navigate, usePath } from './router';
import { Avatar, Logo } from './ui';
import type { Perfil } from './types';

export interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  /** Funcionalidade prevista para sprints futuras (código do backlog). */
  pb?: string;
}

export const NAV: Record<Perfil, NavItem[]> = {
  ALUNO: [
    { to: '/', label: 'Dashboard', icon: 'grid' },
    { to: '/boletim', label: 'Boletim', icon: 'book' },
    { to: '/agenda', label: 'Agenda', icon: 'calendar', pb: 'PB13' },
    { to: '/atividades', label: 'Atividades', icon: 'file' },
    { to: '/provas', label: 'Provas', icon: 'bookmark', pb: 'PB16' },
    { to: '/comunicados', label: 'Comunicados', icon: 'message', pb: 'PB18' },
    { to: '/vestibular', label: 'Vestibular', icon: 'award' },
  ],
  PROFESSOR: [
    { to: '/', label: 'Dashboard', icon: 'grid' },
    { to: '/turmas', label: 'Minhas Turmas', icon: 'users', pb: 'PB07' },
    { to: '/avaliacoes', label: 'Avaliações', icon: 'bookmark' },
    { to: '/notas', label: 'Lançar Notas', icon: 'edit' },
    { to: '/frequencia', label: 'Frequência', icon: 'checkCircle' },
    { to: '/atividades', label: 'Atividades', icon: 'file' },
    { to: '/boletim', label: 'Boletins', icon: 'book' },
    { to: '/comunicados', label: 'Comunicados', icon: 'message', pb: 'PB18' },
    { to: '/ocorrencias', label: 'Ocorrências', icon: 'alert', pb: 'PB19' },
  ],
  COORDENADOR: [
    { to: '/', label: 'Dashboard', icon: 'grid' },
    { to: '/professores', label: 'Professores', icon: 'users' },
    { to: '/agenda', label: 'Agenda Escolar', icon: 'calendar', pb: 'PB13' },
    { to: '/avaliacoes', label: 'Avaliações', icon: 'bookmark' },
    { to: '/notas', label: 'Notas', icon: 'file' },
    { to: '/frequencia', label: 'Frequência', icon: 'checkCircle' },
    { to: '/boletim', label: 'Boletins', icon: 'book' },
    { to: '/atividades', label: 'Atividades', icon: 'edit' },
    { to: '/ocorrencias', label: 'Ocorrências', icon: 'alert', pb: 'PB19' },
    { to: '/horarios', label: 'Horários', icon: 'clock', pb: 'PB22' },
  ],
  RESPONSAVEL: [
    { to: '/', label: 'Dashboard', icon: 'grid' },
    { to: '/alunos', label: 'Meus Alunos', icon: 'users', pb: 'PB09' },
    { to: '/mensalidades', label: 'Mensalidade', icon: 'card', pb: 'PB20' },
    { to: '/boletim', label: 'Boletim', icon: 'book' },
    { to: '/atividades', label: 'Atividades', icon: 'file' },
    { to: '/ocorrencias', label: 'Ocorrências', icon: 'alert', pb: 'PB19' },
    { to: '/comunicados', label: 'Comunicados', icon: 'message', pb: 'PB18' },
    { to: '/calendario', label: 'Calendário', icon: 'calendar', pb: 'PB17' },
  ],
  ADMIN: [
    { to: '/', label: 'Dashboard', icon: 'grid' },
    { to: '/usuarios', label: 'Usuários', icon: 'users' },
    { to: '/atividades', label: 'Atividades', icon: 'file' },
    { to: '/avaliacoes', label: 'Avaliações', icon: 'bookmark' },
    { to: '/notas', label: 'Notas', icon: 'edit' },
    { to: '/frequencia', label: 'Frequência', icon: 'checkCircle' },
    { to: '/boletim', label: 'Boletins', icon: 'book' },
  ],
};

/** Menu exibido dentro da Área de Vestibular (conforme protótipo). */
const NAV_VESTIBULAR: (NavItem & { ancora?: string })[] = [
  { to: '/', label: 'Dashboard', icon: 'grid' },
  { to: '/vestibular', label: 'Simulados', icon: 'bookmark', ancora: 'simulados' },
  { to: '/vestibular', label: 'Redações', icon: 'file', ancora: 'redacoes' },
  { to: '/vestibular', label: 'Fórum', icon: 'message', ancora: 'forum' },
  { to: '/vestibular', label: 'Materiais', icon: 'book', ancora: 'materiais' },
  { to: '/vestibular/desempenho', label: 'Meu Desempenho', icon: 'award', pb: 'PB30' },
];

function ativo(path: string, to: string) {
  return to === '/' ? path === '/' : path === to || path.startsWith(to + '/');
}

function irPara(to: string, ancora: string | undefined, path: string) {
  if (path !== to) navigate(to);
  if (ancora) setTimeout(() => document.getElementById(ancora)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), path !== to ? 80 : 0);
}

export function Shell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const path = usePath();
  const [maisAberto, setMaisAberto] = useState(false);
  if (!user) return null;

  const naVestibular = user.perfil === 'ALUNO' && path.startsWith('/vestibular');
  const itens: (NavItem & { ancora?: string })[] = naVestibular ? NAV_VESTIBULAR : NAV[user.perfil];
  const principais = itens.slice(0, 4);
  const resto = itens.slice(4);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-top"><Logo /></div>
        <nav aria-label="Navegação principal">
          {itens.map((i) => {
            const on = i.ancora ? i.ancora === 'simulados' : ativo(path, i.to);
            return (
              <Link key={i.label} to={i.to} className={`nav-item ${on ? 'on' : ''}`}
                onClick={(e) => { if (i.ancora) { e.preventDefault(); irPara(i.to, i.ancora, path); } }}>
                <Icon name={i.icon} />{i.label}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-user">
          <Avatar nome={user.nome} />
          <div className="who">
            <strong>{user.nome}</strong>
            <span>{user.perfil === 'ALUNO' ? `Aluno${user.turma ? ` - ${user.turma}` : ''}` : user.perfil === 'PROFESSOR' ? `Docente${user.especialidade ? ` - ${user.especialidade}` : ''}` : user.cargo ?? rotuloPerfil[user.perfil]}</span>
          </div>
          <button className="icon-btn ghost" onClick={logout} aria-label="Sair" title="Sair"><Icon name="logout" size={18} /></button>
        </div>
      </aside>

      <div className="main-col">
        <div className="mobile-top">
          <Logo size={30} />
          <button className="icon-btn" onClick={() => setMaisAberto(true)} aria-label="Menu"><Icon name="grid" size={18} /></button>
        </div>
        <main className="main">{children}</main>
      </div>

      <nav className="bottom-nav" aria-label="Navegação">
        {principais.map((i) => (
          <Link key={i.label} to={i.to} className={ativo(path, i.to) ? 'on' : ''}>
            <Icon name={i.icon} size={22} /><span>{i.to === '/' ? 'Home' : i.label}</span>
          </Link>
        ))}
        <button onClick={() => setMaisAberto(true)}><Icon name="more" size={22} /><span>Mais</span></button>
      </nav>

      {maisAberto && (
        <div className="sheet-backdrop" onClick={() => setMaisAberto(false)}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-user"><Avatar nome={user.nome} /><div><strong>{user.nome}</strong><span>{rotuloPerfil[user.perfil]}</span></div></div>
            {resto.map((i) => (
              <Link key={i.label} to={i.to} className="nav-item" onClick={() => setMaisAberto(false)}><Icon name={i.icon} />{i.label}</Link>
            ))}
            <button className="nav-item" onClick={logout}><Icon name="logout" />Sair</button>
          </div>
        </div>
      )}
    </div>
  );
}
