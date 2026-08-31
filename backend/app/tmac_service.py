from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import floor, ceil
from statistics import median
from typing import Iterable


def _round_minutes(value: float) -> float:
    return round(max(0.0, value), 2)


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent
    lower, upper = floor(position), ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def build_tmac_report(notas: Iterable[object], inicio: datetime, fim: datetime) -> dict:
    valid, inconsistent = [], []
    for nota in notas:
        emission = getattr(nota, "data_emissao", None)
        bip = getattr(nota, "data_cadastro", None)
        if not emission or not bip:
            continue
        minutes = (bip - emission).total_seconds() / 60
        item = {
            "id": getattr(nota, "id", None),
            "numero_nf": getattr(nota, "numero_nf", None),
            "chave_acesso": getattr(nota, "chave_acesso", None),
            "emissao": emission,
            "bipe": bip,
            "minutos": round(minutes, 2),
        }
        if minutes < 0:
            inconsistent.append(item)
        else:
            valid.append(item)

    valid.sort(key=lambda item: (item["bipe"], item["id"] or 0))
    values = [item["minutos"] for item in valid]
    by_day = defaultdict(list)
    for item in valid:
        by_day[item["bipe"].date()].append(item["minutos"])
    daily = []
    for day, day_values in sorted(by_day.items()):
        daily.append({
            "data": day.isoformat(),
            "quantidade_notas": len(day_values),
            "media_minutos": _round_minutes(sum(day_values) / len(day_values)),
            "mediana_minutos": _round_minutes(float(median(day_values))),
            "p90_minutos": _round_minutes(percentile(day_values, 0.9)),
        })

    return {
        "inicio": inicio,
        "fim": fim,
        "total_notas": len(valid),
        "total_inconsistencias": len(inconsistent),
        "media_minutos": _round_minutes(sum(values) / len(values)) if values else 0.0,
        "mediana_minutos": _round_minutes(float(median(values))) if values else 0.0,
        "p90_minutos": _round_minutes(percentile(values, 0.9)),
        "maior_tempo_minutos": max(values, default=0.0),
        "dias": daily,
        "maiores_tempos": sorted(valid, key=lambda item: (item["minutos"], item["bipe"]), reverse=True)[:5],
        "inconsistencias": inconsistent,
    }
