import { FormEvent, useState } from 'react';
import { ApiError } from '../api';
import { useAuth } from '../auth';
import { Icon } from '../icons';
import { navigate } from '../router';
import { BotaoTema } from '../theme';
import { Logo } from '../ui';

declare const __DEMO__: boolean;

const DEMO = [
  ['Aluno (Lucas)', `${new Date().getFullYear()}0001`, 'senha123'],
  ['Responsável (Maria)', 'maria@eduvance.com', 'senha123'],
  ['Professor (Ricardo)', 'ricardo@eduvance.com', 'senha123'],
  ['Coordenadora (Paula)', 'paula@eduvance.com', 'senha123'],
  ['Administrador', 'admin@eduvance.com', 'admin123'],
];

export default function Login() {
  const { login } = useAuth();
  const [ident, setIdent] = useState('');
  const [senha, setSenha] = useState('');
  const [ver, setVer] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [esqueci, setEsqueci] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    if (!ident.trim() || !senha) {
      setErro('Informe e-mail/matrícula e senha.');
      return;
    }
    setEnviando(true);
    try {
      await login(ident.trim(), senha);
      navigate('/', true);
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Erro ao entrar.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="login-page">
      <span className="login-tema"><BotaoTema className="icon-btn" /></span>
      <div className="login-wrap">
        <form className="login-card" onSubmit={enviar} noValidate>
          <Logo size={38} />
          <h1>Bem-vindo ao portal</h1>
          <p className="sub">Insira suas credenciais para continuar</p>

          <div className="form">
            {erro && <div className="alert alert-red" role="alert"><Icon name="alert" size={18} />{erro}</div>}
            {esqueci && (
              <div className="alert alert-blue" role="status">
                <Icon name="info" size={18} />Solicite a redefinição de senha à secretaria ou à coordenação da escola.
              </div>
            )}
            <label className="field">
              <span className="field-label">E-mail ou Matrícula</span>
              <span className="input-icon">
                <Icon name="user" size={18} />
                <input type="text" autoComplete="username" placeholder="exemplo@escola.com.br" value={ident} onChange={(e) => setIdent(e.target.value)} autoFocus />
              </span>
            </label>
            <label className="field">
              <span className="label-row">
                <span className="field-label">Senha</span>
                <button type="button" className="link-btn" onClick={() => setEsqueci((v) => !v)}>Esqueci minha senha</button>
              </span>
              <span className="input-icon">
                <Icon name="lock" size={18} />
                <input type={ver ? 'text' : 'password'} autoComplete="current-password" placeholder="••••••••" value={senha} onChange={(e) => setSenha(e.target.value)} />
                <button type="button" className="toggle" onClick={() => setVer((v) => !v)} aria-label={ver ? 'Ocultar senha' : 'Mostrar senha'}>
                  <Icon name={ver ? 'eye' : 'eyeOff'} size={18} />
                </button>
              </span>
            </label>
            <button className="btn btn-primary btn-block" disabled={enviando} style={{ marginTop: 6, minHeight: 46 }}>
              {enviando ? 'Entrando…' : 'Entrar no Sistema'}
            </button>
          </div>
          <p className="login-foot">Precisa de ajuda? <a href="mailto:suporte@eduvance.com">Fale com o suporte</a></p>
        </form>

        {__DEMO__ && (
          <details className="demo">
            <summary>Contas de demonstração (ambiente de desenvolvimento)</summary>
            <table>
              <tbody>
                {DEMO.map(([rotulo, i, s]) => (
                  <tr key={i}>
                    <td>{rotulo}</td>
                    <td><code>{i}</code></td>
                    <td><button type="button" onClick={() => { setIdent(i!); setSenha(s!); setErro(null); }}>Preencher</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        )}
      </div>
    </div>
  );
}
