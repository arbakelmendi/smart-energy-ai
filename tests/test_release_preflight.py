"""Release preflight must report prerequisites without mutating application state."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ReleasePreflightTests(unittest.TestCase):
    def test_default_preflight_does_not_connect_create_database_or_write_research(self):
        paths = [ROOT/'ml/models/final_xgboost_model.json', *sorted((ROOT/'ml/results').glob('*.json'))]
        before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        with tempfile.TemporaryDirectory(prefix='release-preflight-') as directory:
            database = Path(directory)/'must-not-exist.db'
            result = subprocess.run([sys.executable,str(ROOT/'tests/verify_demo_preflight.py')],
                cwd=directory,env={**os.environ,'DATABASE_URL':'sqlite:///'+database.as_posix()},
                capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            evidence=json.loads(result.stdout)
            self.assertFalse(evidence['database_connected'])
            self.assertFalse(evidence['raw_or_processed_data_required'])
            self.assertFalse(evidence['model_fit'])
            self.assertFalse(database.exists())
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})

    def test_invalid_database_configuration_does_not_echo_connection_secret(self):
        secret='preflight-private-marker-not-a-real-credential'
        result=subprocess.run([sys.executable,str(ROOT/'tests/verify_demo_preflight.py')],
            env={**os.environ,'DATABASE_URL':'invalid-'+secret},capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('Preflight failed',result.stderr)
        self.assertNotIn(secret,result.stdout+result.stderr)
        self.assertNotIn('Traceback',result.stderr)

    def test_missing_prerequisites_fail_without_creating_files(self):
        namespace=runpy.run_path(str(ROOT/'tests/verify_demo_preflight.py'))
        with tempfile.TemporaryDirectory(prefix='release-preflight-empty-') as directory:
            function=namespace['main']
            with patch.dict(function.__globals__,{'ROOT':Path(directory)}), patch.object(sys,'argv',['verify_demo_preflight.py']):
                with self.assertRaisesRegex(ValueError,'Missing prerequisites'):
                    function()
            self.assertEqual(list(Path(directory).iterdir()),[])


if __name__=='__main__':
    unittest.main()
