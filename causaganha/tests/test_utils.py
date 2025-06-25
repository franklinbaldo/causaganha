import unittest
import logging
from unittest.mock import patch
import sys
from pathlib import Path

# Ensure the project root is in sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from causaganha.core.utils import normalize_lawyer_name, validate_decision

# Suppress logging output during tests unless specifically testing for it
logging.disable(logging.CRITICAL)


class TestNormalizeLawyerName(unittest.TestCase):
    def test_title_removal(self):
        self.assertEqual(normalize_lawyer_name("Dr. Foo Bar"), "foo bar")
        self.assertEqual(normalize_lawyer_name("Dra. Bar Baz"), "bar baz")
        self.assertEqual(normalize_lawyer_name("Doutor Baz Qux"), "baz qux")
        self.assertEqual(normalize_lawyer_name("DOUTORA Alice"), "alice")
        self.assertEqual(
            normalize_lawyer_name("DR.  QUX"), "qux"
        )  # Extra space after DR.
        self.assertEqual(normalize_lawyer_name("dr. foo"), "foo")  # Lowercase title

    def test_accent_normalization(self):
        self.assertEqual(
            normalize_lawyer_name("João Álves da Silva"), "joao alves da silva"
        )
        self.assertEqual(
            normalize_lawyer_name("José Élio Çइंटيا"), "jose elio cइंटيا"
        )  # Corrected expected output
        self.assertEqual(normalize_lawyer_name("Ñunez Ôliveira"), "nunez oliveira")

    def test_spacing_normalization(self):
        self.assertEqual(normalize_lawyer_name("  Pedro   Machado  "), "pedro machado")
        self.assertEqual(normalize_lawyer_name("Ana\tClara"), "ana clara")  # Tab
        self.assertEqual(normalize_lawyer_name("Silva"), "silva")  # No change

    def test_combined_normalization(self):
        self.assertEqual(
            normalize_lawyer_name("  DRA.  MARÍA ÇLARA  NÚÑEZ  "), "maria clara nunez"
        )
        self.assertEqual(
            normalize_lawyer_name("Dr. Antônio de Oliveira e Silva"),
            "antonio de oliveira e silva",
        )

    def test_oab_string_preservation(self):
        self.assertEqual(
            normalize_lawyer_name("Dr. José (OAB/SP 123)"), "jose (oab/sp 123)"
        )
        self.assertEqual(
            normalize_lawyer_name("Maria Silva OAB/RJ12345"), "maria silva oab/rj12345"
        )

    def test_advanced_title_removal(self):
        # Based on current improved logic in utils.py (iterative prefix stripping)
        self.assertEqual(normalize_lawyer_name("Dr.Dr. Foo"), "foo")
        self.assertEqual(normalize_lawyer_name("Dra.Ana Maria"), "ana maria")
        self.assertEqual(normalize_lawyer_name("Dr. Dra. Bar"), "bar")
        self.assertEqual(normalize_lawyer_name("Doutor Doutora Baz"), "baz")

    def test_empty_and_none_input(self):
        self.assertEqual(normalize_lawyer_name(""), "")
        # Assuming the function is robust to None or raises TypeError,
        # current implementation returns "" for non-str.
        self.assertEqual(normalize_lawyer_name(None), "")


class TestValidateDecision(unittest.TestCase):
    def setUp(self):
        self.valid_decision = {
            "numero_processo": "0001234-56.2023.8.22.0001",
            "partes": {
                "requerente": ["Fulano de Tal"],
                "requerido": "Cicrano Indústria Ltda",
            },
            "resultado": "procedente",
        }

    def test_valid_decision(self):
        self.assertTrue(validate_decision(self.valid_decision.copy()))

    def test_missing_numero_processo(self):
        invalid = self.valid_decision.copy()
        del invalid["numero_processo"]
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                "Validation failed: 'numero_processo' is missing or empty."
            )

    def test_bad_numero_processo_format(self):
        invalid = self.valid_decision.copy()
        invalid["numero_processo"] = "123.456"  # Too short / wrong format
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                f"Validation failed: 'numero_processo' ({invalid['numero_processo']}) does not match pattern [\\d.-]{{15,25}}."
            )

    def test_numero_processo_not_string(self):
        invalid = self.valid_decision.copy()
        invalid["numero_processo"] = 12345
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                f"Validation failed: 'numero_processo' is not a string (got {type(invalid['numero_processo'])}). Value: {invalid['numero_processo']}"
            )

    def test_missing_partes(self):
        invalid = self.valid_decision.copy()
        del invalid["partes"]
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                "Validation failed: 'partes' is missing or not a dictionary (got <class 'NoneType'>)."
            )

    def test_partes_not_dict(self):
        invalid = self.valid_decision.copy()
        invalid["partes"] = "not a dict"
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                f"Validation failed: 'partes' is missing or not a dictionary (got {type(invalid['partes'])})."
            )

    def test_missing_requerente(self):
        invalid = self.valid_decision.copy()
        invalid["partes"] = {"requerido": ["Some Recipient"]}
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                "Validation failed: 'partes.requerente' is missing or empty."
            )

    def test_empty_requerente_list(self):
        invalid = self.valid_decision.copy()
        invalid["partes"]["requerente"] = []
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                "Validation failed: 'partes.requerente' is missing or empty."
            )

    def test_empty_requerente_string(
        self,
    ):  # Assuming string is allowed based on current validate_decision
        invalid = self.valid_decision.copy()
        invalid["partes"]["requerente"] = ""
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                "Validation failed: 'partes.requerente' is missing or empty."
            )

    def test_requerente_wrong_type(self):
        invalid = self.valid_decision.copy()
        invalid["partes"]["requerente"] = 123
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                f"Validation failed: 'partes.requerente' is not a list or string (got {type(invalid['partes']['requerente'])})."
            )

    def test_missing_requerido(self):  # Similar tests for 'requerido'
        invalid = self.valid_decision.copy()
        invalid["partes"] = {"requerente": ["Some Applicant"]}
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                "Validation failed: 'partes.requerido' is missing or empty."
            )

    def test_missing_resultado(self):
        invalid = self.valid_decision.copy()
        del invalid["resultado"]
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                "Validation failed: 'resultado' is missing or empty."
            )

    def test_empty_resultado_string(self):
        invalid = self.valid_decision.copy()
        invalid["resultado"] = ""
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            mock_log.assert_called_with(
                "Validation failed: 'resultado' is missing or empty."
            )

    def test_resultado_wrong_type(self):
        invalid = self.valid_decision.copy()
        invalid["resultado"] = []  # Empty list makes 'not resultado' True
        with patch.object(
            logging.getLogger("causaganha.core.utils"), "warning"
        ) as mock_log:
            self.assertFalse(validate_decision(invalid))
            # The first check to fail for an empty list is 'missing or empty'
            mock_log.assert_called_with(
                "Validation failed: 'resultado' is missing or empty."
            )


if __name__ == "__main__":
    # Re-enable logging for running the file directly for demonstration, if desired
    # logging.disable(logging.NOTSET)
    # logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
