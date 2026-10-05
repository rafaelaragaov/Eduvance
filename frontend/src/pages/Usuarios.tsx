import { FormEvent, useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import { rotuloPerfil } from '../format';
import { Icon } from '../icons';
import type { Perfil, Usuario } from '../types';
import { Avatar, Badge, Card, Empty, ErrorBox, Field, Loading, Modal, PageHeader, useApi, useToast } from '../ui';

const FILTROS: { id: string; rotulo: string }[] = [
  { id: '', rotulo: 'Todos' },
  { id: 'ALUNO', rotulo: 'Alunos' },
  { id: 'RESPONSAVEL', rotulo: 'Responsáveis' },
  { id: 'PROFESSOR', rotulo: 'Professores' },
  { id: 'COORDENADOR', rotulo: 'Coordenadores' },
  { id: 'ADMIN', rotulo: 'Administradores' },
];

interface Turma { id: number; nome: string }

function UsuarioForm({ inicial, perfisPermitidos, perfilFixo, onClose, onSalvo }: {
  inicial?: Usuario; perfisPermitidos: Perfil[]; perfilFixo?: Perfil; onClose: () => void; onSalvo: () => void;
}) {
  const toast = useToast();
  const editando = !!inicial;
  const [perfil, setPerfil] = useState<Perfil>(inicial?.perfil ?? perfilFixo ?? perfisPermitidos[0]!);
  const [nome, setNome] = useState(inicial?.nome ?? '');
  const [email, setEmail] = useState(inicial?.email ?? '');
  const [senha, setSenha] = useState('');
  const [ativo, setAtivo] = useState(inicial?.ativo ?? true);
  const [matricula, setMatricula] = useState(inicial?.matricula ?? '');
  const [serie, setSerie] = useState(inicial?.serie ?? '');
  const [nasc, setNasc] = useState(inicial?.dataNascimento ?? '');
  const [idTurma, setIdTurma] = useState<number | ''>(inicial?.idTurma ?? '');
  const [telefone, setTelefone] = useState(inicial?.telefone ?? '');
  const [especialidade, setEspecialidade] = useState(inicial?.especialidade ?? '');
  const [cargo, setCargo] = useState(inicial?.cargo ?? '');
  const [resp, setResp] = useState<{ idResponsavel: number | ''; grauParentesco: string }[]>(
    inicial?.responsaveis?.map((r) => ({ idResponsavel: r.idResponsavel, grauParentesco: r.grauParentesco ?? '' })) ?? [],
  );
  const [turmas, setTurmas] = useState<Turma[]>([]);
  const [responsaveis, setResponsaveis] = useState<Usuario[]>([]);
  const [erro, setErro] = useState<ApiError | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (perfil !== 'ALUNO') return;
    api<Turma[]>('/catalogo/turmas').then(setTurmas).catch(() => {});
    api<Usuario[]>('/usuarios?perfil=RESPONSAVEL').then(setResponsaveis).catch(() => {});
  }, [perfil]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    const corpo: Record<string, unknown> = { nome, email, ativo, perfil };
    if (senha) corpo.senha = senha;
    if (perfil === 'ALUNO') {
      Object.assign(corpo, {
        matricula: matricula || undefined, serie: serie || null, dataNascimento: nasc || null, idTurma: idTurma === '' ? null : idTurma,
        responsaveis: resp.filter((r) => r.idResponsavel !== '').map((r) => ({ idResponsavel: r.idResponsavel, grauParentesco: r.grauParentesco || null })),
      });
    }
    if (perfil === 'RESPONSAVEL') corpo.telefone = telefone || null;
    if (perfil === 'PROFESSOR') corpo.especialidade = especialidade || null;
    if (perfil === 'COORDENADOR') corpo.cargo = cargo || null;
    try {
      if (editando) await api(`/usuarios/${inicial!.id}`, { method: 'PUT', body: corpo });
      else await api('/usuarios', { method: 'POST', body: corpo });
      toast(editando ? 'Usuário atualizado.' : 'Usuário cadastrado com sucesso!');
      onSalvo();
    } catch (err) {
      setErro(err as ApiError);
    } finally {
      setEnviando(false);
    }
  }

  const setR = (i: number, v: Partial<(typeof resp)[number]>) => setResp((r) => r.map((x, j) => (j === i ? { ...x, ...v } : x)));

  return (
    <Modal titulo={editando ? 'Editar usuário' : perfilFixo === 'PROFESSOR' ? 'Novo professor' : 'Novo usuário'} onClose={onClose} largo>
      <form className="form" onSubmit={enviar} noValidate>
        {erro && !erro.detalhes && <div className="alert alert-red" role="alert">{erro.message}</div>}
        <div className="form-row">
          <Field label="Perfil de acesso" error={erro?.campo('perfil')}>
            <select value={perfil} disabled={editando || !!perfilFixo} onChange={(e) => setPerfil(e.target.value as Perfil)}>
              {perfisPermitidos.map((p) => <option key={p} value={p}>{rotuloPerfil[p]}</option>)}
            </select>
          </Field>
          <Field label="Situação">
            <select value={ativo ? '1' : '0'} onChange={(e) => setAtivo(e.target.value === '1')}>
              <option value="1">Ativo</option><option value="0">Inativo (sem acesso)</option>
            </select>
          </Field>
        </div>
        <Field label="Nome completo" error={erro?.campo('nome')}><input type="text" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={120} /></Field>
        <div className="form-row">
          <Field label="E-mail" error={erro?.campo('email')}><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" /></Field>
          <Field label={editando ? 'Nova senha (opcional)' : 'Senha'} error={erro?.campo('senha')} hint="Mínimo de 6 caracteres">
            <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="new-password" />
          </Field>
        </div>

        {perfil === 'ALUNO' && (
          <>
            <div className="form-row">
              <Field label="Matrícula" error={erro?.campo('matricula')} hint="Usada pelo aluno para entrar no sistema">
                <input type="text" value={matricula} onChange={(e) => setMatricula(e.target.value)} maxLength={20} />
              </Field>
              <Field label="Data de nascimento" error={erro?.campo('dataNascimento')}><input type="date" value={nasc} onChange={(e) => setNasc(e.target.value)} /></Field>
            </div>
            <div className="form-row">
              <Field label="Turma" error={erro?.campo('idTurma')}>
                <select value={idTurma} onChange={(e) => setIdTurma(e.target.value ? Number(e.target.value) : '')}>
                  <option value="">Sem turma</option>
                  {turmas.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
                </select>
              </Field>
              <Field label="Série" error={erro?.campo('serie')}><input type="text" value={serie} onChange={(e) => setSerie(e.target.value)} placeholder="Ex.: 8º Ano" /></Field>
            </div>
            <Field label="Responsáveis (até 2)" error={erro?.campo('responsaveis')}>
              <div className="form">
                {resp.map((r, i) => (
                  <div className="form-row" key={i}>
                    <select value={r.idResponsavel} onChange={(e) => setR(i, { idResponsavel: e.target.value ? Number(e.target.value) : '' })} aria-label={`Responsável ${i + 1}`}>
                      <option value="">Selecione…</option>
                      {responsaveis.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
                    </select>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input type="text" value={r.grauParentesco} onChange={(e) => setR(i, { grauParentesco: e.target.value })} placeholder="Parentesco (Mãe, Pai…)" />
                      <button type="button" className="icon-btn" onClick={() => setResp((x) => x.filter((_, j) => j !== i))} aria-label="Remover responsável"><Icon name="x" size={16} /></button>
                    </div>
                  </div>
                ))}
                {resp.length < 2 && <button type="button" className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => setResp((x) => [...x, { idResponsavel: '', grauParentesco: '' }])}><Icon name="plus" size={14} />Vincular responsável</button>}
              </div>
            </Field>
          </>
        )}
        {perfil === 'RESPONSAVEL' && <Field label="Telefone" error={erro?.campo('telefone')}><input type="text" value={telefone} onChange={(e) => setTelefone(e.target.value)} placeholder="(81) 99999-0000" /></Field>}
        {perfil === 'PROFESSOR' && <Field label="Especialidade / disciplina" error={erro?.campo('especialidade')}><input type="text" value={especialidade} onChange={(e) => setEspecialidade(e.target.value)} placeholder="Ex.: Matemática" /></Field>}
        {perfil === 'COORDENADOR' && <Field label="Cargo" error={erro?.campo('cargo')}><input type="text" value={cargo} onChange={(e) => setCargo(e.target.value)} placeholder="Ex.: Coordenadora Pedagógica" /></Field>}

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" disabled={enviando}>{enviando ? 'Salvando…' : editando ? 'Salvar alterações' : 'Cadastrar'}</button>
        </div>
      </form>
    </Modal>
  );
}

