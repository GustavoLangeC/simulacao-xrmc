"""Verifica arquivo, geometria e vínculo da referência analítica."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from gerar_cenario_analitico import generate


class TesteCenarioAnalitico(unittest.TestCase):
    def test_quatro_formas_e_profundidades(self):
        config = Path(__file__).resolve().parents[1] / 'cenarios/quatro_formas.json'
        with tempfile.TemporaryDirectory() as directory:
            image_path, reference_path = generate(config, Path(directory) / 'cenario')
            image = np.load(image_path, allow_pickle=False)
            with np.load(reference_path, allow_pickle=False) as archive:
                labels = archive['labels']
            metadata = json.loads(reference_path.with_suffix('.json').read_text())
            self.assertEqual(image.dtype, np.float64)
            self.assertEqual(image.shape, (256, 256))
            self.assertEqual(set(np.unique(labels)), {0, 1, 2, 3, 4})
            self.assertEqual([item['depth_mm'] for item in metadata['reference_objects']],
                             [5, 10, 15, 20])
            self.assertEqual(float(image[0, 0]), 0.0)
            with self.assertRaises(FileExistsError):
                generate(config, image_path.parent)


if __name__ == '__main__':
    unittest.main()
