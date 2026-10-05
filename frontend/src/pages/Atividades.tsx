import { useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import { quando } from '../format';
import { Icon } from '../icons';
import type { Atividade, DashResponsavel, TurmaDisciplina } from '../types';
import { Badge, Card, Empty, ErrorBox, Loading, Modal, PageHeader, useApi, useToast } from '../ui';
import { urgenciaBadge } from './DashAluno';
import AtividadeForm from './AtividadeForm';

/** CRUD de atividades. Professor/coordenador/admin gerenciam; aluno marca entrega; responsável apenas consulta. */
export default function Atividades() {
  const { user } = useAuth();
  const toast = useToast();
  const perfil = user!.perfil;
  const gerencia = perfil === 'PROFESSOR' || perfil === 'COORDENADOR' || perfil === 'ADMIN';

  const [alunoSel, setAlunoSel] = useState<number | null>(null);
  const vinc = useApi<DashResponsavel>(perfil === 'RESPONSAVEL' ? '/dashboard' : null);
  useEffect(() => { if (vinc.data?.alunos[0] && alunoSel === null) setAlunoSel(vinc.data.alunos[0].id); }, [vinc.data, alunoSel]);

  const path = perfil === 'RESPONSAVEL' ? (alunoSel ? `/atividades?alunoId=${alunoSel}` : null) : '/atividades';
  const { data: lista, erro, carregando, recarregar } = useApi<Atividade[]>(path);

  const [tds, setTds] = useState<TurmaDisciplina[]>([]);
  useEffect(() => { if (gerencia) api<TurmaDisciplina[]>('/catalogo/turma-disciplinas').then(setTds).catch(() => {}); }, [gerencia]);

  const [editando, setEditando] = useState<Atividade | 'nova' | null>(null);
  const [excluindo, setExcluindo] = useState<Atividade | null>(null);
  const [busca, setBusca] = useState('');
  const [excluindoEnvio, setExcluindoEnvio] = useState(false);

  const filtrada = (lista ?? []).filter((a) => `${a.titulo} ${a.disciplina} ${a.turma}`.toLowerCase().includes(busca.toLowerCase()));

  async function excluir() {
    if (!excluindo) return;
    setExcluindoEnvio(true);
    try {
      await api(`/atividades/${excluindo.id}`, { method: 'DELETE' });
      toast('Atividade excluída.');
      setExcluindo(null);
      recarregar();
    } catch (e) {
      toast((e as ApiError).message, 'erro');
    } finally {
      setExcluindoEnvio(false);
    }
  }

  async function alternarEntrega(a: Atividade) {
    const novo = a.statusEntrega === 'ENTREGUE' ? 'PENDENTE' : 'ENTREGUE';
    try {
      await api(`/atividades/${a.id}/entrega`, { method: 'PUT', body: { status: novo } });
      toast(novo === 'ENTREGUE' ? 'Atividade marcada como entregue.' : 'Entrega desmarcada.');
      recarregar();
    } catch (e) {
      toast((e as ApiError).message, 'erro');
    }
  }

  const subtitulo = gerencia ? 'Cadastre, consulte, atualize e exclua as atividades das turmas.' : perfil === 'ALUNO' ? 'Acompanhe prazos e marque o que já foi entregue.' : 'Acompanhe as atividades do aluno selecionado.';

  return (
    <>
      <PageHeader titulo="Atividades" subtitulo={subtitulo} />
      <div className="toolbar">
        {perfil === 'RESPONSAVEL' && vinc.data && vinc.data.alunos.length > 1 && (
          <div className="tabs">
            {vinc.data.alunos.map((a) => <button key={a.id} className={`tab ${a.id === alunoSel ? 'on' : ''}`} onClick={() => setAlunoSel(a.id)}>{a.nome}</button>)}
          </div>
        )}
        <input className="grow" type="search" placeholder="Buscar por título, disciplina ou turma…" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Buscar atividades" />
        {gerencia && <button className="btn btn-primary" onClick={() => setEditando('nova')}><Icon name="plus" size={18} />Nova atividade</button>}
      </div>

      {carregando && !lista && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {lista && (
        <Card>
          {gerencia ? (
            <div className="table-scroll">
              <table className="table">
                <thead><tr><th>Atividade</th><th>Turma / disciplina</th><th>Prazo</th><th>Entregas</th><th>Ações</th></tr></thead>
                <tbody>
                  {filtrada.map((a) => {
                    const b = urgenciaBadge[a.urgencia === 'ENTREGUE' ? 'PLANEJADA' : a.urgencia];
                    return (
                      <tr key={a.id}>
                        <td style={{ textAlign: 'left' }}><strong>{a.titulo}</strong>{a.descricao && <><br /><small className="muted">{a.descricao.slice(0, 80)}{a.descricao.length > 80 ? '…' : ''}</small></>}</td>
                        <td style={{ textAlign: 'left' }}>{a.turma}<br /><small className="muted">{a.disciplina}</small></td>
                        <td style={{ textAlign: 'left' }}>{quando(a.dataEntrega)} <Badge tone={b.tone}>{b.texto}</Badge></td>
                        <td style={{ textAlign: 'left' }}>{a.entregues ?? 0} / {a.total ?? 0}</td>
                        <td className="actions">
                          <button className="btn btn-secondary btn-sm" onClick={() => setEditando(a)}><Icon name="edit" size={14} />Editar</button>{' '}
                          <button className="btn btn-secondary btn-sm" onClick={() => setExcluindo(a)} aria-label={`Excluir ${a.titulo}`}><Icon name="trash" size={14} />Excluir</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="list">
              {filtrada.map((a) => {
                const b = urgenciaBadge[a.urgencia];
                const entregue = a.statusEntrega === 'ENTREGUE' || a.statusEntrega === 'CORRIGIDA';
                return (
                  <div className="row" key={a.id}>
                    <div className="row-main">
                      <strong>{a.titulo}</strong>
                      <small>{a.disciplina} • Prazo: {quando(a.dataEntrega)}{a.professor ? ` • Prof. ${a.professor.split(' ')[0]}` : ''}</small>
                      {a.descricao && <><br /><small className="muted">{a.descricao}</small></>}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <Badge tone={b.tone}>{b.texto}</Badge>
                      {perfil === 'ALUNO' && a.statusEntrega !== 'CORRIGIDA' && (
                        <button className={`btn btn-sm ${entregue ? 'btn-secondary' : 'btn-primary'}`} onClick={() => alternarEntrega(a)}>
                          {entregue ? 'Desfazer entrega' : 'Marcar como entregue'}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {!filtrada.length && <Empty>{busca ? 'Nenhuma atividade encontrada para a busca.' : 'Nenhuma atividade cadastrada.'}</Empty>}
        </Card>
      )}

      {editando && (
        <Modal titulo={editando === 'nova' ? 'Nova atividade' : 'Editar atividade'} onClose={() => setEditando(null)} largo>
          <AtividadeForm tds={tds} inicial={editando === 'nova' ? undefined : editando} onCancelar={() => setEditando(null)} onSalvo={() => { setEditando(null); recarregar(); }} />
        </Modal>
      )}
      {excluindo && (
        <Modal titulo="Excluir atividade?" onClose={() => setExcluindo(null)}>
          <p>Você está prestes a excluir <strong>{excluindo.titulo}</strong> ({excluindo.turma} — {excluindo.disciplina}). As entregas dos alunos também serão removidas. Esta ação não pode ser desfeita.</p>
          <div className="modal-actions">
            <button className="btn btn-secondary" onClick={() => setExcluindo(null)}>Cancelar</button>
            <button className="btn btn-danger" onClick={excluir} disabled={excluindoEnvio}>{excluindoEnvio ? 'Excluindo…' : 'Excluir'}</button>
          </div>
        </Modal>
      )}
    </>
  );
}
