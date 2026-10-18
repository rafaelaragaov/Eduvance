import { Icon } from '../icons';
import { Link } from '../router';
import type { Compromisso, ItemAgenda } from '../types';
import { Badge, Card, Empty, Modal, Tone } from '../ui';

// ---------- datas (sempre no horário local, formato AAAA-MM-DD) ----------
const pad = (n: number) => String(n).padStart(2, '0');
export const iso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const hojeISO = () => iso(new Date());
export const doISO = (s: string) => new Date(`${s.slice(0, 10)}T00:00:00`);
export const somarDias = (d: Date, n: number) => { const x = new Date(d.getFullYear(), d.getMonth(), d.getDate()); x.setDate(x.getDate() + n); return x; };
export const segunda = (d: Date) => somarDias(d, -((d.getDay() + 6) % 7));
export const DIAS_SEMANA = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'];
export const DIAS_CURTOS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
export const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
/** 0 = segunda ... 6 = domingo */
export const diaDaSemana = (d: Date) => (d.getDay() + 6) % 7;
export const dataLonga = (s: string) => { const d = doISO(s); return `${DIAS_SEMANA[diaDaSemana(d)]}, ${d.getDate()} de ${MESES[d.getMonth()]!.toLowerCase()} de ${d.getFullYear()}`; };
export const dataCurta = (s: string) => { const d = doISO(s); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`; };
export const horaDe = (s: string) => s.slice(11, 16);

// ---------- tipos de item ----------
interface Info { rot: string; cls: string; tone: Tone; icone: Parameters<typeof Icon>[0]['name'] }
const INFO: Record<string, Info> = {
  AULA: { rot: 'Aula', cls: 'ag-aula', tone: 'teal', icone: 'book' },
  ATIVIDADE: { rot: 'Entrega', cls: 'ag-atv', tone: 'amber', icone: 'file' },
  PROVA: { rot: 'Prova', cls: 'ag-prova', tone: 'red', icone: 'bookmark' },
  TESTE: { rot: 'Teste', cls: 'ag-prova', tone: 'red', icone: 'bookmark' },
  TRABALHO: { rot: 'Trabalho', cls: 'ag-prova', tone: 'red', icone: 'bookmark' },
  PROJETO: { rot: 'Projeto', cls: 'ag-prova', tone: 'red', icone: 'bookmark' },
  EVENTO: { rot: 'Evento', cls: 'ag-evento', tone: 'blue', icone: 'calendar' },
  REUNIAO: { rot: 'Reunião', cls: 'ag-evento', tone: 'blue', icone: 'users' },
  CONSELHO: { rot: 'Conselho de classe', cls: 'ag-evento', tone: 'blue', icone: 'users' },
  FERIADO: { rot: 'Feriado', cls: 'ag-folga', tone: 'gray', icone: 'calendar' },
  RECESSO: { rot: 'Recesso', cls: 'ag-folga', tone: 'gray', icone: 'calendar' },
};
const FALLBACK: Info = { rot: 'Item', cls: 'ag-evento', tone: 'gray', icone: 'calendar' };
export const infoDe = (categoria: string): Info => INFO[categoria] ?? FALLBACK;
export const semAula = (i: Pick<ItemAgenda, 'categoria'>) => i.categoria === 'FERIADO' || i.categoria === 'RECESSO';

/** O item acontece no dia informado? (eventos podem durar vários dias) */
export function cobreDia(i: Pick<ItemAgenda, 'inicio' | 'fim' | 'tipo'>, dia: string): boolean {
  const ini = i.inicio.slice(0, 10);
  const fim = (i.fim ?? i.inicio).slice(0, 10);
  return i.tipo === 'EVENTO' ? ini <= dia && dia <= fim : ini === dia;
}

export function quandoItem(i: ItemAgenda): string {
  if (i.tipo === 'AULA') return `${horaDe(i.inicio)} – ${i.fim ? horaDe(i.fim) : ''}`;
  if (i.tipo === 'ATIVIDADE') return `até ${horaDe(i.inicio)}`;
  if (i.tipo === 'AVALIACAO' || i.diaInteiro) return 'Dia todo';
  return i.fim && i.fim.slice(0, 10) === i.inicio.slice(0, 10) ? `${horaDe(i.inicio)} – ${horaDe(i.fim)}` : horaDe(i.inicio);
}

const STATUS: Record<string, { rot: string; tone: Tone }> = {
  PENDENTE: { rot: 'Pendente', tone: 'amber' },
  ENTREGUE: { rot: 'Entregue', tone: 'green' },
  CORRIGIDA: { rot: 'Corrigida', tone: 'blue' },
};

export function ChipTipo({ categoria }: { categoria: string }) {
  const i = infoDe(categoria);
  return <Badge tone={i.tone}>{i.rot}</Badge>;
}

export const LEGENDA: { cat: string; rot: string }[] = [
  { cat: 'AULA', rot: 'Aulas' }, { cat: 'ATIVIDADE', rot: 'Entregas' }, { cat: 'PROVA', rot: 'Provas e trabalhos' },
  { cat: 'EVENTO', rot: 'Eventos' }, { cat: 'FERIADO', rot: 'Sem aulas' },
];

export function Legenda() {
  return (
    <ul className="ag-legenda" aria-label="Legenda">
      {LEGENDA.map((l) => <li key={l.cat}><span className={`ag-ponto ${infoDe(l.cat).cls}`} aria-hidden="true" />{l.rot}</li>)}
    </ul>
  );
}

/** Janela com os detalhes de um item da agenda e atalho para a tela do módulo correspondente. */
export function DetalheItem({ item, onClose }: { item: ItemAgenda; onClose: () => void }) {
  const info = infoDe(item.categoria);
  const dias = item.tipo === 'EVENTO' && item.fim && item.fim.slice(0, 10) !== item.inicio.slice(0, 10)
    ? `${dataLonga(item.inicio)} até ${dataLonga(item.fim)}` : dataLonga(item.inicio);
  const destino = item.tipo === 'ATIVIDADE' ? 'Abrir atividades' : item.tipo === 'AVALIACAO' ? 'Abrir calendário de provas' : item.tipo === 'EVENTO' ? 'Abrir calendário escolar' : 'Ver agenda';
  return (
    <Modal titulo={item.titulo} onClose={onClose}>
      <div className="ag-detalhe">
        <p><ChipTipo categoria={item.categoria} />{item.status && <> <Badge tone={STATUS[item.status]?.tone ?? 'gray'}>{STATUS[item.status]?.rot ?? item.status}</Badge></>}</p>
        <dl className="conta">
          <div><dt>Quando</dt><dd>{dias} · {quandoItem(item)}</dd></div>
          {item.turma && <div><dt>Turma</dt><dd>{item.turma}</dd></div>}
          {item.disciplina && item.tipo !== 'AULA' && <div><dt>Disciplina</dt><dd>{item.disciplina}</dd></div>}
          {item.professor && <div><dt>Professor(a)</dt><dd>{item.professor}</dd></div>}
          {item.sala && <div><dt>Sala</dt><dd>{item.sala}</dd></div>}
          {item.aluno && <div><dt>Aluno(a)</dt><dd>{item.aluno}</dd></div>}
          {item.bimestre && <div><dt>Bimestre</dt><dd>{item.bimestre}º</dd></div>}
          {item.nota !== undefined && item.nota !== null && <div><dt>Nota</dt><dd>{item.nota.toFixed(1)}</dd></div>}
        </dl>
        {item.descricao && <p style={{ whiteSpace: 'pre-wrap' }}>{item.descricao}</p>}
        {semAula(item) && <p className="muted">Não há aulas nem avaliações neste período.</p>}
      </div>
      <div className="modal-actions">
        <button className="btn btn-secondary" onClick={onClose}>Fechar</button>
        {item.tipo !== 'AULA' && <Link to={item.link} className="btn btn-primary" onClick={onClose}><Icon name={info.icone} size={16} />{destino}</Link>}
      </div>
    </Modal>
  );
}

/** Card dos dashboards: o que vem por aí (provas, entregas, eventos) e aviso quando hoje não há aula. */
export function ProximosCompromissos({ compromissos, semAulaHoje }: { compromissos: Compromisso[]; semAulaHoje: string | null }) {
  const hoje = hojeISO();
  const rotulo = (c: Compromisso) => {
    const dia = c.inicio.slice(0, 10);
    const d = Math.round((doISO(dia).getTime() - doISO(hoje).getTime()) / 86400000);
    return d === 0 ? 'Hoje' : d === 1 ? 'Amanhã' : d < 0 ? 'Atrasada' : dataCurta(dia);
  };
  return (
    <Card title="Próximos compromissos" action={<Link to="/agenda" className="card-link">Abrir agenda</Link>} className="proximos">
      {semAulaHoje && <div className="alert alert-blue" role="status" data-testid="sem-aula-hoje"><Icon name="calendar" size={18} /><span>Hoje não há aulas: <strong>{semAulaHoje}</strong>.</span></div>}
      <div className="list">
        {compromissos.map((c) => (
          <Link key={c.id} to={c.link} className="row row-link" data-testid="compromisso">
            <div className="row-main">
              <strong>{c.titulo}</strong>
              <small>{[c.disciplina, c.turma, c.aluno].filter(Boolean).join(' · ') || infoDe(c.categoria).rot}</small>
            </div>
            <span className="prova-lado"><ChipTipo categoria={c.categoria} /><Badge tone={rotulo(c) === 'Atrasada' ? 'red' : 'gray'}>{rotulo(c)}</Badge></span>
          </Link>
        ))}
        {!compromissos.length && <Empty>Nenhum compromisso nos próximos 14 dias.</Empty>}
      </div>
    </Card>
  );
}
