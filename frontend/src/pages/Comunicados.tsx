import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth';
import { api, ApiError } from '../api';
import { quando } from '../format';
import { Icon } from '../icons';
import type { Comunicado, PublicoComunicado, TurmaDisciplina } from '../types';
import { avisarNotificacoes, Badge, Card, Empty, ErrorBox, Field, Loading, Modal, PageHeader, useApi, useToast } from '../ui';

const PUBLICOS: { v: PublicoComunicado; r: string }[] = [
  { v: 'TODOS', r: 'Toda a comunidade escolar' },
  { v: 'ALUNOS', r: 'Somente alunos' },
  { v: 'RESPONSAVEIS', r: 'Somente responsáveis' },
  { v: 'PROFESSORES', r: 'Somente professores' },
  { v: 'TURMA', r: 'Uma turma específica' },
];

const rotuloPublico = (c: Pick<Comunicado, 'publico' | 'turma'>) =>
  c.publico === 'TURMA' ? `Turma ${c.turma ?? ''}` : PUBLICOS.find((p) => p.v === c.publico)?.r.replace('Somente ', '').replace('Toda a comunidade escolar', 'Todos') ?? c.publico;

function ComunicadoForm({ inicial, turmas, soTurma, onSalvo, onCancelar }: {
  inicial?: Comunicado; turmas: { id: number; nome: string }[]; soTurma: boolean; onSalvo: () => void; onCancelar: () => void;
}) {
  const toast = useToast();
  const [titulo, setTitulo] = useState(inicial?.titulo ?? '');
  const [mensagem, setMensagem] = useState(inicial?.mensagem ?? '');
  const [publico, setPublico] = useState<PublicoComunicado>(inicial?.publico ?? (soTurma ? 'TURMA' : 'TODOS'));
  const [idTurma, setIdTurma] = useState<number | ''>(inicial?.idTurma ?? turmas[0]?.id ?? '');
  const [erro, setErro] = useState<ApiError | null>(null);
  const [local, setLocal] = useState<Record<string, string>>({});
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    const l: Record<string, string> = {};
    if (titulo.trim().length < 3) l.titulo = 'Informe um título com ao menos 3 caracteres';
    if (mensagem.trim().length < 10) l.mensagem = 'A mensagem deve ter ao menos 10 caracteres';
    if (publico === 'TURMA' && idTurma === '') l.idTurma = 'Escolha a turma que receberá o comunicado';
    setLocal(l);
    setErro(null);
    if (Object.keys(l).length) return;
    setEnviando(true);
    try {
      if (inicial) {
        await api(`/comunicados/${inicial.id}`, { method: 'PUT', body: { titulo, mensagem } });
        toast('Comunicado atualizado.');
      } else {
        const r = await api<Comunicado>('/comunicados', { method: 'POST', body: { titulo, mensagem, publico, ...(publico === 'TURMA' ? { idTurma } : {}) } });
        toast(`Comunicado publicado! ${r.notificados ?? 0} pessoa(s) notificada(s).`);
      }
      avisarNotificacoes();
      onSalvo();
    } catch (err) {
      setErro(err as ApiError);
    } finally {
      setEnviando(false);
    }
  }

  const msg = (c: string) => local[c] ?? erro?.campo(c);
  return (
    <form className="form" onSubmit={enviar} noValidate>
      {erro && !erro.detalhes && <div className="alert alert-red" role="alert"><Icon name="alert" size={18} />{erro.message}</div>}
      <Field label="Título" error={msg('titulo')}>
        <input type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} maxLength={120} placeholder="Ex.: Reunião de pais e mestres" />
      </Field>
      <Field label="Mensagem" error={msg('mensagem')} hint={`${mensagem.length}/2000 caracteres`}>
        <textarea rows={5} value={mensagem} onChange={(e) => setMensagem(e.target.value)} maxLength={2000} placeholder="Escreva o aviso com as informações necessárias…" />
      </Field>
      <div className="form-row">
        <Field label="Quem vai receber" error={msg('publico')} hint={inicial ? 'O público não pode ser alterado depois de publicado.' : soTurma ? 'Professores publicam para suas turmas.' : undefined}>
          <select value={publico} disabled={!!inicial || soTurma} onChange={(e) => setPublico(e.target.value as PublicoComunicado)}>
            {PUBLICOS.map((p) => <option key={p.v} value={p.v}>{p.r}</option>)}
          </select>
        </Field>
        {publico === 'TURMA' && (
          <Field label="Turma" error={msg('idTurma')}>
            <select value={idTurma} disabled={!!inicial} onChange={(e) => setIdTurma(Number(e.target.value))}>
              {inicial && <option value={inicial.idTurma ?? ''}>{inicial.turma}</option>}
              {!inicial && turmas.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
            </select>
          </Field>
        )}
      </div>
      <div className="modal-actions">
        <button type="button" className="btn btn-secondary" onClick={onCancelar}>Cancelar</button>
        <button className="btn btn-primary" disabled={enviando}>{enviando ? 'Salvando…' : inicial ? 'Salvar alterações' : 'Publicar comunicado'}</button>
      </div>
    </form>
  );
}

