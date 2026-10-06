import { useEffect, useState } from 'react';
import { api } from '../api';
import type { Situacao, TurmaDisciplina } from '../types';
import type { Tone } from '../ui';

/** Turmas/disciplinas que o usuário (professor, coordenador ou admin) pode gerenciar. */
export function useTurmaDisciplinas() {
  const [tds, setTds] = useState<TurmaDisciplina[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  useEffect(() => {
    api<TurmaDisciplina[]>('/catalogo/turma-disciplinas').then(setTds).catch((e) => { setErro(e.message); setTds([]); });
  }, []);
  return { tds, erro };
}

export function TdSelect({ tds, valor, onChange, todas = false, rotulo = 'Turma e disciplina' }: {
  tds: TurmaDisciplina[]; valor: number | ''; onChange: (v: number | '') => void; todas?: boolean; rotulo?: string;
}) {
  return (
    <select value={valor} onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))} aria-label={rotulo} style={{ width: 'auto', minWidth: 220 }}>
      {todas && <option value="">Todas as turmas e disciplinas</option>}
      {tds.map((t) => <option key={t.id} value={t.id}>{t.turma} · {t.disciplina}</option>)}
    </select>
  );
}

export const situacaoTone: Record<Situacao, Tone> = {
  Aprovado: 'green',
  'Recuperação': 'amber',
  'Reprovado por faltas': 'red',
  'Sem nota': 'gray',
};

export const TIPOS = [
  { v: 'PROVA', r: 'Prova' }, { v: 'TRABALHO', r: 'Trabalho' }, { v: 'TESTE', r: 'Teste' }, { v: 'PROJETO', r: 'Projeto' },
] as const;
export const rotuloTipo = (t: string) => TIPOS.find((x) => x.v === t)?.r ?? t;

/** Converte o texto digitado (aceita vírgula) em nota; devolve mensagem de erro se inválido. */
export function lerNota(texto: string): { valor: number | null; erro?: string } {
  const t = texto.trim().replace(',', '.');
  if (t === '') return { valor: null };
  const n = Number(t);
  if (Number.isNaN(n)) return { valor: null, erro: 'Use apenas números (ex.: 7,5)' };
  if (n < 0 || n > 10) return { valor: null, erro: 'A nota deve estar entre 0 e 10' };
  return { valor: Math.round(n * 10) / 10 };
}

/** Data de hoje (ou do último dia útil) no formato AAAA-MM-DD, horário local. */
export function ultimoDiaUtil(): string {
  const d = new Date();
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() - 1);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
export const hojeISO = () => {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};
