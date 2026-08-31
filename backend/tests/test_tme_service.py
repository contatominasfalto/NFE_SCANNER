import unittest
from dataclasses import dataclass
from datetime import datetime

from app.tme_service import build_tme_report, can_access_tme


@dataclass
class Note:
    id: int
    numero_nf: str
    data_emissao: datetime | None


class TmeReportTests(unittest.TestCase):
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

    def test_access_is_exclusive_to_adm_username(self):
        self.assertTrue(can_access_tme("adm"))
        self.assertTrue(can_access_tme(" ADM "))
        self.assertFalse(can_access_tme("admin"))
        self.assertFalse(can_access_tme("viewer_user"))
        self.assertFalse(can_access_tme(None))


if __name__ == "__main__":
    unittest.main()
