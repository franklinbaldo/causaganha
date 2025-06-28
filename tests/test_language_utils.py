import unittest
from src.language_utils import detect_language, translate_text, evaluate_cross_lingual


class TestLanguageUtils(unittest.TestCase):
    def test_detect_language_pt_es(self):
        self.assertEqual(detect_language("Este é um texto."), "pt")
        self.assertEqual(detect_language("Este es un texto."), "es")

    def test_translate_text_fallback(self):
        self.assertEqual(translate_text("hola", "pt"), "olá")

    def test_evaluate_cross_lingual(self):
        decs = [{"language": "pt"}, {"language": "es"}, {"language": "es"}]
        stats = evaluate_cross_lingual(decs)
        self.assertEqual(stats["pt"], 1)
        self.assertEqual(stats["es"], 2)


if __name__ == "__main__":
    unittest.main()
