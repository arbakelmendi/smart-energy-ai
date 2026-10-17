<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

# Bachelor thesis project rules

## Scope and workflow
- Project: Artificial Intelligence for Prediction and Optimization of Energy Consumption in Smart Buildings. Keep work understandable, reproducible, scientifically defensible, and simple enough to explain in a thesis defense.
- Work only on the explicitly requested phase. Inspect relevant files first, preserve working functionality, and never implement later phases early.
- After each phase, run relevant checks, report passes/failures and assumptions, list every created/modified file with its purpose, and stop.
- Preserve the existing Lovable frontend and design. It uses React/TypeScript, Vite, Tailwind, and TanStack Start with file-based routes and SSR; it is not a plain Vite SPA. Preserve the root layout and server middleware. Do not hand-edit src/routeTree.gen.ts or duplicate plugins provided by the Lovable Vite wrapper.
- Add data/, ml/, backend/, and tests/ around the existing frontend when their phase is authorized; do not relocate the frontend.

## Data and forecasting
- Initial dataset: UCI Appliances Energy Prediction. The primary task is one-step-ahead prediction: use information available up to time t to predict Appliances at t+1. One observation interval is expected to be approximately 10 minutes; verify this from the actual dataset before relying on it.
- Never invent dataset variables or synthetic occupancy. Use occupancy only if a selected dataset actually supplies reliable observations.
- Verify schema, timestamps, interval continuity, units, missing values, and duplicates. Document cleaning decisions and dataset provenance.
- Prevent leakage: chronological train/validation/test splits (recommended 70/15/15), no random shuffling, training-only fitting of preprocessing, and no future observations in predictors or rolling statistics. Keep labels on the correct side of split boundaries.
- Consider hour, weekday, month, weekend, cyclical encodings, lags, and rolling statistics. Candidate lags are 1/6/144/1008 ten-minute steps; validate usefulness instead of adding all automatically. Document whether lag indices are relative to forecast origin or target time.

## Models and evaluation
- First implement persistence, Linear Regression, Random Forest Regressor, and XGBoost Regressor. No optional algorithms until these four work correctly.
- Use the training set to fit model parameters.
- Use the validation set and/or TimeSeriesSplit within the training/development portion for hyperparameter tuning and candidate-model comparison. Report validation MAE, RMSE, and R-squared for the four required approaches.
- Select the final model based on validation performance, primarily RMSE together with MAE and R-squared.
- Keep the test set untouched throughout model development, hyperparameter tuning, comparison, and final model selection. Never repeatedly compare models on the test set and select the winner from test results.
- After selecting the final model, evaluate it once on the untouched test set. Report test-set MAE, RMSE, and R-squared as the final performance estimate.
- Follow this chronological workflow: Training -> Validation / TimeSeriesSplit -> Hyperparameter tuning -> Model comparison -> Final model selection -> Final untouched test evaluation.
- Document the validation ranking and tie-breaking rule before model comparison, with RMSE as the primary metric. Never assume an algorithm wins. Report any proposed change to the approved research methodology before implementing it; do not change it silently.
- Record split boundaries, feature definitions, seeds, dependencies, parameters, and evaluation results for reproducibility. Provide feature importance when supported; defer SHAP.
- Never fabricate or hardcode model results or predictions. Existing mock data is a UI prototype, not research evidence; replace it only within an authorized phase. Do not add fake data to make features appear functional.

## Recommendations and honest presentation
- Optimization means prediction plus data-driven decision support. Derive recommendations from observed/predicted values and documented historical statistics; do not claim physical HVAC/building control.
- Do not imply correlation proves that changing an environmental variable saves energy. Never fabricate comfort, occupancy, or equipment evidence.
- Clearly label any simulated energy, monetary, or CO2 savings as estimates/scenarios and document assumptions. Do not present them as measured savings. Do not show unvalidated confidence intervals as statistical results.

## Technology and repository safety
- Use Python, Pandas, NumPy, scikit-learn, XGBoost, joblib, and FastAPI/Pydantic/Uvicorn as their phases require. Reuse existing frontend components and charts; notebooks and Matplotlib/Plotly may support analysis.
- Do not introduce Docker, Kubernetes, cloud services, MongoDB, TensorFlow, PyTorch, microservices, authentication infrastructure, or unrelated complexity unless explicitly requested. Existing demo authentication is not real security.
- Use project-relative paths. Never commit secrets, environment files, raw datasets, or large generated models unless explicitly requested. Add appropriate ignore rules during setup.
- Preserve unrelated user changes. Do not push, merge, delete branches, rename the repository, or rewrite Git history without explicit authorization. Preserve the Lovable notice above.
- Phase 1 repository foundation is complete. The current authorized task is this AGENTS.md update only; do not start Phase 2 until explicitly requested.

## Additional persistent implementation rules
- Existing repository-wide ESLint errors are pre-existing frontend issues. Do not perform repository-wide lint or formatting cleanup unless explicitly requested, and do not reformat unrelated frontend files while implementing thesis functionality.
- Preserve src/routeTree.gen.ts. It may change only when TanStack legitimately regenerates it as a consequence of an explicitly required routing change.
- Preserve the current Bun/npm package-management state. Do not delete or regenerate lockfiles or standardize package managers unless explicitly requested.
- Existing mock research values may temporarily remain in the frontend while the ML pipeline is developed. They must eventually be replaced by real calculated/backend values. Never present mock values as measured thesis results.
- Do not add or claim support for LSTM, occupancy prediction, synthetic occupancy, multi-building prediction, equipment-specific automatic control, automatic HVAC control, or hourly or 24-hour forecasting unless explicitly implemented in a later approved phase. The prohibition on invented dataset variables and synthetic occupancy remains in force unless explicitly revised by the user.
- Never fabricate predictions, MAE, RMSE, R-squared, energy savings, cost savings, CO2 savings, feature importance, or confidence intervals.
- Any later savings calculation based on a scenario rather than physical measurements must be clearly labeled as simulated or estimated.
