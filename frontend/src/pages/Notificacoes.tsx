import { useState } from 'react';
import { api, ApiError } from '../api';
import { quando } from '../format';
import { Icon } from '../icons';
import { navigate } from '../router';
import type { Notificacao } from '../types';
import { avisarNotificacoes, Badge, Card, Empty, ErrorBox, Loading, PageHeader, Tone, useApi, useToast } from '../ui';

const tom: Record<Notificacao['tipo'], { tone: Tone; r: string }> = {
  COMUNICADO: { tone: 'blue', r: 'Comunicado' },
  OCORRENCIA: { tone: 'amber', r: 'Ocorrência' },
  FREQUENCIA: { tone: 'red', r: 'Frequência' },
};

/** Central de notificações do usuário. */
export default function Notificacoes() {
  const toast = useToast();
  const [soNaoLidas, setSoNaoLidas] = useState(false);
  const { data, erro, carregando, recarregar } = useApi<{ naoLidas: number; itens: Notificacao[] }>(`/notificacoes?limite=100${soNaoLidas ? '&naoLidas=1' : ''}`);

  async function abrir(n: Notificacao) {
    try {
      if (!n.lida) await api(`/notificacoes/${n.id}/lida`, { method: 'PUT' });
      avisarNotificacoes();
      if (n.link) navigate(n.link);
      else recarregar();
    } catch (e) {
      toast((e as ApiError).message, 'erro');
    }
  }

  async function todas() {
    try {
      await api('/notificacoes/lidas', { method: 'PUT' });
      toast('Todas as notificações foram marcadas como lidas.');
      avisarNotificacoes();
      recarregar();
    } catch (e) {
      toast((e as ApiError).message, 'erro');
    }
  }

  async function excluir(n: Notificacao) {
    try {
      await api(`/notificacoes/${n.id}`, { method: 'DELETE' });
      avisarNotificacoes();
      recarregar();
    } catch (e) {
      toast((e as ApiError).message, 'erro');
    }
  }

  return (
    <>
      <PageHeader titulo="Notificações" subtitulo="Avisos gerados pelo sistema: comunicados, ocorrências e alertas de frequência." />
      <div className="toolbar">
        <div className="tabs" role="tablist">
          <button role="tab" aria-selected={!soNaoLidas} className={`tab ${!soNaoLidas ? 'on' : ''}`} onClick={() => setSoNaoLidas(false)}>Todas</button>
          <button role="tab" aria-selected={soNaoLidas} className={`tab ${soNaoLidas ? 'on' : ''}`} onClick={() => setSoNaoLidas(true)}>Não lidas{data && data.naoLidas > 0 ? ` (${data.naoLidas})` : ''}</button>
        </div>
        <span className="grow" />
        <button className="btn btn-secondary" onClick={todas} disabled={!data?.naoLidas}><Icon name="check" size={18} />Marcar todas como lidas</button>
      </div>
      {carregando && !data && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {data && (
        <Card>
          {!data.itens.length && <Empty>{soNaoLidas ? 'Nenhuma notificação não lida.' : 'Você ainda não recebeu notificações.'}</Empty>}
          <div className="notif-lista">
            {data.itens.map((n) => (
              <div key={n.id} className={`notif ${n.lida ? '' : 'nova'}`}>
                <button className="notif-corpo" onClick={() => abrir(n)}>
                  <span className="notif-topo"><Badge tone={tom[n.tipo].tone}>{tom[n.tipo].r}</Badge><small className="muted">{quando(n.criadaEm)}</small></span>
                  <strong>{n.titulo}</strong>
                  <span>{n.mensagem}</span>
                </button>
                <button className="icon-btn ghost" aria-label="Excluir notificação" title="Excluir" onClick={() => excluir(n)}><Icon name="trash" size={16} /></button>
              </div>
            ))}
          </div>
        </Card>
      )}
    </>
  );
}
