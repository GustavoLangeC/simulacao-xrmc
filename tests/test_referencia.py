"""Confere a projeção geométrica do cenário mínimo sem executar XRMC."""
import json
import unittest
from pathlib import Path

from gerar_referencia import reference_labels


class TesteReferencia(unittest.TestCase):
    def test_cenario_minimo(self):
        manifest_path = Path(__file__).resolve().parents[1] / 'minimo_pmmaa_furo' / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        labels = reference_labels(manifest, (256, 256))
        self.assertEqual(int(labels.sum()), 2000)
        self.assertEqual(int(labels[128, 128]), 1)
        self.assertEqual(int(labels[0, 0]), 0)
        with self.assertRaises(ValueError):
            reference_labels(manifest, (128, 128))


if __name__ == '__main__':
    unittest.main()
