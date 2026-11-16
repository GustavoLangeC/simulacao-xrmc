#!/usr/bin/env python3
"""Converte a imagem float64 do XRMC e, opcionalmente, cria uma prévia PNG.

O NPY preserva os valores produzidos pelo XRMC. A normalização por percentis é
restrita à prévia visual e nunca substitui a matriz numérica.
"""
import argparse
import os
from pathlib import Path

import numpy as np


def export_preview(image: np.ndarray, destination: Path) -> None:
    """Grava uma visualização PNG, independente dos valores brutos no NPY."""
    # Evita escrever o cache do Matplotlib em ~/.config, que pode ser somente leitura.
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/matplotlib-xrmc')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    low, high = np.percentile(image, (1, 99))
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        low, high = float(image.min()), float(image.max())
    figure, axis = plt.subplots(figsize=(6, 6), constrained_layout=True)
    shown = axis.imshow(image, cmap='gray', vmin=low, vmax=high)
    axis.set_title('XRMC: transmissão simulada')
    axis.set_xlabel('x (pixel)')
    axis.set_ylabel('z (pixel)')
    colorbar = figure.colorbar(shown, ax=axis)
    colorbar.set_label('sinal simulado')
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('entrada')
    parser.add_argument('saida')
    parser.add_argument('--largura', type=int, required=True)
    parser.add_argument('--altura', type=int, required=True)
    parser.add_argument('--offset', type=int, default=60)
    parser.add_argument('--preview', type=Path,
                        help='PNG de visualização; não altera os valores do NPY.')
    args = parser.parse_args()
    raw = Path(args.entrada).read_bytes()
    expected = args.offset + args.largura * args.altura * 8
    if len(raw) != expected:
        raise ValueError(f'Tamanho inesperado: {len(raw)} bytes; esperado {expected}.')
    image = np.frombuffer(raw, dtype='<f8', offset=args.offset).reshape(args.altura, args.largura)
    if not np.isfinite(image).all():
        raise ValueError('A saída XRMC contém valores não finitos.')
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    np.save(args.saida, image)
    if args.preview:
        export_preview(image, args.preview)
    center = image[112:144, 112:144]
    surround = np.concatenate((image[40:88, 104:152].ravel(), image[168:216, 104:152].ravel()))
    print(f'Imagem: {image.shape}, mínimo={image.min():.6g}, máximo={image.max():.6g}')
    print(f'Transmissão centro={center.mean():.6g}; PMMA ao redor={surround.mean():.6g}')
    if args.preview:
        print(f'Prévia PNG: {args.preview}')


if __name__ == '__main__':
    main()