/** Mural de comunicados: leitura para todos os perfis e publicação por coordenação, administração e professores. */
export default function Comunicados() {
  const { user } = useAuth();
  const toast = useToast();
  const podePublicar = user!.perfil !== 'ALUNO' && user!.perfil !== 'RESPONSAVEL';
  const soTurma = user!.perfil === 'PROFESSOR';
  const [somenteNaoLidos, setSomenteNaoLidos] = useState(false);
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  useEffect(() => { const t = setTimeout(() => setBuscaAplicada(busca), 250); return () => clearTimeout(t); }, [busca]);
  const qs = [somenteNaoLidos ? 'lido=nao' : '', buscaAplicada ? `busca=${encodeURIComponent(buscaAplicada)}` : ''].filter(Boolean).join('&');
  const { data: lista, erro, carregando, recarregar } = useApi<Comunicado[]>(`/comunicados${qs ? `?${qs}` : ''}`);

  const [tds, setTds] = useState<TurmaDisciplina[]>([]);
  useEffect(() => { if (podePublicar) api<TurmaDisciplina[]>('/catalogo/turma-disciplinas').then(setTds).catch(() => undefined); }, [podePublicar]);
  const turmas = useMemo(() => {
    const m = new Map<number, string>();
    tds.forEach((t) => m.set(t.idTurma, t.turma));
    return [...m].map(([id, nome]) => ({ id, nome }));
  }, [tds]);

  const [editando, setEditando] = useState<Comunicado | 'novo' | null>(null);
  const [excluindo, setExcluindo] = useState<Comunicado | null>(null);
  const [erroExcluir, setErroExcluir] = useState<string | null>(null);
  const [leitura, setLeitura] = useState<Record<number, string>>({});

  async function marcarLido(c: Comunicado) {
    try {
      await api(`/comunicados/${c.id}/lido`, { method: 'PUT' });
      recarregar();
      avisarNotificacoes();
    } catch (e) {
      toast((e as ApiError).message, 'erro');
    }
  }

  async function verLeitura(c: Comunicado) {
    try {
      const d = await api<Comunicado & { leitura: { lidos: number; destinatarios: number } }>(`/comunicados/${c.id}`);
      setLeitura((l) => ({ ...l, [c.id]: `Lido por ${d.leitura.lidos} de ${d.leitura.destinatarios} destinatário(s)` }));
    } catch (e) {
      toast((e as ApiError).message, 'erro');
    }
  }

  async function excluir() {
    if (!excluindo) return;
    try {
      await api(`/comunicados/${excluindo.id}`, { method: 'DELETE' });
      toast('Comunicado excluído.');
      setExcluindo(null);
      recarregar();
    } catch (e) {
      setErroExcluir((e as ApiError).message);
    }
  }

  const naoLidos = lista?.filter((c) => !c.lido).length ?? 0;

  return (
    <>
      <PageHeader titulo="Comunicados" subtitulo={podePublicar ? 'Publique avisos para a comunidade escolar e acompanhe quem já leu.' : 'Avisos da escola e dos professores dirigidos a você.'} />
      <div className="toolbar">
        <div className="tabs" role="tablist">
          <button role="tab" aria-selected={!somenteNaoLidos} className={`tab ${!somenteNaoLidos ? 'on' : ''}`} onClick={() => setSomenteNaoLidos(false)}>Todos</button>
          <button role="tab" aria-selected={somenteNaoLidos} className={`tab ${somenteNaoLidos ? 'on' : ''}`} onClick={() => setSomenteNaoLidos(true)}>Não lidos{!somenteNaoLidos && naoLidos > 0 ? ` (${naoLidos})` : ''}</button>
        </div>
        <input type="search" placeholder="Buscar comunicado…" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Buscar comunicado" style={{ width: 'auto', minWidth: 220 }} />
        <span className="grow" />
        {podePublicar && <button className="btn btn-primary" onClick={() => setEditando('novo')}><Icon name="plus" size={18} />Novo comunicado</button>}
      </div>

      {carregando && !lista && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {lista && !lista.length && <Card><Empty>{somenteNaoLidos ? 'Você não tem comunicados não lidos.' : buscaAplicada ? 'Nenhum comunicado encontrado para a busca.' : 'Nenhum comunicado publicado para você.'}</Empty></Card>}
      <div className="com-lista">
        {lista?.map((c) => (
          <article key={c.id} className={`card com-card ${c.lido ? '' : 'nao-lido'}`}>
            <header>
              <h2>{c.titulo}</h2>
              <span className="com-tags">
                {!c.lido && <Badge tone="red">Novo</Badge>}
                <Badge tone="teal">{rotuloPublico(c)}</Badge>
              </span>
            </header>
            <p className="com-msg">{c.mensagem}</p>
            <footer>
              <small className="muted">Publicado por {c.autor} • {quando(c.dataPublicacao)}{leitura[c.id] ? ` • ${leitura[c.id]}` : ''}</small>
              <span className="com-acoes">
                {!c.lido && <button className="btn btn-primary btn-sm" onClick={() => marcarLido(c)}><Icon name="check" size={14} />Marcar como lido</button>}
                {c.podeAlterar && (
                  <>
                    <button className="btn btn-secondary btn-sm" onClick={() => verLeitura(c)}>Ver leituras</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditando(c)}>Editar</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setErroExcluir(null); setExcluindo(c); }} aria-label={`Excluir ${c.titulo}`}><Icon name="trash" size={14} />Excluir</button>
                  </>
                )}
              </span>
            </footer>
          </article>
        ))}
      </div>

      {editando && (
        <Modal titulo={editando === 'novo' ? 'Novo comunicado' : 'Editar comunicado'} onClose={() => setEditando(null)} largo>
          <ComunicadoForm inicial={editando === 'novo' ? undefined : editando} turmas={turmas} soTurma={soTurma} onCancelar={() => setEditando(null)} onSalvo={() => { setEditando(null); recarregar(); }} />
        </Modal>
      )}
      {excluindo && (
        <Modal titulo="Excluir comunicado?" onClose={() => setExcluindo(null)}>
          <p>Você está prestes a excluir <strong>{excluindo.titulo}</strong>. Ele deixará de aparecer para todos os destinatários.</p>
          {erroExcluir && <div className="alert alert-red" role="alert"><Icon name="alert" size={18} />{erroExcluir}</div>}
          <div className="modal-actions">
            <button className="btn btn-secondary" onClick={() => setExcluindo(null)}>Cancelar</button>
            <button className="btn btn-danger" onClick={excluir}>Excluir</button>
          </div>
        </Modal>
      )}
    </>
  );
}
