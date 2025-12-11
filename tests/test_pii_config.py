import unittest
import os
import uuid
import importlib
import sys
import logging

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestPiiConfig(unittest.TestCase):
    def test_default_uuid(self):
        # Ensure env var is unset
        old_val = os.environ.get("PII_NAMESPACE_UUID")
        if old_val:
            del os.environ["PII_NAMESPACE_UUID"]

        try:
            if 'src.pii_manager' in sys.modules:
                del sys.modules['src.pii_manager']

            import src.pii_manager
            importlib.reload(src.pii_manager)

            expected = uuid.UUID("0ab3b73f-71ac-45a0-9f08-381f7a3e62df")
            self.assertEqual(src.pii_manager.APPLICATION_NAMESPACE_UUID, expected)
        finally:
            if old_val:
                os.environ["PII_NAMESPACE_UUID"] = old_val

    def test_custom_uuid(self):
        custom_uuid = "12345678-1234-5678-1234-567812345678"

        old_val = os.environ.get("PII_NAMESPACE_UUID")
        os.environ["PII_NAMESPACE_UUID"] = custom_uuid

        try:
            if 'src.pii_manager' in sys.modules:
                del sys.modules['src.pii_manager']

            import src.pii_manager
            importlib.reload(src.pii_manager)

            self.assertEqual(src.pii_manager.APPLICATION_NAMESPACE_UUID, uuid.UUID(custom_uuid))
        finally:
             if old_val is None:
                 del os.environ["PII_NAMESPACE_UUID"]
             else:
                 os.environ["PII_NAMESPACE_UUID"] = old_val

    def test_invalid_uuid(self):
        invalid_uuid = "not-a-uuid"

        old_val = os.environ.get("PII_NAMESPACE_UUID")
        os.environ["PII_NAMESPACE_UUID"] = invalid_uuid

        try:
            if 'src.pii_manager' in sys.modules:
                del sys.modules['src.pii_manager']

            import src.pii_manager
            importlib.reload(src.pii_manager)

            # Should fall back to default
            expected = uuid.UUID("0ab3b73f-71ac-45a0-9f08-381f7a3e62df")
            self.assertEqual(src.pii_manager.APPLICATION_NAMESPACE_UUID, expected)
        finally:
             if old_val is None:
                 del os.environ["PII_NAMESPACE_UUID"]
             else:
                 os.environ["PII_NAMESPACE_UUID"] = old_val

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR) # Suppress warnings during test
    unittest.main()
