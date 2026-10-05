import { FormEvent, useState } from 'react';
import { api, ApiError } from '../api';
import { diaMes, nota } from '../format';
import { Icon } from '../icons';
import type { Vestibular as V } from '../types';
import { Badge, Card, Empty, ErrorBox, Field, Loading, Modal, PageHeader, Tone, useApi, useToast } from '../ui';

const tom = (c: string): Tone => (c === 'Excelente' ? 'green' : c === 'Acima da Média' ? 'teal' : c === 'Regular' ? 'amber' : 'red');

function NovaRedacao({ onClose, onEnviada }: { onClose: () => void; onEnviada: () => void }) {
  const toast = useToast();
  const [tema, setTema] = useState('');
  const [texto, setTexto] = useState('');
  const [erro, setErro] = useState<ApiError | null>(null);
  const [enviando, setEnviando] = useState(false);
  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      await api('/vestibular/redacoes', { method: 'POST', body: { tema, texto } });
      toast('Redação enviada para correção!');
      onEnviada();
      onClose();
    } catch (err) {
      setErro(err as ApiError);
    } finally {
      setEnviando(false);
    }
  }
  return (
    <Modal titulo="Enviar nova redação" onClose={onClose} largo>
      <form className="form" onSubmit={enviar} noValidate>
        {erro && !erro.detalhes && <div className="alert alert-red">{erro.message}</div>}
        <Field label="Tema" error={erro?.campo('tema')}><input type="text" value={tema} onChange={(e) => setTema(e.target.value)} maxLength={200} /></Field>
        <Field label="Texto" error={erro?.campo('texto')} hint={`${texto.length} caracteres (mínimo 50)`}>
          <textarea value={texto} onChange={(e) => setTexto(e.target.value)} style={{ minHeight: 200 }} />
        </Field>
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" disabled={enviando}>{enviando ? 'Enviando…' : 'Enviar redação'}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Vestibular() {
  const toast = useToast();
  const [foco, setFoco] = useState('');
  const { data: d, erro, carregando, recarregar } = useApi<V>(`/vestibular${foco ? `?foco=${encodeURIComponent(foco)}` : ''}`);
  const [nova, setNova] = useState(false);
  const ano = new Date().getFullYear();

  const seletor = (
    <select className="select-pill" value={foco} onChange={(e) => setFoco(e.target.value)} aria-label="Foco do vestibular">
      <option value="">Foco: Todos</option>
      {(d?.focos ?? ['ENEM', 'Unicamp', 'FUVEST']).map((f) => <option key={f} value={f}>Foco: {f} {ano}</option>)}
    </select>
  );

  return (
    <>
      <PageHeader titulo="Área de Vestibular" subtitulo="Acesse simulados, envie redações e acompanhe seu progresso de preparação." extra={seletor} />
      {carregando && !d && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {d && (
        <div className="grid-2">
          <div className="col">
            <Card id="simulados" title="Simulados Recentes" action={<button className="link-btn" onClick={() => toast('Aplicação de novos simulados prevista para uma próxima Sprint (PB25).', 'info')}>Novo Simulado</button>}>
              <div className="list">
                {d.simulados.map((s) => (
                  <div className="simulado" key={s.id}>
                    <span className="ico"><Icon name="book" size={22} /></span>
                    <div className="info"><strong>{s.titulo}</strong><small className="muted">Realizado em {diaMes(s.data)}</small><br /><strong style={{ fontSize: 14 }}>{s.pontuacao} / 1000 pts</strong></div>
                    <Badge tone={tom(s.classificacao)}>{s.classificacao}</Badge>
                  </div>
                ))}
                {!d.simulados.length && <Empty>Nenhum simulado realizado{foco ? ` para ${foco}` : ''}.</Empty>}
              </div>
            </Card>

            <Card id="redacoes" title="Redações Enviadas" action={<button className="link-btn" onClick={() => setNova(true)}>Enviar Nova</button>}>
              <div className="list">
                {d.redacoes.map((r) => (
                  <div className="row" key={r.id}>
                    <div className="row-main">
                      <strong style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Tema: {r.tema}</strong>
                      <small>{r.status === 'CORRIGIDA' ? `Corrigida • Avaliada por Prof. ${r.avaliador?.split(' ')[0] ?? '—'}` : 'Aguardando correção'}</small>
                    </div>
                    {r.nota !== null ? <span className="nota-badge">{nota(r.nota).replace('.0', '')} / 1000</span> : <Badge tone="amber">Enviada</Badge>}
                  </div>
                ))}
                {!d.redacoes.length && <Empty>Você ainda não enviou redações.</Empty>}
              </div>
            </Card>
          </div>

          <div className="col">
            <Card id="forum" title="Fórum de Discussão Ativo">
              <div className="list">
                {d.foruns.map((f) => (
                  <div className="forum-item" key={f.id}>
                    <div><strong>{f.titulo}</strong><small className="muted">{f.disciplina ?? 'Geral'} • {f.respostas} respostas</small></div>
                    <Icon name="down" size={18} />
                  </div>
                ))}
                {!d.foruns.length && <Empty>Nenhum tópico ativo.</Empty>}
              </div>
            </Card>
            <Card id="materiais" title="Materiais Recomendados">
              <div className="materiais">
                {d.materiais.map((m) => (
                  <div className="material" key={m.id}>
                    <span className="tag">{m.tipo}</span>
                    <strong>{m.titulo}</strong>
                    <small className="muted">{m.detalhe}</small>
                  </div>
                ))}
              </div>
              {!d.materiais.length && <Empty>Nenhum material para este foco.</Empty>}
            </Card>
          </div>
        </div>
      )}
      {nova && <NovaRedacao onClose={() => setNova(false)} onEnviada={recarregar} />}
    </>
  );
}
