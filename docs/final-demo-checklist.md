# Final defense checklist

[Exact setup](../README.md#local-installation-and-startup) | [Demo sequence and recovery](thesis-demo-guide.md)

## Before defense

- [ ] Review `git status`; commit only the intended release manifest. Resolve the generated route-tree recommendation in the final audit explicitly.
- [ ] Activate `.venv`; install documented dependencies beforehand, including recorded numerical versions.
- [ ] Install frontend dependencies without creating `package-lock.json`; preserve `bun.lock`.
- [ ] Place verified ignored `ml/models/final_xgboost_model.json`; run `python tests/verify_demo_preflight.py`.
- [ ] Have `data/raw/energydata_complete.csv` if using the explicit UCI importer or preparing a real compatible CSV.
- [ ] Run `python -m alembic upgrade head`; check `python -m alembic current`.
- [ ] Create your own ADMIN with `python scripts/create_admin.py`; retain credentials privately.
- [ ] Start backend/frontend using the localhost commands in README; check `/health`, `/docs` and sign-in.
- [ ] Rehearse with observed historical data; do not call it live telemetry. Keep a prepared reference-building alternative.

## During demo

- [ ] Explain objective, Wh/ten-minute semantics and single-building validation boundary.
- [ ] Show signup/login, create/select building, manual/CSV measurements and continuity-based readiness.
- [ ] Request forecast/recommendation, repeat to demonstrate reuse, and show persisted history/dashboard.
- [ ] Explain separate research results and exact held-out metrics.
- [ ] Sign in as ADMIN; inspect overview/users/buildings/predictions, then deactivate/reactivate a prepared USER.
- [ ] State limits: experimental transfer, no IoT/control/savings/intervals, prototype security.

## Recovery

- [ ] Backend: inspect terminal, restart README command, check `/health`, then Retry.
- [ ] Frontend: inspect terminal and restart with localhost/strict port; refresh owned-building deep link.
- [ ] Database: inspect `DATABASE_URL` privately and `alembic current`; back up real data before migration. Never delete it to hide an error.
- [ ] Model: stop forecast demo on mismatch. Restore verified artifact; deliberate `python ml/src/save_final_model.py` regeneration requires matching splits/environment and is not live-defense repair.
- [ ] If USER history is incomplete, use explicitly imported ADMIN-owned UCI Reference Building; it is historical data, not another validated building.
- [ ] If services cannot recover, show fact sheet honestly as documents rather than claim a running application.
