import { Icon } from '../icons';
import { Link } from '../router';
import type { Recomendacao, Recomendacoes } from '../types';
import { Badge, Card, Empty, ErrorBox, Loading, Tone, useApi } from '../ui';

const PRIORIDADE: Record<Recomendacao['prioridade'], { tone: Tone; rot: string }> = {
  ALTA: { tone: 'red', rot: 'Prioridade alta' },
  MEDIA: { tone: 'amber', rot: 'Prioridade média' },
  BAIXA: { tone: 'green', rot: 'Sugestão' },
};
const ICONE: Record<Recomendacao['tipo'], Parameters<typeof Icon>[0]['name']> = {
  REFORCO: 'book', PROVA: 'bookmark', FREQUENCIA: 'clock', ATIVIDADE: 'file', DESTAQUE: 'award',
};
const NIVEL = {
  TRANQUILO: { tone: 'green' as Tone, rot: 'Tudo em dia' },
  CUIDADO: { tone: 'amber' as Tone, rot: 'Um ponto de atenção' },
  ATENCAO: { tone: 'red' as Tone, rot: 'Vários pontos de atenção' },
};
const ORIGEM = { servico: 'Serviço de recomendação', motor: 'Motor de regras', 'motor-fallback': 'Motor de regras (serviço indisponível)' };

/** Card "Recomendações de estudo": cruza notas, faltas e a agenda de provas/entregas (serviço de recomendação). */
export default function CardRecomendacoes({ idAluno }: { idAluno?: number }) {
  const { data, erro, carregando, recarregar } = useApi<Recomendacoes>(`/recomendacoes${idAluno ? `?idAluno=${idAluno}` : ''}`);
  return (
    <Card title="Recomendações de estudo" className="recomendacoes" action={data && <Badge tone={NIVEL[data.resumo.nivel].tone}>{NIVEL[data.resumo.nivel].rot}</Badge>}>
      {carregando && !data && <Loading />}
      {erro && <ErrorBox erro={erro} onRetry={recarregar} />}
      {data && (
        <>
          <div className="list">
            {data.itens.map((r) => {
              const p = PRIORIDADE[r.prioridade];
              return (
                <Link key={`${r.tipo}-${r.titulo}`} to={r.link} className="row row-link recomendacao" data-testid="recomendacao" data-tipo={r.tipo} data-prioridade={r.prioridade}>
                  <span className={`rec-icone rec-${r.prioridade.toLowerCase()}`} aria-hidden="true"><Icon name={ICONE[r.tipo]} size={18} /></span>
                  <div className="row-main">
                    <strong>{r.titulo}</strong>
                    <small>{r.mensagem}</small>
                  </div>
                  <Badge tone={p.tone}>{p.rot}</Badge>
                </Link>
              );
            })}
            {!data.itens.length && <Empty>Nenhuma recomendação por enquanto — continue assim! 🎉</Empty>}
          </div>
          <p className="rec-origem muted" data-testid="rec-origem">Gerado por: {ORIGEM[data.origem]}</p>
        </>
      )}
    </Card>
  );
}
