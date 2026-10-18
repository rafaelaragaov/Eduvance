import { useAuth } from '../auth';
import { rotuloPerfil } from '../format';
import { Icon } from '../icons';
import { definirPrefs, Fonte, FONTES, indiceFonte, restaurarPadrao, Tema, usePrefs } from '../prefs';
import { Badge, Card, PageHeader, useToast } from '../ui';

const TEMAS: { valor: Tema; rotulo: string; texto: string }[] = [
  { valor: 'claro', rotulo: 'Claro', texto: 'Fundo claro, ideal para ambientes iluminados.' },
  { valor: 'escuro', rotulo: 'Escuro', texto: 'Fundo escuro, mais confortável à noite.' },
  { valor: 'auto', rotulo: 'Automático', texto: 'Acompanha o tema do seu aparelho.' },
];
const TAMANHO_AA = [13, 16, 19, 22, 26]; // tamanho (px) do "Aa" de cada opção, fixo para mostrar a diferença real

/** Página de Configurações (Sprint 06): tamanho do texto e tema, salvos na conta de cada usuário. */
export default function Configuracoes() {
  const { user } = useAuth();
  const toast = useToast();
  const p = usePrefs();
  const i = indiceFonte(p.fonte);
  const atual = FONTES[i]!;

  const mudar = (f: Fonte) => { void definirPrefs({ fonte: f }); };
  const restaurar = async () => { await restaurarPadrao(); toast('Preferências restauradas para o padrão.'); };

  return (
    <>
      <PageHeader titulo="Configurações" subtitulo="Ajuste a aparência do sistema para ler com mais conforto. As escolhas ficam salvas na sua conta." />

      <div className="grid-2">
        <div className="col">
          <Card title="Tamanho do texto">
            <p className="muted" style={{ margin: '-4px 0 14px' }}>Aumente ou diminua as letras de todas as telas. A mudança é imediata.</p>
            <div className="fonte-controle">
              <button className="btn btn-secondary fonte-passo" disabled={i === 0} onClick={() => mudar(FONTES[i - 1]!.valor)} aria-label="Diminuir o texto" data-testid="fonte-menos">
                <span aria-hidden="true" style={{ fontSize: 15 }}>A−</span>
              </button>
              <div className="fonte-opcoes" role="radiogroup" aria-label="Tamanho do texto">
                {FONTES.map((f, k) => (
                  <button key={f.valor} role="radio" aria-checked={p.fonte === f.valor} className={`fonte-op ${p.fonte === f.valor ? 'on' : ''}`} onClick={() => mudar(f.valor)} aria-label={`${f.rotulo} (${f.valor}%)`} title={f.rotulo} data-testid={`fonte-${f.valor}`}>
                    <span className="fonte-aa" style={{ fontSize: TAMANHO_AA[k] }} aria-hidden="true">Aa</span>
                    <small>{f.valor}%</small>
                  </button>
                ))}
              </div>
              <button className="btn btn-secondary fonte-passo" disabled={i === FONTES.length - 1} onClick={() => mudar(FONTES[i + 1]!.valor)} aria-label="Aumentar o texto" data-testid="fonte-mais">
                <span aria-hidden="true" style={{ fontSize: 20 }}>A+</span>
              </button>
            </div>
            <p className="fonte-atual" aria-live="polite">Tamanho atual: <strong data-testid="fonte-atual">{atual.rotulo} ({atual.valor}%)</strong></p>
          </Card>

          <Card title="Tema">
            <div className="tema-opcoes" role="radiogroup" aria-label="Tema">
              {TEMAS.map((t) => (
                <button key={t.valor} role="radio" aria-checked={p.tema === t.valor} className={`tema-op ${p.tema === t.valor ? 'on' : ''}`} onClick={() => { void definirPrefs({ tema: t.valor }); }} data-testid={`tema-${t.valor}`}>
                  <span className={`tema-amostra amostra-${t.valor}`} aria-hidden="true"><i /><i /><i /></span>
                  <strong>{t.rotulo}</strong>
                  <small>{t.texto}</small>
                </button>
              ))}
            </div>
          </Card>
        </div>

        <div className="col">
          <Card title="Pré-visualização">
            <div className="previa">
              <h3>Boletim — Matemática</h3>
              <p className="muted">Professor Ricardo Alves · 8º Ano B</p>
              <div className="row" style={{ marginTop: 10 }}>
                <div className="row-main"><strong>Prova B2</strong><small>Média ponderada do bimestre</small></div>
                <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}><strong style={{ fontSize: '1.125rem' }}>7,5</strong><Badge tone="green">Aprovado</Badge></span>
              </div>
              <p style={{ marginTop: 12 }}>Os comunicados, as notas e a agenda usam este mesmo tamanho. Se alguma coisa ficar difícil de ler, ajuste ao lado.</p>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button className="btn btn-primary btn-sm" type="button">Botão principal</button>
                <button className="btn btn-secondary btn-sm" type="button">Secundário</button>
              </div>
            </div>
          </Card>

          <Card title="Sua conta">
            {user && (
              <dl className="conta">
                <div><dt>Nome</dt><dd>{user.nome}</dd></div>
                <div><dt>E-mail</dt><dd>{user.email}</dd></div>
                <div><dt>Perfil</dt><dd>{rotuloPerfil[user.perfil]}</dd></div>
              </dl>
            )}
            <button className="btn btn-secondary" onClick={restaurar} data-testid="restaurar"><Icon name="repeat" size={16} />Restaurar padrões</button>
          </Card>
        </div>
      </div>
    </>
  );
}
