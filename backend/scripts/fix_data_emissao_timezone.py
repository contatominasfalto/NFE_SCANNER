"""Corrige datas de emissao gravadas com deslocamento UTC indevido.

Uso recomendado para validar primeiro:
    python scripts/fix_data_emissao_timezone.py --chave 3126...27540

Para aplicar em uma chave especifica:
    python scripts/fix_data_emissao_timezone.py --chave 3126...27540 --apply

Para aplicar em todas as notas sem erro, use com cuidado:
    python scripts/fix_data_emissao_timezone.py --all --apply
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.models import NotaFiscal  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--chave", help="Corrige apenas uma chave de acesso.")
    group.add_argument("--all", action="store_true", help="Corrige todas as notas sem erro.")
    parser.add_argument("--hours", type=int, default=3, help="Horas a subtrair. Padrao: 3.")
    parser.add_argument("--apply", action="store_true", help="Grava a correcao no banco.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    db = SessionLocal()

    try:
        query = db.query(NotaFiscal).filter(NotaFiscal.data_emissao.isnot(None))

        if args.chave:
            query = query.filter(NotaFiscal.chave_acesso == args.chave.strip())
        else:
            query = query.filter(
                (NotaFiscal.erro_salvamento.is_(False))
                | (NotaFiscal.erro_salvamento.is_(None))
            )

        notas = query.order_by(NotaFiscal.id).all()

        if not notas:
            print("Nenhuma nota encontrada para corrigir.")
            return 0

        deslocamento = timedelta(hours=args.hours)

        for nota in notas:
            atual = nota.data_emissao
            corrigida = atual - deslocamento
            print(
                f"id={nota.id} chave={nota.chave_acesso} "
                f"{atual} -> {corrigida}"
            )
            if args.apply:
                nota.data_emissao = corrigida

        if args.apply:
            db.commit()
            print(f"Correcao aplicada em {len(notas)} nota(s).")
        else:
            print("Simulacao concluida. Use --apply para gravar.")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
