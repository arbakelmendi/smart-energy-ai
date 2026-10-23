# Final full-stack thesis demo guide

[Checklist](final-demo-checklist.md) | [Fact sheet](project-fact-sheet.md) | [Technical answers](defense-technical-reference.md) | [Exact setup](../README.md#local-installation-and-startup)

## Prepare before defense

Follow README once: install dependencies, provision matching ignored model, migrate DB and create your own ADMIN using the hidden-password bootstrap. Never store credentials in source/docs. Preflight is read-only; it does not confirm accounts or apply migrations:

```powershell
.\.venv\Scripts\Activate.ps1
python tests/verify_demo_preflight.py
python -m alembic current
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second root terminal:

```powershell
npm run dev -- --host localhost --port 5173 --strictPort
```

Use browser/API **localhost** consistently: [application](http://localhost:5173), [health](http://localhost:8000/health), [Swagger](http://localhost:8000/docs). Binding Uvicorn to loopback is compatible with these browser URLs. Keep startup errors visible. Never regenerate research results during defense.

## Two honest data options

**A: prepared UCI Reference Building (easiest live-defense backup).** With original CSV and an existing active ADMIN, explicitly run:

```powershell
python scripts/import_uci_reference_building.py --admin-email <your-admin-email>
```

Replace placeholder with your privately chosen account. The tool imports 19,735 observed historical UCI records under that ADMIN; repeat import is rejected. It is not startup seeding or another building validation. Sign in as that ADMIN and use its ordinary dashboard for forecasting. Dedicated admin views inspect other owners but do not run their forecasts.

**B: USER-owned building with compatible CSV.** Signup, create building and import observed history following [CSV contract](measurement-import.md). Use `date` or `timestamp` and all 26 correctly cased raw values. UCI `rv1`/`rv2` are recognized and ignored; never invent derived features/occupancy. At least 1,009 continuous ten-minute observations ending at the latest observation are required. If manually entering the first row, exclude it from CSV to avoid atomic duplicate rejection. Keep one genuine subsequent observation available to append. This demonstrates workflow; external-building predictions remain experimental. A user-created copy of UCI history is still UCI historical data.

## Suggested sequence (about 10-15 minutes)

1. Explain objective: next-ten-minute Appliances Wh and conservative decision support, not automatic control.
2. Signup/login, create/edit metadata, select building. Registration supplies neither measurements nor model validation.
3. Show manual measurement and actual CSV import, atomic errors, count/time range; refresh for persistence.
4. Show NOT READY for insufficient/gapped history and READY for a continuous 1,009-point latest window. Counts alone are insufficient.
5. Click **Predict next 10 minutes**. Server builds 42 features and runs existing model/Phase 14 rules. Explain origin/target time and Wh, not instantaneous power.
6. Show recommendation, repeat request for identical-input reuse, open saved history. Genuine later history makes prior results historical until explicit new forecast.
7. Open separate dashboard research section: validation selected Tuned XGBoost before TEST. Exact final metrics are in fact sheet; R-squared is not accuracy/savings percentage. Importance is predictive, not causal.
8. Switch two owned buildings for isolation. Another USER cannot read these private API resources/deep links.
9. Sign in as ADMIN; inspect overview/users/buildings/activity. Deactivate prepared USER: next protected request/login fails while records remain. Reactivate, then sign in again; old sessions never revive. Never deactivate yourself.
10. Refresh owned-building deep link, restart backend and Retry to demonstrate persistence. Explain limitations.

## Recovery

- Backend: inspect terminal, restart above command, check `/health`, then Retry. No fallback operational values.
- Frontend: inspect terminal/root/port; restart with localhost/strict port. Never kill unrelated processes.
- Database: inspect `DATABASE_URL` privately, use `alembic current` and explicit upgrade after backing up real data; never delete/reseed to hide an error.
- Model: stop forecast demo on missing/mismatched artifact. Restore original matching file. Deliberate `python ml/src/save_final_model.py` requires matching processed TRAIN/VALIDATION/TEST and recorded environment, reconstructs locked fit and equivalence gates, and is not live-defense repair. Never weaken checksums/rewrite results.
- Incomplete USER history: use prepared ADMIN-owned UCI alternative labeled historical. If services cannot recover, show documents while acknowledging unavailable application.
- Stop your own terminals with Ctrl+C afterward.

No IoT telemetry, occupancy, external-building validation, scheduler/control, verified savings, calibrated intervals or production-grade security is claimed. Optional low-level Swagger example `python tests/verify_demo_preflight.py --development-request` alone requires processed TRAIN CSV; it is historical development data, not normal startup.
