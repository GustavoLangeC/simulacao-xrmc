#!/usr/bin/env python3
"""Gera a referência geométrica do cenário XRMC mínimo após a simulação.

Esta máscara é verdade de referência do modelo ideal de raios centrais, não
uma entrada do detector nem uma anotação manual de pixels de borda.
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


def reference_labels(manifest, shape):
    phantom = manifest['phantom']
    detector = manifest['detector']
    if phantom['hole_type'] != 'through':
        raise ValueError('Este gerador suporta apenas a perfuração passante do cenário mínimo.')
    width, height = map(int, detector['pixels'])
    if shape != (height, width):
        raise ValueError(f'Imagem {shape} não coincide com detector {(height, width)}.')
    pixel_x, pixel_z = map(float, detector['pixel_size_cm'])
    source_x, source_z = map(float, manifest['source_center_xz_cm'])
    hole_x, hole_z = map(float, phantom['hole_center_xz_cm'])
    distance = float(manifest['source_detector_distance_cm'])
    near = float(phantom['near_face_distance_to_detector_cm'])
    far = near + float(phantom['thickness_cm'])
    radius = float(phantom['hole_diameter_cm']) / 2
    if not (pixel_x > 0 and pixel_z > 0 and radius > 0 and 0 < near < far < distance):
        raise ValueError('Geometria incompleta ou incompatível com a projeção.')

    z, x = np.mgrid[:height, :width]
    x_detector = (x - (width - 1) / 2) * pixel_x
    z_detector = (z - (height - 1) / 2) * pixel_z
    inside = np.ones(shape, dtype=bool)
    for face_distance in (near, far):
        factor = (distance - face_distance) / distance
        x_face = source_x + (x_detector - source_x) * factor
        z_face = source_z + (z_detector - source_z) * factor
        inside &= (x_face - hole_x)**2 + (z_face - hole_z)**2 <= radius**2
    return inside.astype(np.int32)


def generate(manifest_path, image_path, output_path):
    manifest_path, image_path, output_path = map(Path, (manifest_path, image_path, output_path))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    image = np.load(image_path, mmap_mode='r', allow_pickle=False)
    if image.ndim != 2 or not np.issubdtype(image.dtype, np.floating):
        raise ValueError('A imagem XRMC deve ser uma matriz 2D de ponto flutuante.')
    labels = reference_labels(manifest, image.shape)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, labels=labels)
    provenance = {
        'schema_version': 1,
        'origin': 'geometria_ideal_do_cenario_xrmc_minimo',
        'method': 'intersecao_das_projecoes_da_perfuracao_nas_duas_faces; raios_centrais e centros de pixel',
        'image_sha256': sha256(image_path),
        'manifest_sha256': sha256(manifest_path),
        'reference_regions': int(np.unique(labels[labels > 0]).size),
        'reference_pixels': int(np.count_nonzero(labels)),
        'reference_objects': [{
            'reference_id': 1, 'shape': 'circulo_passante',
            'depth_mm': float(manifest['phantom']['thickness_cm']) * 10,
            'area_px': int(np.count_nonzero(labels)),
        }],
        'boundary_note': 'Amostragem de pixels e penumbra podem deslocar a borda visível.',
    }
    output_path.with_suffix('.json').write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding='utf-8')
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--imagem', type=Path, required=True)
    parser.add_argument('--saida', type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.manifest, args.imagem, args.saida)
    print(f"Referência: {args.saida} ({result['reference_regions']} região, "
          f"{result['reference_pixels']} pixels)")


if __name__ == '__main__':
    main()
