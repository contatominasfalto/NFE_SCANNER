"""Impede commits no fluxo incorreto de branches do NFE Scanner."""

from __future__ import annotations

import subprocess
import sys


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "Nao foi possivel consultar o Git.")
        raise SystemExit(1)
    return result.stdout.strip()


def blocked_files(branch: str, staged_files: list[str]) -> tuple[str, list[str]] | None:
    if branch == "dev_testes":
        files = [path for path in staged_files if path == "mobile" or path.startswith("mobile/")]
        if files:
            return "aplicativo Android", files
    if branch == "main":
        files = [path for path in staged_files if path == "backend" or path.startswith("backend/")]
        if files:
            return "painel/backend", files
    return None


def main() -> int:
    branch = git("branch", "--show-current")
    staged = git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    staged_files = [line.strip().replace("\\", "/") for line in staged.splitlines() if line.strip()]
    blocked = blocked_files(branch, staged_files)
    if not blocked:
        return 0

    area, files = blocked
    print()
    print("=" * 76)
    print(f"COMMIT BLOQUEADO: alteracao de {area} na branch {branch}")
    print("=" * 76)
    print()
    print("Fluxo do aplicativo Android:")
    print("  main -> producao")
    print()
    print("Fluxo do painel/backend:")
    print("  dev_testes -> homologacao -> main -> producao")
    print()
    print("Arquivos encontrados:")
    for path in files:
        print(f"  - {path}")
    print()
    if branch == "dev_testes":
        print("Mude para main antes de desenvolver ou publicar o aplicativo.")
    else:
        print("Desenvolva o painel/backend na dev_testes e promova por merge para main.")
        print("Em uma emergencia consciente, o Git permite ignorar o hook com --no-verify.")
    print()
    print("As alteracoes locais foram preservadas; somente o commit foi cancelado.")
    print()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
