# Smart Energy Pulse

Build a web application called Smart Energy AI — an intelligent platform for forecasting and optimizing energy consumption in smart buildings, powered by machine learning models. The GitHub repository will be named smart-energy-ai.

Product context

The app serves building managers, facility administrators (schools, hospitals, offices, shopping centers, residential buildings), and energy analysts. Goal: visualize historical consumption, view forecasts of future consumption (based on temperature, humidity, season, time of day, day of week, number of occupants), and receive practical recommendations for reducing consumption without sacrificing comfort.

Design direction — NOT GENERIC

Don't use the standard "blue-and-white dashboard with plain cards" template. I want a specific, alive visual identity that connects the energy theme with AI:

Color palette: dark base (deep navy/charcoal, e.g. #0B1220 – #111827) combined with energetic accents — electric green/teal for efficiency (#22D3A6 or similar) and warm amber/orange for alerts/peak consumption (#F59E0B). High contrast, a modern "control room" feel, not corporate pastel.

Typography: a strong sans-serif font for headings (e.g. Space Grotesk / Sora style) paired with a clean font for body text (Inter). Avoid Lovable's thoughtless default fonts.

Distinctive visual elements: subtle gradient mesh or "glow" behind key cards, background lines/graphs suggesting energy waves or a pulse chart, line-style icons (not emoji), light micro-animations (hover states, numbers that "count up", smooth transitions between pages).

Charts: use dark-mode chart styling with gradient fill under the lines, not default charts on a white background.

Don't repeat the same card layout on every page — vary the visual rhythm: some full-width sections with a large chart, some grid layouts with small cards, some dense tables for data.

Must support both light mode and dark mode, but default to dark mode (fitting for an energy "control room").

Fully responsive (mobile, tablet, desktop) — the dashboard especially should degrade gracefully on mobile with collapsible charts/tabs.

Pages and functionality

1. Landing Page (public)

Hero section with a strong headline (e.g. "Predict. Optimize. Save energy with AI.") and a visualization/animation suggesting live energy data.

"How it works" section (3–4 steps: data collection → predictive model → recommendations → savings).

Section with demo metrics (e.g. "up to X% reduction in consumption", MAE/RMSE as technical trust indicators).

"Use cases" section (schools, hospitals, offices, shopping centers, residential buildings) as cards.

Call-to-action for Sign Up / Request Demo.

Footer with links, contact info.

2. Authentication

Login (email + password, "Remember me" option, "Forgot password?")

Sign Up (name, email, password, account role: Building Admin / Analyst / Viewer)

Forgot/Reset Password flow (email → code/link → new password)

"Verify your email" page

3. Onboarding (after first registration)

Short wizard: add your building (name, type, m², address), connect a data source (CSV upload or simulated "connect sensor"), set savings goals.

4. Main Dashboard (logged-in user)

Overview: current consumption vs forecast, estimated savings, 7/30/90-day trend chart.

"Active AI recommendations" card (e.g. "Lower heating by 2°C between 2:00–4:00 PM").

Comparison chart of actual vs predicted consumption (with confidence interval).

Alerts/notifications for anomalous consumption.

Per-building section if the user manages multiple buildings (building selector).

5. Predictions Page

Detailed short-term/long-term forecast chart.

Filters by factor (temperature, humidity, season, time of day).

Model metrics (MAE, RMSE, R²) clearly displayed for transparency.

Ability to compare different algorithms (e.g. Linear Regression vs Random Forest vs LSTM) — comparison table/chart.

6. Data Analysis Page (Data / Reports)

Dataset upload/import (CSV) with preview.

Historical data table with search, filter, sort.

Report export (PDF/CSV).

Charts broken down by: time of day, day of week, season.

7. Recommendations

List of system-generated recommendations, ranked by impact (high/medium/low savings).

Status per recommendation: new / in progress / applied / dismissed.

8. Building Management (Buildings)

List of buildings as cards (name, type, current consumption, status).

Detail page for a specific building with all the above charts filtered for that building.

Add/Edit/Delete building.

9. User Profile / Settings

Personal info, password change.

Notification preferences.

Theme selection (dark/light).

Management of linked accounts (if there are team members).

10. Admin Panel (role: Admin)

Separate admin dashboard: platform-wide stats (number of users, number of buildings, total aggregated consumption, average model accuracy).

User management (list, role, activate/deactivate, delete).

Management of all buildings in the system.

Log/audit of key activities.

AI model configuration (e.g. alert thresholds, active model version).

11. Helper pages

Custom 404 page (not default).

"About the Project" page (academic context: UBT, thesis topic).

Contact/support page.

Suggested technical structure

Use clear routes: /, /login, /signup, /dashboard, /predictions, /data, /recommendations, /buildings, /buildings/:id, /settings, /admin, /admin/users, /admin/buildings.

Clearly separate the public layout (landing, auth) from the app layout (sidebar + topbar for dashboard/admin).

Collapsible sidebar with icons, active state clearly highlighted with the green/teal accent.

Use realistic mock data (not "Lorem ipsum") for charts and tables, so the demo looks academically convincing (kWh, °C, real calendar dates).

Overall tone

Serious, technical-academic but modern — it should feel like a real SaaS product for energy management, not a basic student project. Focus on data clarity and trustworthiness (visible model metrics), without overloading the UI.

Note: after the first generation, you can ask Lovable to refine individual pages (e.g. "improve the main dashboard by adding the actual-vs-predicted comparison chart with a confidence interval").

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/51b987dd-100f-4fdf-9eb1-f1ae8a81ba78).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
