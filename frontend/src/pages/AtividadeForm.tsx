import { FormEvent, useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import { paraInputDataHora } from '../format';
import type { Atividade, TurmaDisciplina } from '../types';
import { Field, useToast } from '../ui';

/** Valor padrão do prazo: daqui a 7 dias às 23:59. */
export function prazoPadrao(): string {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T23:59`;
}

/** Formulário de cadastro/edição de atividade (usado no dashboard do professor e na página de atividades). */
export default function AtividadeForm({
  tds, inicial, compacto = false, onSalvo, onCancelar,
}: {
  tds: TurmaDisciplina[];
  inicial?: Atividade;
  compacto?: boolean;
  onSalvo: (a: Atividade) => void;
  onCancelar?: () => void;
}) {
  const toast = useToast();
  const [titulo, setTitulo] = useState(inicial?.titulo ?? '');
  const [descricao, setDescricao] = useState(inicial?.descricao ?? '');
  const [td, setTd] = useState<number | ''>(inicial?.idTurmaDisciplina ?? tds[0]?.id ?? '');
  // as turmas chegam de forma assíncrona: seleciona a primeira assim que carregarem
  useEffect(() => { if (td === '' && tds[0]) setTd(tds[0].id); }, [tds, td]);
  const [prazo, setPrazo] = useState(inicial ? paraInputDataHora(inicial.dataEntrega) : prazoPadrao());
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<ApiError | null>(null);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      const corpo = { titulo, descricao: descricao || null, dataEntrega: prazo, idTurmaDisciplina: td === '' ? null : td };
      const r = inicial
        ? await api<Atividade>(`/atividades/${inicial.id}`, { method: 'PUT', body: corpo })
        : await api<Atividade>('/atividades', { method: 'POST', body: corpo });
      toast(inicial ? 'Atividade atualizada.' : 'Atividade publicada!');
      if (!inicial) setTitulo('');
      if (!inicial) setDescricao('');
      onSalvo(r);
    } catch (err) {
      setErro(err as ApiError);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="form" onSubmit={enviar} noValidate>
      {erro && !erro.detalhes && <div className="alert alert-red" role="alert">{erro.message}</div>}
      <Field label={compacto ? 'Título' : 'Título da atividade'} error={erro?.campo('titulo')}>
        <input type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Título: ex. Resolução Cap. 4" maxLength={160} />
      </Field>
      {!compacto && (
        <Field label="Descrição (opcional)" error={erro?.campo('descricao')}>
          <textarea value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Orientações para os alunos" maxLength={2000} />
        </Field>
      )}
      <div className="form-row">
        <Field label="Turma / disciplina" error={erro?.campo('idTurmaDisciplina')}>
          <select value={td} onChange={(e) => setTd(Number(e.target.value))}>
            {tds.map((t) => <option key={t.id} value={t.id}>{t.turma} — {t.disciplina}</option>)}
          </select>
        </Field>
        <Field label="Prazo de entrega" error={erro?.campo('dataEntrega')}>
          <input type="datetime-local" value={prazo} onChange={(e) => setPrazo(e.target.value)} />
        </Field>
      </div>
      <div className={compacto ? '' : 'modal-actions'}>
        {onCancelar && <button type="button" className="btn btn-secondary" onClick={onCancelar}>Cancelar</button>}
        <button className={`btn btn-primary ${compacto ? 'btn-block' : ''}`} disabled={enviando || !tds.length}>
          {enviando ? 'Salvando…' : inicial ? 'Salvar alterações' : 'Publicar Atividade'}
        </button>
      </div>
    </form>
  );
}
