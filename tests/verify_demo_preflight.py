"""Read-only local defense preflight; no fitting, TEST reads or artifact writes.

Run from any working directory with the project Python. --development-request
prints only a Swagger body from the first actual TRAIN row after all checks pass.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development-request', action='store_true')
    args = parser.parse_args()
    required = [
        'ml/models/final_xgboost_model.json', 'ml/results/final_model_metadata.json',
        'ml/results/feature_schema.json', 'ml/results/phase11_selection_lock.json',
        'ml/results/phase14_recommendation_thresholds.json', 'data/processed/energy_train.csv',
        'docs/thesis-demo-guide.md', 'docs/defense-technical-reference.md',
        'docs/project-fact-sheet.md', 'docs/reproducibility.md', 'package.json',
        'node_modules/typescript/bin/tsc',
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise ValueError('Missing prerequisites: ' + ', '.join(missing))
    import pandas as pd
    from backend.main import app
    from ml.src.model_inference import load_final_model, predict_next_appliances
    from ml.src.recommendation_engine import load_thresholds, predict_and_recommend
    bundle = load_final_model()
    metadata = bundle[1]
    model_path = ROOT / metadata['model_artifact_relative_path']
    actual_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if actual_hash != metadata['model_artifact_sha256']:
        raise ValueError('Model checksum mismatch')
    row = pd.read_csv(ROOT / 'data/processed/energy_train.csv', nrows=1)
    features = row[metadata['ordered_feature_names']]
    first = float(predict_next_appliances(features, bundle).iloc[0])
    second = float(predict_next_appliances(features, bundle).iloc[0])
    if first != second:
        raise ValueError('Repeated inference differs')
    recommendation = predict_and_recommend(features, model_bundle=bundle, thresholds=load_thresholds())[0]
    if recommendation['prediction']['value_wh'] != first:
        raise ValueError('Recommendation forecast differs')
    scripts = json.loads((ROOT / 'package.json').read_text())['scripts']
    if not all(name in scripts for name in ('dev', 'build')):
        raise ValueError('Frontend dev/build script missing')
    if not shutil.which('node') or not (shutil.which('npm.cmd') or shutil.which('npm')):
        raise ValueError('Node/npm command unavailable')
    ports = {}
    for port in (8000, 5173):
        with socket.socket() as sock:
            ports[str(port)] = 'listening' if sock.connect_ex(('127.0.0.1', port)) == 0 else 'not_listening'
    if args.development_request:
        print(json.dumps({'features': features.iloc[0].to_dict()}, allow_nan=False))
    else:
        print(json.dumps({'passed': True, 'api': app.title, 'model': metadata['model_name'],
                          'model_sha256': actual_hash, 'inference_deterministic': True,
                          'fixture': 'known development-data example: first TRAIN row',
                          'origin': str(row['date'].iloc[0]), 'feature_count': len(features.columns),
                          'recommendation_matches': True, 'frontend_scripts': scripts,
                          'ports_ipv4': ports, 'port_note': 'Listening does not identify ownership; localhost may also use IPv6. No process is stopped.',
                          'research_writes': False, 'test_data_read': False}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Preflight failed: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
