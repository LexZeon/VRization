import ast
from pathlib import Path
import tempfile
import unittest

from vrization_host.i18n import ENGLISH, load_language, save_language, translate


class LanguageTests(unittest.TestCase):
    def test_english_default_and_persisted_language(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'language.json'
            self.assertEqual(load_language(path), 'en')
            save_language('zh', path)
            self.assertEqual(load_language(path), 'zh')
            save_language('en', path)
            self.assertEqual(load_language(path), 'en')
            path.write_text('{invalid', encoding='utf-8')
            self.assertEqual(load_language(path), 'en')

    def test_ui_catalog_has_no_missing_english_messages(self):
        source = Path(__file__).parents[1] / 'src/vrization_host/gui.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != 'tr':
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            message = node.args[0].value
            if isinstance(message, str) and any(0x4e00 <= ord(c) <= 0x9fff for c in message):
                self.assertIn(message, ENGLISH)
                self.assertFalse(any(0x4e00 <= ord(c) <= 0x9fff for c in translate(message)), message)
        self.assertEqual(translate('停止'), 'Stop')
        self.assertEqual(translate('停止', 'zh'), '停止')
        self.assertEqual(translate('电脑地址  {ip} : 8765', ip='192.0.2.5'), 'PC address  192.0.2.5 : 8765')
