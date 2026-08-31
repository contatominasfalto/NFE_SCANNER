from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Iterable


def _round_minutes(value: float) -> float:
    return round(max(0.0, value), 2)


def can_access_tme(username: str | None) -> bool:
    return (username or "").strip().casefold() == "adm"


def build_tme_report(notas: Iterable[object], inicio: datetime, fim: datetime) -> dict:
    """Calcula intervalos consecutivos usando exclusivamente a data de emissao."""
    ordered = sorted(
        (nota for nota in notas if getattr(nota, "data_emissao", None) is not None),
        key=lambda nota: (nota.data_emissao, getattr(nota, "id", 0) or 0),
    )
    intervals = []
    for index, (previous, current) in enumerate(zip(ordered, ordered[1:]), start=1):
        minutes = _round_minutes(
            (current.data_emissao - previous.data_emissao).total_seconds() / 60
        )
        intervals.append(
            {
                "ordem": index,
                "inicio": previous.data_emissao,
                "fim": current.data_emissao,
                "minutos": minutes,
                "nota_anterior": {
                    "id": getattr(previous, "id", None),
                    "numero_nf": getattr(previous, "numero_nf", None),
                },
                "nota_atual": {
                    "id": getattr(current, "id", None),
                    "numero_nf": getattr(current, "numero_nf", None),
                },
            }
        )

    values = [item["minutos"] for item in intervals]
    first_emission = ordered[0].data_emissao if ordered else None
    last_emission = ordered[-1].data_emissao if ordered else None
    total_span = (
        _round_minutes((last_emission - first_emission).total_seconds() / 60)
        if first_emission and last_emission
        else 0.0
    )
    largest = sorted(
        intervals,
        key=lambda item: (item["minutos"], item["fim"]),
        reverse=True,
    )[:5]

    return {
        "inicio": inicio,
        "fim": fim,
        "total_notas": len(ordered),
        "total_intervalos": len(intervals),
        "primeira_emissao": first_emission,
        "ultima_emissao": last_emission,
        "tempo_total_minutos": total_span,
        "tme_minutos": _round_minutes(sum(values) / len(values)) if values else 0.0,
        "mediana_minutos": _round_minutes(float(median(values))) if values else 0.0,
        "maior_intervalo_minutos": max(values, default=0.0),
        "intervalos": intervals,
        "maiores_intervalos": largest,
    }
