"""Resumo do histórico do Git por autor e por dia — evidência de quem contribuiu e de como o trabalho foi distribuído.

    python tools/contribuicoes.py [--desde AAAA-MM-DD] [--ate AAAA-MM-DD]
"""
import argparse
import subprocess
import sys
from collections import Counter, defaultdict


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde")
    ap.add_argument("--ate")
    a = ap.parse_args()
    cmd = ["git", "log", "--no-merges", "--format=%an\t%ae\t%ad\t%s", "--date=format:%Y-%m-%d %H:%M"]
    if a.desde:
        cmd.append(f"--since={a.desde}")
    if a.ate:
        cmd.append(f"--until={a.ate} 23:59")
    saida = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip().splitlines()
    commits = [l.split("\t", 3) for l in saida if l]
    if not commits:
        print("Nenhum commit no período.")
        return 0
    por_autor = Counter(c[0] for c in commits)
    por_dia: dict[str, Counter] = defaultdict(Counter)
    tipos: dict[str, Counter] = defaultdict(Counter)
    for nome, _email, quando, msg in commits:
        por_dia[quando[:10]][nome] += 1
        tipos[nome][msg.split(":")[0].split("(")[0] if ":" in msg else "outro"] += 1
    print(f"{len(commits)} commits, {len(por_autor)} autor(es), {len(por_dia)} dia(s) com atividade\n")
    print(f"{'Autor':40} {'Commits':>7}  Tipos")
    for nome, n in por_autor.most_common():
        print(f"{nome:40} {n:>7}  " + ", ".join(f"{t}={q}" for t, q in tipos[nome].most_common()))
    print(f"\n{'Dia':12} " + "  ".join(f"{n[:18]:>18}" for n in por_autor))
    for dia in sorted(por_dia):
        print(f"{dia:12} " + "  ".join(f"{por_dia[dia][n]:>18}" for n in por_autor))
    if len(por_autor) == 1:
        print("\n⚠ Só há um autor no período: cada integrante deve commitar com a própria identidade (ver CONTRIBUTING.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
