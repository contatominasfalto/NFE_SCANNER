import unittest
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import patch

from app.tme_service import build_tme_report, can_access_tme
from app.report_service import _sample_tme_intervals, generate_tme_pdf


@dataclass
class Note:
    id: int
    numero_nf: str
    data_emissao: datetime | None


class TmeReportTests(unittest.TestCase):
    def test_pdf_chart_sampling_preserves_largest_weekly_intervals(self):
        intervals = [
            {"ordem": index, "minutos": 5.0}
            for index in range(1, 594)
        ]
        peaks = [(510, 908.1), (57, 106.0), (233, 38.0), (401, 22.0), (492, 18.2)]
        for order, minutes in peaks:
            intervals[order - 1]["minutos"] = minutes
        largest = sorted(intervals, key=lambda item: item["minutos"], reverse=True)[:5]

        sampled = _sample_tme_intervals(intervals, largest)

        sampled_orders = {item["ordem"] for item in sampled}
        self.assertTrue({order for order, _minutes in peaks}.issubset(sampled_orders))
        self.assertEqual(max(item["minutos"] for item in sampled), 908.1)
        self.assertEqual(sampled, sorted(sampled, key=lambda item: item["ordem"]))

    def test_generates_branded_tme_pdf(self):
        inicio = datetime(2026, 8, 1, 7, 0)
        fim = datetime(2026, 8, 1, 8, 0)
        report = build_tme_report(
            [Note(1, "100", inicio), Note(2, "101", fim)], inicio, fim
        )
        output = BytesIO()
        generated_at = datetime(2026, 8, 31, 12, 34)
        with patch("app.report_service.local_now", return_value=generated_at) as now:
            generate_tme_pdf(report, output)
        self.assertTrue(output.getvalue().startswith(b"%PDF"))
        self.assertGreater(len(output.getvalue()), 2000)
        self.assertGreaterEqual(now.call_count, 1)

    def setUp(self):
        self.start = datetime(2026, 8, 31, 0, 0)
        self.end = datetime(2026, 8, 31, 23, 59, 59)

    def test_calculates_consecutive_intervals_and_summary(self):
        notes = [
            Note(3, "103", datetime(2026, 8, 31, 7, 25)),
            Note(1, "101", datetime(2026, 8, 31, 7, 0)),
            Note(2, "102", datetime(2026, 8, 31, 7, 10)),
        ]
        result = build_tme_report(notes, self.start, self.end)
        self.assertEqual(result["total_notas"], 3)
        self.assertEqual(result["total_intervalos"], 2)
        self.assertEqual([item["minutos"] for item in result["intervalos"]], [10.0, 15.0])
        self.assertEqual(result["tme_minutos"], 12.5)
        self.assertEqual(result["mediana_minutos"], 12.5)
        self.assertEqual(result["maior_intervalo_minutos"], 15.0)
        self.assertEqual(result["tempo_total_minutos"], 25.0)

    def test_returns_five_largest_idle_periods(self):
        minutes = [0, 1, 3, 9, 11, 16, 23, 31]
        notes = [
            Note(index, str(100 + index), datetime(2026, 8, 31, 7, minute))
            for index, minute in enumerate(minutes, start=1)
        ]
        result = build_tme_report(notes, self.start, self.end)
        self.assertEqual(
            [item["minutos"] for item in result["maiores_intervalos"]],
            [8.0, 7.0, 6.0, 5.0, 2.0],
        )
        self.assertEqual(len(result["maiores_intervalos"]), 5)

    def test_handles_fewer_than_two_valid_notes(self):
        result = build_tme_report(
            [Note(1, "101", None), Note(2, "102", datetime(2026, 8, 31, 7, 0))],
            self.start,
            self.end,
        )
        self.assertEqual(result["total_notas"], 1)
        self.assertEqual(result["total_intervalos"], 0)
        self.assertEqual(result["tme_minutos"], 0.0)
        self.assertEqual(result["maiores_intervalos"], [])

    def test_uses_id_as_tie_breaker_for_equal_emission_time(self):
        emission = datetime(2026, 8, 31, 7, 0)
        result = build_tme_report(
            [Note(2, "102", emission), Note(1, "101", emission)],
            self.start,
            self.end,
        )
        self.assertEqual(result["intervalos"][0]["minutos"], 0.0)
        self.assertEqual(result["intervalos"][0]["nota_anterior"]["id"], 1)
        self.assertEqual(result["intervalos"][0]["nota_atual"]["id"], 2)

    def test_access_is_limited_to_authorized_usernames(self):
        self.assertTrue(can_access_tme("adm"))
        self.assertTrue(can_access_tme(" ADM "))
        self.assertTrue(can_access_tme("Mauro"))
        self.assertTrue(can_access_tme(" MAURO "))
        self.assertFalse(can_access_tme("admin"))
        self.assertFalse(can_access_tme("viewer_user"))
        self.assertFalse(can_access_tme(None))


if __name__ == "__main__":
    unittest.main()
