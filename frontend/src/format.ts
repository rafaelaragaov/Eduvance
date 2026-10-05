const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const MESES_ABREV = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'];

const pad = (n: number) => String(n).padStart(2, '0');
/** Datas vindas do servidor são horário local sem fuso (ex.: 2026-10-05T23:59:00). */
export const parse = (s: string) => new Date(s.length === 10 ? `${s}T00:00:00` : s);
const mesmoDia = (a: Date, b: Date) => a.toDateString() === b.toDateString();
const diasEntre = (a: Date, b: Date) => Math.round((new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime() - new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime()) / 864e5);

export const mesAno = (d = new Date()) => `${MESES[d.getMonth()]}, ${d.getFullYear()}`;
export const hora = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;
export const diaMes = (s: string) => { const d = parse(s); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`; };
export const diaMesCurto = (s: string) => { const d = parse(s); return { dia: pad(d.getDate()), mes: MESES_ABREV[d.getMonth()] }; };
export const dataBR = (s: string) => { const d = parse(s); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`; };

/** "Hoje, 23:59" / "Amanhã, 12:00" / "Ontem, 08:15" / "15 de Outubro". */
export function quando(s: string, comHora = true): string {
  const d = parse(s);
  const off = diasEntre(d, new Date());
  const h = hora(d);
  if (off === 0) return comHora ? `Hoje, ${h}` : 'Hoje';
  if (off === 1) return comHora ? `Amanhã, ${h}` : 'Amanhã';
  if (off === -1) return comHora ? `Ontem, ${h}` : 'Ontem';
  return `${d.getDate()} de ${MESES[d.getMonth()]}`;
}

export const moeda = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
export const nota = (n: number | null | undefined) => (n === null || n === undefined ? '—' : n.toFixed(1));

/** Valor para <input type="datetime-local"> a partir de data do servidor. */
export const paraInputDataHora = (s: string) => s.slice(0, 16);

export const iniciais = (nome: string) =>
  nome.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join('');

export const rotuloPerfil: Record<string, string> = {
  ADMIN: 'Administrador',
  COORDENADOR: 'Coordenador(a)',
  PROFESSOR: 'Professor(a)',
  ALUNO: 'Aluno(a)',
  RESPONSAVEL: 'Responsável',
};
