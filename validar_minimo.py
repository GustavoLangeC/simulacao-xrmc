#!/usr/bin/env python3
"""Verificação específica do experimento mínimo; não é um segmentador."""
import argparse
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("imagem", type=Path)
    args = parser.parse_args()

    image = np.load(args.imagem)
    if image.shape != (256, 256):
        raise ValueError(f"Forma inesperada: {image.shape}; esperado (256, 256).")

    # A região central está inteiramente dentro do furo de 10 mm projetado.
    hole = image[112:144, 112:144]
    # Faixas acima e abaixo estão dentro da placa, longe da borda e do furo.
    pmma = np.concatenate((image[40:88, 104:152].ravel(), image[168:216, 104:152].ravel()))
    mean_hole = float(hole.mean())
    mean_pmma = float(pmma.mean())
    ratio = mean_hole / mean_pmma
    print(f"transmissao_furo={mean_hole:.6g}")
    print(f"transmissao_pmma={mean_pmma:.6g}")
    print(f"razao_furo_pmma={ratio:.6f}")
    if not mean_hole > mean_pmma:
        raise SystemExit("Falha: o furo não apresentou transmissão maior que o PMMA.")


if __name__ == "__main__":
    main()
