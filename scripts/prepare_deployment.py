"""Restaurar únicamente artefactos congelados y verificar su integridad; sin entrenar."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    bundle = ROOT / 'deployment/artifacts'
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    allowed = {'models/modelo_seleccionado.joblib', 'data/processed/test.csv',
               'data/processed/development.csv'}
    assert set(manifest['files']) == allowed
    for destination, item in manifest['files'].items():
        source = bundle / Path(destination).name
        if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('El artefacto de despliegue no coincide con el verificado.')
        target = ROOT / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    from src.evaluation import load_frozen_experiment
    _, _, _, hashes = load_frozen_experiment(ROOT)
    print('Artefactos restaurados y verificados. Modelo:', hashes['model_sha256'])

if __name__ == '__main__':
    main()
