export type Perfil = 'ADMIN' | 'COORDENADOR' | 'PROFESSOR' | 'ALUNO' | 'RESPONSAVEL';

export interface Usuario {
  id: number;
  nome: string;
  email: string;
  perfil: Perfil;
  ativo: boolean;
  matricula: string | null;
  serie: string | null;
  dataNascimento: string | null;
  idTurma: number | null;
  turma: string | null;
  telefone: string | null;
  especialidade: string | null;
  cargo: string | null;
  responsaveis?: { idResponsavel: number; nome: string; grauParentesco: string | null }[];
  alunos?: { idAluno: number; nome: string; grauParentesco: string | null }[];
}

export type Urgencia = 'ATRASADA' | 'URGENTE' | 'PENDENTE' | 'PLANEJADA' | 'ENTREGUE';

export interface LinhaBoletim {
  idTurmaDisciplina: number;
  materia: string;
  nota: number | null;
  frequencia: number | null;
  status: 'Aprovado' | 'Recuperação' | 'Sem nota';
}

export interface Aula {
  idHorario: number;
  idTurmaDisciplina: number;
  inicio: string;
  fim: string;
  sala: string | null;
  turma: string;
  disciplina: string;
  professor: string | null;
  status: 'Concluída' | 'Em andamento' | 'Próxima';
}

export interface AtividadeResumo {
  id: number;
  titulo: string;
  dataEntrega: string;
  disciplina: string;
  urgencia: Urgencia;
}

export interface DashAluno {
  perfil: 'ALUNO';
  mediaGeral: number | null;
  classificacaoMedia: string;
  faltas: number;
  faltasStatus: string;
  atividadesPendentes: number;
  atividadesStatus: string;
  bimestre: number;
  boletim: LinhaBoletim[];
  agendaHoje: Aula[];
  atividades: AtividadeResumo[];
  comunicados: { id: number; titulo: string; mensagem: string; data: string }[];
}

export interface TurmaCard {
  id: number;
  turma: string;
  disciplina: string;
  alunos: number;
  proximaAula: string | null;
}

export interface DashProfessor {
  perfil: 'PROFESSOR';
  turmas: TurmaCard[];
  aulasHoje: Aula[];
}

export interface DashCoordenador {
  perfil: 'COORDENADOR';
  kpis: { professoresAtivos: number; ocorrenciasAbertas: number; taxaFrequencia: number | null; metaFrequencia: number };
  professores: { id: number; nome: string; disciplina: string }[];
  eventos: { id: number; titulo: string; descricao: string | null; inicio: string }[];
  horariosHoje: Aula[];
  ocorrencias: { id: number; aluno: string; turma: string | null; titulo: string; descricao: string; data: string }[];
}

export interface AlunoVinculado {
  id: number;
  nome: string;
  turma: string | null;
  serie: string | null;
  mediaGeral: number | null;
  faltas: number;
}

export interface DashResponsavel {
  perfil: 'RESPONSAVEL';
  alunos: AlunoVinculado[];
}

export interface DashAdmin {
  perfil: 'ADMIN';
  usuariosPorPerfil: Record<string, number>;
  turmas: number;
  disciplinas: number;
  atividades: number;
}

export type Dashboard = DashAluno | DashProfessor | DashCoordenador | DashResponsavel | DashAdmin;

export interface ResumoAluno {
  aluno: { id: number; nome: string };
  boletim: LinhaBoletim[];
  mediaGeral: number | null;
  faltas: number;
  mensalidades: { id: number; valor: number; vencimento: string; status: 'ABERTA' | 'PAGA' | 'ATRASADA'; formaPagamento: string | null }[];
  ocorrencias: { id: number; titulo: string; descricao: string; data: string; status: string }[];
}

export interface TurmaDisciplina {
  id: number;
  idTurma: number;
  turma: string;
  disciplina: string;
  professor: string | null;
  alunos: number;
  notasLancadas: number;
}

export interface Atividade {
  id: number;
  titulo: string;
  descricao: string | null;
  dataEntrega: string;
  idTurmaDisciplina: number;
  turma: string;
  disciplina: string;
  professor: string | null;
  urgencia: Urgencia;
  statusEntrega?: 'PENDENTE' | 'ENTREGUE' | 'CORRIGIDA';
  entregues?: number;
  total?: number;
}

export interface NotasTurma {
  avaliacao: { id: number; titulo: string; data: string; bimestre: number } | null;
  alunos: { idAluno: number; nome: string; matricula: string; valor: number | null }[];
}

export interface Vestibular {
  focos: string[];
  foco: string | null;
  simulados: { id: number; titulo: string; data: string; vestibular: string; pontuacao: number; classificacao: string }[];
  redacoes: { id: number; tema: string; status: 'ENVIADA' | 'CORRIGIDA'; nota: number | null; avaliador: string | null; enviadaEm: string }[];
  foruns: { id: number; titulo: string; disciplina: string | null; respostas: number }[];
  materiais: { id: number; titulo: string; tipo: string; detalhe: string | null; url: string | null }[];
}
