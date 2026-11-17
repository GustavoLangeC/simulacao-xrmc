#!/usr/bin/env python3
"""Gera um fantoma analítico para testar o segmentador, sem executar XRMC.

O modelo de transmissão é ilustrativo: sinal = fundo * exp(mu * profundidade).
Não representa espectro, dose ou resposta de um equipamento clínico.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def object_mask(shape, item):
    y, x = np.ogrid[:shape[0], :shape[1]]
    cx, cy = map(float, item['center_xy_px'])
    kind = item['shape']
    if kind == 'circle':
        radius = float(item['radius_px'])
        if not np.isfinite(radius) or radius <= 0:
            raise ValueError('Raio do círculo deve ser positivo e finito.')
        mask = (x - cx)**2 + (y - cy)**2 <= radius**2
    elif kind == 'ellipse':
        rx, ry = map(float, item['radii_xy_px'])
        if not np.isfinite([rx, ry]).all() or min(rx, ry) <= 0:
            raise ValueError('Raios da elipse devem ser positivos e finitos.')
        mask = ((x - cx) / rx)**2 + ((y - cy) / ry)**2 <= 1
    elif kind == 'rectangle':
        width, height = map(float, item['size_xy_px'])
        if not np.isfinite([width, height]).all() or min(width, height) <= 0:
            raise ValueError('Dimensões do retângulo devem ser positivas e finitas.')
        mask = (abs(x - cx) <= width / 2) & (abs(y - cy) <= height / 2)
    elif kind == 'L':
        width, height = map(float, item['size_xy_px'])
        thick = float(item['thickness_px'])
        if not np.isfinite([width, height, thick]).all() or min(width, height, thick) <= 0:
            raise ValueError('Dimensões do L devem ser positivas e finitas.')
        box = (abs(x - cx) <= width / 2) & (abs(y - cy) <= height / 2)
        mask = box & ((x <= cx - width / 2 + thick) |
                      (y >= cy + height / 2 - thick))
    else:
        raise ValueError(f'Forma não suportada: {kind}')
    return np.asarray(mask, dtype=bool)


def generate(config_path, output_dir):
    config_path, output_dir = Path(config_path), Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f'Saída já contém dados: {output_dir}')
    config = json.loads(config_path.read_text(encoding='utf-8'))
    height, width = map(int, config['image_shape_yx'])
    if not (64 <= height <= 2048 and 64 <= width <= 2048):
        raise ValueError('Dimensões devem estar entre 64 e 2048 pixels.')
    y0, x0, y1, x1 = map(int, config['phantom_box_yxyx'])
    if not (2 < y0 < y1 < height - 2 and 2 < x0 < x1 < width - 2):
        raise ValueError('O fantoma deve ficar dentro da imagem.')
    mu = float(config['mu_cm_inv'])
    noise = float(config['noise_sigma'])
    base = float(config['pmma_signal'])
    gx, gy = map(float, config.get('gradient_per_pixel_xy', (0, 0)))
    if not (np.isfinite([mu, noise, base, gx, gy]).all() and
            mu > 0 and noise >= 0 and base > 0):
        raise ValueError('Parâmetros de sinal, ruído ou gradiente inválidos.')
    seed = int(config['seed'])
    image = np.zeros((height, width), dtype=np.float64)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    image[y0:y1, x0:x1] = base + gx * (xx - width / 2) + gy * (yy - height / 2)
    if np.min(image[y0:y1, x0:x1]) <= 0:
        raise ValueError('O gradiente tornou o sinal do PMMA não positivo.')
    labels = np.zeros((height, width), dtype=np.int32)
    phantom = np.zeros((height, width), dtype=bool)
    phantom[y0:y1, x0:x1] = True
    entries = []
    for index, item in enumerate(config['objects'], 1):
        depth = float(item['depth_mm'])
        if not np.isfinite(depth) or not 0 <= depth <= float(config['phantom_thickness_mm']):
            raise ValueError(f'Profundidade fora da placa no objeto {index}.')
        mask = object_mask(image.shape, item)
        if not mask.any() or np.any(mask & ~phantom) or np.any(mask & (labels > 0)):
            raise ValueError(f'Objeto {index} vazio, fora da placa ou sobreposto.')
        labels[mask] = index
        image[mask] *= np.exp(mu * depth / 10)
        entries.append({'reference_id': index, 'shape': item['shape'],
                        'depth_mm': depth, 'area_px': int(mask.sum())})
    rng = np.random.default_rng(seed)
    image[y0:y1, x0:x1] += rng.normal(0, noise, size=(y1-y0, x1-x0))
    if config.get('clip_max') is not None:
        ceiling = float(config['clip_max'])
        if not np.isfinite(ceiling) or ceiling <= 0:
            raise ValueError('clip_max deve ser positivo e finito.')
        image = np.minimum(image, ceiling)
    if not np.isfinite(image).all():
        raise ValueError('A configuração produziu pixels não finitos.')

    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / 'image.npy'
    reference_path = output_dir / 'verdade_simulada.npz'
    np.save(image_path, image)
    np.savez_compressed(reference_path, labels=labels)
    (output_dir / 'manifest.json').write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    sidecar = {
        'schema_version': 1, 'origin': 'modelo_analitico_ilustrativo',
        'image_sha256': sha256(image_path), 'config_sha256': sha256(config_path),
        'reference_objects': entries,
        'model_note': 'S=fundo*exp(mu*profundidade_cm)+ruído; sem espectro ou calibração clínica.',
    }
    reference_path.with_suffix('.json').write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2), encoding='utf-8')
    return image_path, reference_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--saida', type=Path, required=True)
    args = parser.parse_args()
    image, reference = generate(args.config, args.saida)
    print(f'Imagem: {image}\nReferência: {reference}')


if __name__ == '__main__':
    main()
