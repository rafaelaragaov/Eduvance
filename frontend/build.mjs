// Compila o front-end com esbuild -> dist/ (servido pelo Flask em http://localhost:5000)
import { build, context } from 'esbuild';
import { cpSync, mkdirSync, rmSync } from 'node:fs';

const watch = process.argv.includes('--watch');
const demo = process.env.EDUVANCE_DEMO !== '0'; // mostra contas de demonstração na tela de login

rmSync('dist', { recursive: true, force: true });
mkdirSync('dist', { recursive: true });
cpSync('public', 'dist', { recursive: true });

const opts = {
  entryPoints: ['src/main.tsx'],
  bundle: true,
  outfile: 'dist/app.js',
  minify: !watch,
  sourcemap: watch,
  target: 'es2020',
  jsx: 'automatic',
  loader: { '.css': 'css' },
  define: {
    'process.env.NODE_ENV': watch ? '"development"' : '"production"',
    __DEMO__: JSON.stringify(demo),
  },
  logLevel: 'info',
};

if (watch) {
  const ctx = await context(opts);
  await ctx.watch();
  console.log('Observando alterações... (Ctrl+C para sair)');
} else {
  await build(opts);
}
