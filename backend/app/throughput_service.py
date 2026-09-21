from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable


def _round_ton(value: float) -> float:
    return round(max(0.0, value), 3)


def build_throughput_report(
    notas: Iterable[object],
    selected_date: date,
    timestamp_field: str,
    code: str,
    title: str,
) -> dict:
    """Agrupa toneladas por hora e produz comparativos mensal e anual."""
    valid = []
    for nota in notas:
        timestamp = getattr(nota, timestamp_field, None)
        quantity = getattr(nota, "quantidade", None)
        try:
            quantity_kg = float(quantity)
        except (TypeError, ValueError):
            continue
        if timestamp is None or quantity_kg < 0:
            continue
        valid.append((timestamp, quantity_kg / 1000, getattr(nota, "id", 0) or 0))

    valid.sort(key=lambda item: (item[0], item[2]))
    by_day = defaultdict(float)
    by_hour = defaultdict(float)
    notes_by_hour = defaultdict(int)
    for timestamp, tons, _note_id in valid:
        by_day[timestamp.date()] += tons
        if timestamp.date() == selected_date:
            hour = timestamp.replace(minute=0, second=0, microsecond=0)
            by_hour[hour] += tons
            notes_by_hour[hour] += 1

    selected_items = [item for item in valid if item[0].date() == selected_date]
    first_timestamp = selected_items[0][0] if selected_items else None
    last_timestamp = selected_items[-1][0] if selected_items else None
    hours = []
    if first_timestamp and last_timestamp:
        cursor = first_timestamp.replace(minute=0, second=0, microsecond=0)
        final_hour = last_timestamp.replace(minute=0, second=0, microsecond=0)
        while cursor <= final_hour:
            hours.append({
                "hora": cursor,
                "rotulo": cursor.strftime("%H:00"),
                "toneladas": _round_ton(by_hour[cursor]),
                "quantidade_notas": notes_by_hour[cursor],
            })
            cursor += timedelta(hours=1)

    total_day = _round_ton(sum(item[1] for item in selected_items))
    active_hours = len(hours)
    days_in_month = monthrange(selected_date.year, selected_date.month)[1]
    month_days = []
    active_day_values = []
    for day_number in range(1, days_in_month + 1):
        current = date(selected_date.year, selected_date.month, day_number)
        tons = _round_ton(by_day[current])
        month_days.append({"data": current.isoformat(), "dia": day_number, "toneladas": tons})
        if tons > 0:
            active_day_values.append(tons)
    month_daily_average = _round_ton(
        sum(active_day_values) / len(active_day_values) if active_day_values else 0
    )

    months = []
    for month in range(1, 13):
        values = [
            _round_ton(total)
            for current, total in by_day.items()
            if current.year == selected_date.year and current.month == month and total > 0
        ]
        months.append({
            "mes": month,
            "media_toneladas_dia": _round_ton(sum(values) / len(values) if values else 0),
            "dias_com_movimento": len(values),
            "total_toneladas": _round_ton(sum(values)),
        })

    peak = max(hours, key=lambda item: item["toneladas"], default=None)
    return {
        "codigo": code,
        "titulo": title,
        "campo_referencia": timestamp_field,
        "data": selected_date.isoformat(),
        "ano": selected_date.year,
        "mes": selected_date.month,
        "total_toneladas_dia": total_day,
        "total_notas_dia": len(selected_items),
        "media_toneladas_hora": _round_ton(total_day / active_hours if active_hours else 0),
        "pico_toneladas_hora": peak["toneladas"] if peak else 0,
        "hora_pico": peak["rotulo"] if peak else None,
        "primeiro_evento": first_timestamp,
        "ultimo_evento": last_timestamp,
        "horas_analisadas": active_hours,
        "horas": hours,
        "media_diaria_mes": month_daily_average,
        "dias_com_movimento_mes": len(active_day_values),
        "dias_mes": month_days,
        "meses_ano": months,
    }