/** Cadastro e gestão de usuários. Admin: todos os perfis. Coordenador: somente professores. */
export default function Usuarios({ somenteProfessores = false }: { somenteProfessores?: boolean }) {
  const { user } = useAuth();
  const toast = useToast();
  const [filtro, setFiltro] = useState(somenteProfessores ? 'PROFESSOR' : '');
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  useEffect(() => { const t = setTimeout(() => setBuscaAplicada(busca), 250); return () => clearTimeout(t); }, [busca]);

  const params = new URLSearchParams();
  if (filtro) params.set('perfil', filtro);
  if (buscaAplicada) params.set('q', buscaAplicada);
  const { data: lista, erro, carregando, recarregar } = useApi<Usuario[]>(`/usuarios${params.toString() ? `?${params}` : ''}`);

  const [form, setForm] = useState<Usuario | 'novo' | null>(null);
  const [excluir, setExcluir] = useState<Usuario | null>(null);
  const [excluindo, setExcluindo] = useState(false);

  const admin = user!.perfil === 'ADMIN';
  const perfisPermitidos: Perfil[] = admin ? ['ALUNO', 'RESPONSAVEL', 'PROFESSOR', 'COORDENADOR', 'ADMIN'] : ['PROFESSOR'];

  async function confirmarExclusao() {
    if (!excluir) return;
    setExcluindo(true);
    try {
      await api(`/usuarios/${excluir.id}`, { method: 'DELETE' });
      toast('Usuário excluído.');
      setExcluir(null);
      recarregar();
    } catch (e) {
      toast((e as ApiError).message, 'erro');
    } finally {
      setExcluindo(false);
    }
  }

  return (
    <>
      <PageHeader titulo={somenteProfessores ? 'Professores' : 'Usuários'} subtitulo={somenteProfessores ? 'Cadastre e gerencie o corpo docente.' : 'Cadastre e gerencie alunos, responsáveis, professores, coordenadores e administradores.'} />
      <div className="toolbar">
        {!somenteProfessores && <div className="tabs">{FILTROS.map((f) => <button key={f.id} className={`tab ${filtro === f.id ? 'on' : ''}`} onClick={() => setFiltro(f.id)}>{f.rotulo}</button>)}</div>}
        <input className="grow" type="search" placeholder="Buscar por nome, e-mail ou matrícula…" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Buscar usuários" />
        <button className="btn btn-primary" onClick={() => setForm('novo')}><Icon name="plus" size={18} />{somenteProfessores ? 'Novo professor' : 'Novo usuário'}</button>
      </div>

      {carregando && !lista && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {lista && (
        <Card>
          <div className="table-scroll">
            <table className="table">
              <thead><tr><th>Nome</th><th>Acesso</th><th>Perfil</th><th>Detalhes</th><th>Situação</th><th>Ações</th></tr></thead>
              <tbody>
                {lista.map((u) => (
                  <tr key={u.id}>
                    <td style={{ textAlign: 'left' }}><div className="person"><Avatar nome={u.nome} size={34} /><strong>{u.nome}</strong></div></td>
                    <td style={{ textAlign: 'left' }}>{u.email}{u.matricula && <><br /><small className="muted">Matrícula {u.matricula}</small></>}</td>
                    <td style={{ textAlign: 'left' }}><Badge tone="teal">{rotuloPerfil[u.perfil]}</Badge></td>
                    <td style={{ textAlign: 'left' }} className="muted">{u.turma ?? u.especialidade ?? u.cargo ?? u.telefone ?? '—'}</td>
                    <td style={{ textAlign: 'left' }}><Badge tone={u.ativo ? 'green' : 'gray'}>{u.ativo ? 'Ativo' : 'Inativo'}</Badge></td>
                    <td className="actions">
                      <button className="btn btn-secondary btn-sm" onClick={() => setForm(u)}><Icon name="edit" size={14} />Editar</button>{' '}
                      <button className="btn btn-secondary btn-sm" disabled={u.id === user!.id} onClick={() => setExcluir(u)} aria-label={`Excluir ${u.nome}`}><Icon name="trash" size={14} />Excluir</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!lista.length && <Empty>Nenhum usuário encontrado.</Empty>}
          {lista.length >= 500 && <p className="muted" style={{ textAlign: 'center' }}>Mostrando os primeiros 500 resultados. Refine a busca.</p>}
        </Card>
      )}

      {form && <UsuarioForm inicial={form === 'novo' ? undefined : form} perfisPermitidos={perfisPermitidos} perfilFixo={somenteProfessores ? 'PROFESSOR' : undefined} onClose={() => setForm(null)} onSalvo={() => { setForm(null); recarregar(); }} />}
      {excluir && (
        <Modal titulo="Excluir usuário?" onClose={() => setExcluir(null)}>
          <p>Você está prestes a excluir <strong>{excluir.nome}</strong> ({rotuloPerfil[excluir.perfil]}). Notas, frequência e demais registros vinculados também serão removidos. Para apenas bloquear o acesso, prefira marcar como <em>Inativo</em>.</p>
          <div className="modal-actions">
            <button className="btn btn-secondary" onClick={() => setExcluir(null)}>Cancelar</button>
            <button className="btn btn-danger" onClick={confirmarExclusao} disabled={excluindo}>{excluindo ? 'Excluindo…' : 'Excluir'}</button>
          </div>
        </Modal>
      )}
    </>
  );
}
