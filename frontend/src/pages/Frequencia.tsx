import { useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import { dataBR } from '../format';
import { Icon } from '../icons';
import { Link } from '../router';
import type { ChamadaDia } from '../types';
import { Badge, Card, Empty, ErrorBox, Field, Loading, PageHeader, useToast } from '../ui';
import { hojeISO, TdSelect, ultimoDiaUtil, useTurmaDisciplinas } from './academico';

/** Registro de frequência (chamada) por turma/disciplina e dia. */
export default function Frequencia() {
  const toast = useToast();
  const { tds, erro: erroTds } = useTurmaDisciplinas();
  const [td, setTd] = useState<number | ''>('');
  const [data, setData] = useState(ultimoDiaUtil());
  const [chamada, setChamada] = useState<ChamadaDia | null>(null);
  const [presencas, setPresencas] = useState<Record<number, boolean>>({});
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => { if (tds?.length && td === '') setTd(tds[0]!.id); }, [tds, td]);

  useEffect(() => {
    if (td === '') return;
    let vivo = true;
    setCarregando(true);
    setErro(null);
    api<ChamadaDia>(`/frequencia?idTurmaDisciplina=${td}&data=${encodeURIComponent(data)}`)
      .then((c) => {
        if (!vivo) return;
        setChamada(c);
        // sem chamada registrada, todos começam como presentes (o professor marca só as faltas)
        setPresencas(Object.fromEntries(c.alunos.map((a) => [a.idAluno, a.presente ?? true])));
      })
      .catch((e: ApiError) => { if (vivo) { setChamada(null); setErro(e.message); } })
      .finally(() => vivo && setCarregando(false));
    return () => { vivo = false; };
  }, [td, data, tick]);

  const total = chamada?.alunos.length ?? 0;
  const faltas = Object.values(presencas).filter((p) => !p).length;

  async function salvar() {
    if (!chamada) return;
    setSalvando(true);
    try {
      const registros = chamada.alunos.map((a) => ({ idAluno: a.idAluno, presente: presencas[a.idAluno] ?? true }));
      const r = await api<ChamadaDia>('/frequencia', { method: 'PUT', body: { idTurmaDisciplina: chamada.idTurmaDisciplina, data, registros } });
      toast(`Chamada de ${dataBR(data)} salva: ${r.resumo?.presentes} presente(s), ${r.resumo?.faltas} falta(s).`);
      setTick((t) => t + 1);
    } catch (e) {
      toast((e as ApiError).message, 'erro');
      setErro((e as ApiError).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <>
      <PageHeader titulo="Frequência" subtitulo="Registre a chamada do dia e acompanhe as faltas acumuladas de cada aluno." />
      {erroTds && <ErrorBox erro={erroTds} />}
      <div className="toolbar">
        {tds && td !== '' && <TdSelect tds={tds} valor={td} onChange={setTd} />}
        <Field label="Data da aula">
          <input type="date" value={data} max={hojeISO()} onChange={(e) => setData(e.target.value)} style={{ width: 'auto' }} />
        </Field>
        <span className="grow" />
        <button className="btn btn-secondary" onClick={() => setPresencas(Object.fromEntries((chamada?.alunos ?? []).map((a) => [a.idAluno, true])))} disabled={!chamada}>Marcar todos presentes</button>
        <button className="btn btn-primary" onClick={salvar} disabled={!chamada || salvando}><Icon name="check" size={18} />{salvando ? 'Salvando…' : 'Salvar chamada'}</button>
      </div>

      {tds && !tds.length && !erroTds && <Card><Empty>Você ainda não está vinculado a nenhuma turma.</Empty></Card>}
      {carregando && !chamada && <Loading />}
      {erro && <div className="alert alert-red" role="alert" style={{ marginBottom: 16 }}><Icon name="alert" size={18} />{erro}</div>}
      {chamada && (
        <Card
          title={`${chamada.turma} · ${chamada.disciplina} — ${dataBR(data)}`}
          action={<span style={{ display: 'flex', gap: 8 }}>
            <Badge tone={chamada.registrada ? 'green' : 'amber'}>{chamada.registrada ? 'Chamada registrada' : 'Ainda não registrada'}</Badge>
            <Badge tone="teal">{total - faltas} presentes</Badge>
            <Badge tone={faltas ? 'red' : 'gray'}>{faltas} faltas</Badge>
          </span>}
        >
          <div className="table-scroll">
            <table className="table bol-table">
              <thead><tr><th>Aluno</th><th className="num">Faltas acum.</th><th className="num">Frequência</th><th>Presença</th></tr></thead>
              <tbody>
                {chamada.alunos.map((a) => {
                  const p = presencas[a.idAluno] ?? true;
                  return (
                    <tr key={a.idAluno} className={`linha-aluno ${a.abaixoDoMinimo ? 'abaixo' : ''}`}>
                      <td><strong>{a.nome}</strong><br /><small className="muted">Mat. {a.matricula.slice(-4)} · <Link to={`/boletim/${a.idAluno}`} className="card-link">boletim</Link></small></td>
                      <td className="num">{a.faltas}</td>
                      <td className="num">
                        {a.frequencia === null ? '—' : `${a.frequencia.toFixed(0)}%`}
                        {a.abaixoDoMinimo && <> <Badge tone="red">abaixo de {chamada.frequenciaMinima.toFixed(0)}%</Badge></>}
                      </td>
                      <td>
                        <div className="seg" role="group" aria-label={`Presença de ${a.nome}`}>
                          <button className={`presente ${p ? 'on' : ''}`} aria-pressed={p} onClick={() => setPresencas((s) => ({ ...s, [a.idAluno]: true }))}>Presente</button>
                          <button className={`falta ${!p ? 'on' : ''}`} aria-pressed={!p} onClick={() => setPresencas((s) => ({ ...s, [a.idAluno]: false }))}>Falta</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!chamada.alunos.length && <Empty>Esta turma não possui alunos cadastrados.</Empty>}
        </Card>
      )}
    </>
  );
}
