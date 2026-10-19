"""Repeatable Phase 18 gates using installed tools; no fitting or research writes.

Run with project .venv from the project root. Optional --browser runs the existing
Windows Edge/CDP verifier after the automated gates. Logs go to ignored generated/.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
GENERATED = ROOT / "ml/results/generated"


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(name, command):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    (GENERATED / ("phase18_" + name + ".log")).write_text(output, encoding="utf-8")
    return {"command": [".venv/Scripts/python.exe" if item == sys.executable else "npm" if str(item).lower().endswith("npm.cmd") else str(item) for item in command], "return_code": result.returncode, "passed": result.returncode == 0}, output


def main():
    GENERATED.mkdir(exist_ok=True)
    protected = [p for directory in ("data/raw", "data/processed", "ml/models", "ml/results", "ml/notebooks", "ml/src")
                 for p in (ROOT / directory).glob("*") if p.is_file() and p.name != "phase18_quality_assurance.json"]
    protected += [ROOT / p for p in ("src/routeTree.gen.ts", "package-lock.json", "bun.lock", "package.json", "requirements.txt")]
    baseline = {p.relative_to(ROOT).as_posix(): checksum(p) for p in protected if p.is_file()}
    from ml.src import model_inference as inference
    bundle = inference.load_final_model()
    from backend.main import app
    result = {"application_import": app.title, "model_loaded": bundle[1]["model_name"]}
    result["python_tests"], output = run("python_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"])
    count = re.search(r"Ran (\d+) tests?", output)
    result["python_tests"]["collected"] = int(count.group(1)) if count else None
    result["python_tests"]["skipped"] = 0 if "skipped=" not in output else int(re.search(r"skipped=(\d+)", output).group(1))
    result["frontend_tests"], output = run("frontend_tests", ["node", "--experimental-strip-types", "--test", "tests/frontend_api.test.mjs"])
    for key in ("tests", "pass", "fail", "skipped"):
        match = re.search(r"(?:#|\u2139) " + key + r" (\d+)", output)
        result["frontend_tests"][key] = int(match.group(1)) if match else None
    result["build"], output = run("build", [shutil.which("npm.cmd") or "npm", "run", "build"])
    result["build"]["significant_warnings"] = [line for line in output.splitlines() if "warn" in line.lower() or "vite-tsconfig-paths" in line or "PLUGIN_TIMINGS" in line]
    result["typecheck"], _ = run("typecheck", ["node", "node_modules/typescript/bin/tsc", "--noEmit"])
    targets = ["src/lib/api/client.ts", "src/lib/api/types.ts", "src/lib/api/smartEnergyApi.ts", "src/lib/api/research-schemas.ts",
               "src/hooks/use-smart-energy-api.ts", "src/components/research-dashboard.tsx", "src/components/backend-status.tsx",
               "src/components/app-shell.tsx", "src/components/charts.tsx", "src/routes/dashboard.tsx", "src/routes/predictions.tsx", "src/routes/recommendations.tsx"]
    result["targeted_lint"], output = run("targeted_lint", ["node", "node_modules/eslint/bin/eslint.js", *targets, "--format", "json"])
    try:
        entries = json.loads(output)
        counts = {}
        for entry in entries:
            for message in entry["messages"]:
                key = message.get("ruleId") or "parser"
                counts[key] = counts.get(key, 0) + 1
        result["targeted_lint"]["issues_by_rule"] = counts
    except ValueError:
        result["targeted_lint"]["parseable_json_report"] = False
    result["targeted_semantic_lint"], _ = run("targeted_semantic_lint", ["node", "node_modules/eslint/bin/eslint.js", *targets, "--rule", '{"prettier/prettier":"off"}'])
    if "--browser" in sys.argv:
        result["browser"], _ = run("browser", [sys.executable, "tests/verify_dashboard_browser.py", "--phase18"])
    changed_sources = subprocess.run(["git", "diff", "--name-only"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    qa_targets = [name for name in changed_sources if name.startswith("src/") and name.endswith((".ts", ".tsx")) and name != "src/routeTree.gen.ts"] + ["src/lib/demo-session.ts"]
    result["qa_semantic_lint"], _ = run("qa_semantic_lint", ["node", "node_modules/eslint/bin/eslint.js", *qa_targets, "--rule", '{"prettier/prettier":"off"}'])
    patterns = {"private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "aws_access_key": r"AKIA[0-9A-Z]{16}", "github_token": r"gh[pousr]_[A-Za-z0-9]{30,}", "openai_key": r"sk-(?:proj-)?[A-Za-z0-9_-]{40,}"}
    files = list((ROOT / "src").rglob("*.ts")) + list((ROOT / "src").rglob("*.tsx")) + list((ROOT / "backend").glob("*.py")) + list((ROOT / ".output/public/assets").glob("*.js"))
    findings = []
    for file in files:
        text = file.read_text(encoding="utf-8", errors="replace")
        for name, pattern in patterns.items():
            if re.search(pattern, text):
                findings.append({"file": file.relative_to(ROOT).as_posix(), "pattern": name})
    result["security_sanity"] = {"files_scanned": len(files), "secret_pattern_findings": findings, "scope": "Lightweight source and built frontend JS pattern scan, not penetration testing or proof of absence of all secrets."}
    result["git_diff_check"], _ = run("git_diff_check", ["git", "diff", "--check"])
    result["protected_checksums_unchanged"] = all(checksum(ROOT / path) == expected for path, expected in baseline.items())
    result["protected_file_count"] = len(baseline)
    result["artifact_checksums"] = baseline
    result["python_warnings"] = ["Installed Starlette TestClient warns that httpx support is deprecated; all tests execute with existing httpx."]
    (GENERATED / "phase18_gates.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "artifact_checksums"}, indent=2))
    gates = ["python_tests", "frontend_tests", "build", "typecheck", "targeted_semantic_lint", "qa_semantic_lint", "git_diff_check"]
    if "browser" in result:
        gates.append("browser")
    if not all(result[key]["passed"] for key in gates) or not result["protected_checksums_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
