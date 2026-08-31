import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import patch

from app.report_service import generate_tmac_pdf
from app.tmac_service import build_tmac_report


@dataclass
class Note:
    id: int
    numero_nf: str
    chave_acesso: str
    data_emissao: datetime | None
    data_cadastro: datetime | None


class TmacReportTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 8, 24)
        self.end = datetime(2026, 8, 30, 23, 59, 59)

    def test_calculates_note_times_daily_metrics_and_ranking(self):
        base = datetime(2026, 8, 24, 7)
        notes = [Note(index, str(100 + index), str(index) * 44, base, base + timedelta(minutes=minutes)) for index, minutes in enumerate([10, 20, 30, 40, 100, 60], start=1)]
        result = build_tmac_report(notes, self.start, self.end)
        self.assertEqual(result["total_notas"], 6)
        self.assertEqual(result["media_minutos"], 43.33)
        self.assertEqual(result["mediana_minutos"], 35.0)
        self.assertEqual(result["p90_minutos"], 80.0)
        self.assertEqual(result["maiores_tempos"][0]["numero_nf"], "105")
        self.assertEqual(result["dias"][0]["quantidade_notas"], 6)
        self.assertEqual(len(result["notas"]), 6)
        self.assertEqual([item["minutos"] for item in result["notas"]], [100.0, 60.0, 40.0, 30.0, 20.0, 10.0])

    def test_keeps_all_418_notes_for_detailed_chart_and_table(self):
        emission = datetime(2026, 8, 29, 6)
        notes = [Note(index, str(1000 + index), str(index).zfill(44), emission, emission + timedelta(minutes=index)) for index in range(1, 419)]
        result = build_tmac_report(notes, self.start, self.end)
        self.assertEqual(result["total_notas"], 418)
        self.assertEqual(len(result["notas"]), 418)
        self.assertEqual(result["notas"][0]["minutos"], 418.0)
        self.assertEqual(result["notas"][-1]["minutos"], 1.0)

    def test_excludes_negative_times_as_inconsistencies(self):
        emission = datetime(2026, 8, 24, 8)
        result = build_tmac_report([Note(1, "101", "1" * 44, emission, emission - timedelta(minutes=5))], self.start, self.end)
        self.assertEqual(result["total_notas"], 0)
        self.assertEqual(result["total_inconsistencias"], 1)

    def test_generates_tmac_pdf(self):
        emission = datetime(2026, 8, 24, 7)
        notes = [Note(index, str(1000 + index), str(index).zfill(44), emission, emission + timedelta(minutes=index)) for index in range(1, 419)]
        report = build_tmac_report(notes, self.start, self.end)
        output = BytesIO()
        with patch("app.report_service.local_now", return_value=datetime(2026, 8, 31, 12)):
            generate_tmac_pdf(report, output)
        self.assertTrue(output.getvalue().startswith(b"%PDF"))
        self.assertGreater(len(output.getvalue()), 20000)


if __name__ == "__main__":
    unittest.main()
