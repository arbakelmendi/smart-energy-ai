# Final application overview

[Setup](../README.md) | [Demo checklist](final-demo-checklist.md) | [Architecture](system-architecture.md) | [Routes and APIs](final-endpoint-inventory.md)

SmartEnergyAI addresses next-interval Appliances energy forecasting and transparent decision support for smart buildings. It is a completed Bachelor research/application prototype with real relational persistence and role-based access. It is not certified commercial software.

The finalized research model is **Tuned XGBoost**, with **42 features**, predicting **Wh over the next ten-minute interval**. Final held-out TEST MAE is **25.891124725341797 Wh**, RMSE **59.11701146812037 Wh**, and R-squared **0.5820133686065674**. These are original single-building research results, not measurements from newly registered buildings. [Methodology](research-methodology.md) preserves selection and evaluation.

React/TypeScript and TanStack Start SSR/file routing call FastAPI through a typed native-fetch client and TanStack Query. FastAPI verifies opaque cookie sessions and ownership, then uses SQLAlchemy/Alembic and a local SQLite database. The schema supports PostgreSQL-style deployment, but its driver/server and live concurrency are not validated here.

A USER signs up/signs in, creates a building, enters or imports actual compatible history, checks readiness and explicitly requests a forecast. Continuous recent ten-minute history supplies 1,009 observations for origin-relative seven-day lags and rolling statistics. The server constructs the ordered feature row, loads the verified model, applies the unchanged recommendation engine, and atomically persists forecast, recommendation, checksum and feature fingerprint/snapshot. Identical input reuses the same semantic prediction. Changed history leaves earlier results historical; the current dashboard requires matching source/model/features. Nothing schedules forecasts automatically.

An ADMIN uses dedicated overview/user/building/prediction APIs to inspect cross-owner activity and deactivate/reactivate accounts. Deactivation revokes sessions while retaining domain records. Ordinary building APIs remain owner-only even for ADMIN. The supported reference importer creates historical UCI data only on explicit request by an existing active ADMIN.

Passwords are salted Argon2id hashes. Sessions are random opaque HttpOnly/SameSite cookies; only token digests are stored. Expiry, active-account checks, trusted-Origin/non-simple-header CSRF enforcement, credentialed CORS, safe errors and private query isolation define the implemented security boundary. [Security audit](security-and-quality-assurance.md) records its limits.

Observed history, stored predictions and original research evidence are separate. Ownership/schema compatibility does not validate transfer to another building. Source data covers one building in January-May; observations use naive source-local timestamps. There is no occupancy input, IoT streaming, actuator/control integration, automatic forecast scheduler, verified intervention savings or calibrated prediction interval. Other limits include no MFA/rate limiting/email recovery delivery, local SQLite write limits, partly unpinned dependencies and no production-security certification.
