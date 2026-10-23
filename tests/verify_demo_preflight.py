"""Read-only full-stack preflight. Never connects to DB, fits or repairs.

--development-request optionally reads the first TRAIN row for a Swagger body.
Normal startup needs neither processed datasets nor operational DB state.
"""
from pathlib import Path
import argparse
import hashlib
import importlib
from importlib.metadata import version
import json
import shutil
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
        'ml/results/phase14_recommendation_thresholds.json', 'alembic.ini',
        'scripts/create_admin.py', 'docs/thesis-demo-guide.md',
        'docs/defense-technical-reference.md', 'docs/project-fact-sheet.md',
        'docs/reproducibility.md', 'docs/final-application-overview.md',
        'docs/final-demo-checklist.md', 'package.json', 'node_modules/typescript/bin/tsc',
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise ValueError('Missing prerequisites: ' + ', '.join(missing))
    dependencies = {}
    for package, module in [('pandas','pandas'), ('numpy','numpy'),
            ('scikit-learn','sklearn'), ('xgboost','xgboost'), ('joblib','joblib'),
            ('fastapi','fastapi'), ('pydantic','pydantic'), ('uvicorn','uvicorn'),
            ('SQLAlchemy','sqlalchemy'), ('alembic','alembic'), ('pwdlib','pwdlib'),
            ('argon2-cffi','argon2'), ('email-validator','email_validator'),
            ('python-multipart','python_multipart')]:
        importlib.import_module(module)
        dependencies[package] = version(package)
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from backend.database import database_url
    from backend.main import app
    from ml.src.model_inference import load_final_model
    from ml.src.recommendation_engine import load_thresholds
    config = Config(str(ROOT / 'alembic.ini'))
    config.set_main_option('script_location', str(ROOT / 'backend/migrations'))
    heads = ScriptDirectory.from_config(config).get_heads()
    if heads != ['0026_prediction_feature_snapshots']:
        raise ValueError('Unexpected migration head; review release documentation')
    try:
        url = database_url()
        backend = url.get_backend_name()
        if backend not in ('sqlite', 'postgresql'):
            raise ValueError()
    except Exception:
        raise ValueError('Database configuration is invalid; inspect DATABASE_URL privately') from None
    bundle = load_final_model()
    metadata = bundle[1]
    actual_hash = hashlib.sha256((ROOT / metadata['model_artifact_relative_path']).read_bytes()).hexdigest()
    if actual_hash != metadata['model_artifact_sha256']:
        raise ValueError('Model checksum mismatch')
    schema = json.loads((ROOT / 'ml/results/feature_schema.json').read_text(encoding='utf-8'))
    if metadata['ordered_feature_names'] != schema['model_feature_columns'] or len(metadata['ordered_feature_names']) != 42:
        raise ValueError('Feature schema differs from production ordering')
    load_thresholds()
    scripts = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['scripts']
    if not all(name in scripts for name in ('dev', 'build')):
        raise ValueError('Frontend dev/build script missing')
    if not shutil.which('node') or not (shutil.which('npm.cmd') or shutil.which('npm')):
        raise ValueError('Node/npm command unavailable')
    if args.development_request:
        import pandas as pd
        path = ROOT / 'data/processed/energy_train.csv'
        if not path.is_file():
            raise ValueError('Optional development example requires data/processed/energy_train.csv')
        features = pd.read_csv(path, nrows=1, float_precision='round_trip')[metadata['ordered_feature_names']]
        from ml.src.model_inference import predict_next_appliances
        predict_next_appliances(features, bundle)
        print(json.dumps({'features': features.iloc[0].to_dict()}, allow_nan=False))
    else:
        print(json.dumps({'passed': True, 'api': app.title, 'python': sys.version.split()[0],
            'packages': dependencies, 'model': metadata['model_name'], 'model_sha256': actual_hash,
            'feature_count': 42, 'feature_order_matches': True, 'thresholds_loaded': True,
            'migration_head': heads[0], 'database_backend': backend,
            'database_connected': False, 'database_migration_applied_checked': False,
            'admin_existence_checked': False, 'frontend_scripts': scripts,
            'openapi_operation_count': sum(method in ('get','post','patch','delete','put')
                for item in app.openapi()['paths'].values() for method in item),
            'raw_or_processed_data_required': False, 'research_writes': False,
            'test_data_read': False, 'model_fit': False,
            'next_step': 'Explicitly migrate DB, bootstrap ADMIN, start services and verify sign-in.'}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except ValueError as exc:
        print('Preflight failed: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print('Preflight failed (' + type(exc).__name__ + '): verify installed dependencies and matching artifacts; inspect configuration privately.', file=sys.stderr)
        raise SystemExit(1)
