import unittest
from datetime import date, datetime
from io import BytesIO

from app.report_service import generate_throughput_pdf
from app.throughput_service import build_throughput_report


class Note:
    def __init__(self, note_id, quantity, bip, emission=None):
        self.id = note_id
        self.quantidade = quantity
        self.data_cadastro = bip
        self.data_emissao = emission or bip


class ThroughputServiceTests(unittest.TestCase):
    def setUp(self):
        self.selected = date(2026, 6, 17)
        self.notes = [
            Note(1, 10_000, datetime(2026, 6, 17, 8, 10), datetime(2026, 6, 17, 7, 5)),
            Note(2, 20_000, datetime(2026, 6, 17, 8, 55), datetime(2026, 6, 17, 9, 15)),
            Note(3, 30_000, datetime(2026, 6, 17, 10, 5), datetime(2026, 6, 17, 10, 20)),
            Note(4, 40_000, datetime(2026, 6, 18, 11, 0), datetime(2026, 7, 1, 11, 0)),
        ]

    def test_tphb_groups_from_first_to_last_bip_including_empty_hours(self):
        result = build_throughput_report(self.notes, self.selected, "data_cadastro", "TPHB", "Tonelada por Hora Bipada")
        self.assertEqual(result["total_toneladas_dia"], 60.0)
        self.assertEqual(result["total_notas_dia"], 3)
        self.assertEqual([item["rotulo"] for item in result["horas"]], ["08:00", "09:00", "10:00"])
        self.assertEqual([item["toneladas"] for item in result["horas"]], [30.0, 0.0, 30.0])
        self.assertEqual(result["media_toneladas_hora"], 20.0)
        self.assertEqual(result["media_diaria_mes"], 50.0)

    def test_tphe_uses_emission_instead_of_bip(self):
        result = build_throughput_report(self.notes, self.selected, "data_emissao", "TPHE", "Tonelada por Hora Emitida")
        self.assertEqual([item["rotulo"] for item in result["horas"]], ["07:00", "08:00", "09:00", "10:00"])
        self.assertEqual([item["toneladas"] for item in result["horas"]], [10.0, 0.0, 20.0, 30.0])
        self.assertEqual(result["media_toneladas_hora"], 15.0)
        self.assertEqual(result["meses_ano"][5]["media_toneladas_dia"], 60.0)
        self.assertEqual(result["meses_ano"][6]["media_toneladas_dia"], 40.0)

    def test_ignores_invalid_quantities_and_handles_empty_day(self):
        notes = [Note(1, None, datetime(2026, 6, 17, 8)), Note(2, -1, datetime(2026, 6, 17, 9))]
        result = build_throughput_report(notes, self.selected, "data_cadastro", "TPHB", "Tonelada por Hora Bipada")
        self.assertEqual(result["total_toneladas_dia"], 0)
        self.assertEqual(result["horas"], [])
        self.assertIsNone(result["primeiro_evento"])

    def test_generates_pdf_with_all_three_views(self):
        report = build_throughput_report(self.notes, self.selected, "data_cadastro", "TPHB", "Tonelada por Hora Bipada")
        output = BytesIO()
        generate_throughput_pdf(report, output)
        self.assertTrue(output.getvalue().startswith(b"%PDF"))
        self.assertGreater(len(output.getvalue()), 5000)


if __name__ == "__main__":
    unittest.main()
