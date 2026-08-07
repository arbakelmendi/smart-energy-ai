/**
 * Deterministic mock data for the Smart Energy AI demo.
 * Values are seeded so server render and client render always match.
 */

export type BuildingType =
  | "School"
  | "Hospital"
  | "Office"
  | "Shopping Center"
  | "Residential";

export type Building = {
  id: string;
  name: string;
  type: BuildingType;
  address: string;
  areaM2: number;
  occupants: number;
  currentKwh: number;
  baselineKwh: number;
  savingsPct: number;
  status: "optimal" | "watch" | "peak";
  sensors: number;
};

export const buildings: Building[] = [
  {
    id: "ubt-campus-a",
    name: "UBT Campus — Block A",
    type: "School",
    address: "Rr. Rexhep Krasniqi 56, Prishtinë",
    areaM2: 8400,
    occupants: 1250,
    currentKwh: 412.6,
    baselineKwh: 476.3,
    savingsPct: 13.4,
    status: "optimal",
    sensors: 42,
  },
  {
    id: "regional-hospital",
    name: "Regional Hospital — Wing C",
    type: "Hospital",
    address: "Bulevardi i Dëshmorëve 12, Prishtinë",
    areaM2: 15200,
    occupants: 640,
    currentKwh: 1284.9,
    baselineKwh: 1310.4,
    savingsPct: 1.9,
    status: "peak",
    sensors: 88,
  },
  {
    id: "meridian-offices",
    name: "Meridian Business Tower",
    type: "Office",
    address: "Rr. Luan Haradinaj 4, Prishtinë",
    areaM2: 11600,
    occupants: 890,
    currentKwh: 726.1,
    baselineKwh: 869.5,
    savingsPct: 16.5,
    status: "optimal",
    sensors: 61,
  },
  {
    id: "albi-mall",
    name: "Albi Retail Center",
    type: "Shopping Center",
    address: "Magjistralja Prishtinë–Ferizaj km 7",
    areaM2: 24800,
    occupants: 3400,
    currentKwh: 2140.3,
    baselineKwh: 2288.0,
    savingsPct: 6.5,
    status: "watch",
    sensors: 124,
  },
  {
    id: "dardania-residences",
    name: "Dardania Residences B3",
    type: "Residential",
    address: "Lagjja Dardania, Prishtinë",
    areaM2: 6100,
    occupants: 310,
    currentKwh: 268.4,
    baselineKwh: 302.7,
    savingsPct: 11.3,
    status: "optimal",
    sensors: 28,
  },
];

export function getBuilding(id: string) {
  return buildings.find((b) => b.id === id);
}

/* ---------------------------------- seeds --------------------------------- */

function seeded(i: number, salt = 1) {
  const x = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** Fixed "today" so the demo is reproducible. */
export const TODAY = new Date(Date.UTC(2026, 1, 12));

function dateLabel(offsetDays: number) {
  const d = new Date(TODAY.getTime() - offsetDays * 86400000);
  return `${d.getUTCDate()} ${MONTH_NAMES[d.getUTCMonth()]}`;
}

export type TrendPoint = {
  date: string;
  actual: number;
  predicted: number;
  lower: number;
  upper: number;
  temperature: number;
  humidity: number;
};

/** Daily consumption series: `days` back from TODAY. */
export function buildTrend(days: number, scale = 1, salt = 3): TrendPoint[] {
  const out: TrendPoint[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const idx = days - i;
    const season = Math.cos((i / 365) * Math.PI * 2) * 0.09;
    const weekly = i % 7 === 0 || i % 7 === 6 ? -0.16 : 0.03;
    const noise = (seeded(idx, salt) - 0.5) * 0.09;
    const base = 780 * scale;
    const actual = base * (1 + season + weekly + noise);
    const bias = (seeded(idx, salt + 11) - 0.5) * 0.05;
    const predicted = actual * (1 + bias);
    const band = predicted * (0.045 + seeded(idx, salt + 5) * 0.03);
    out.push({
      date: dateLabel(i),
      actual: Math.round(actual * 10) / 10,
      predicted: Math.round(predicted * 10) / 10,
      lower: Math.round((predicted - band) * 10) / 10,
      upper: Math.round((predicted + band) * 10) / 10,
      temperature: Math.round((4 + Math.cos((i / 365) * Math.PI * 2) * 12 + noise * 8) * 10) / 10,
      humidity: Math.round(58 + seeded(idx, salt + 7) * 26),
    });
  }
  return out;
}

/** Forward-looking hourly forecast. */
export function buildForecast(hours = 48, scale = 1): TrendPoint[] {
  const out: TrendPoint[] = [];
  for (let h = 0; h < hours; h++) {
    const hourOfDay = (8 + h) % 24;
    const daily = Math.sin(((hourOfDay - 4) / 24) * Math.PI * 2) * 0.34;
    const noise = (seeded(h, 17) - 0.5) * 0.06;
    const predicted = 34 * scale * (1 + daily + noise);
    const band = predicted * (0.06 + seeded(h, 23) * 0.05);
    out.push({
      date: `${String(hourOfDay).padStart(2, "0")}:00`,
      actual: h < 12 ? Math.round(predicted * (1 + (seeded(h, 31) - 0.5) * 0.07) * 10) / 10 : 0,
      predicted: Math.round(predicted * 10) / 10,
      lower: Math.round((predicted - band) * 10) / 10,
      upper: Math.round((predicted + band) * 10) / 10,
      temperature: Math.round((2 + Math.sin(((hourOfDay - 6) / 24) * Math.PI * 2) * 7) * 10) / 10,
      humidity: Math.round(62 + seeded(h, 41) * 22),
    });
  }
  return out;
}

export const hourlyProfile = Array.from({ length: 24 }, (_, h) => ({
  hour: `${String(h).padStart(2, "0")}h`,
  kwh: Math.round((22 + Math.sin(((h - 5) / 24) * Math.PI * 2) * 13 + seeded(h, 9) * 3) * 10) / 10,
}));

export const weekdayProfile = [
  { day: "Mon", kwh: 812.4, forecast: 798.1 },
  { day: "Tue", kwh: 839.7, forecast: 826.5 },
  { day: "Wed", kwh: 851.2, forecast: 861.0 },
  { day: "Thu", kwh: 828.9, forecast: 819.4 },
  { day: "Fri", kwh: 794.3, forecast: 802.7 },
  { day: "Sat", kwh: 612.8, forecast: 604.2 },
  { day: "Sun", kwh: 548.1, forecast: 559.6 },
];

export const seasonProfile = [
  { season: "Winter", kwh: 1042.6, hdd: 412 },
  { season: "Spring", kwh: 726.9, hdd: 168 },
  { season: "Summer", kwh: 938.4, hdd: 24 },
  { season: "Autumn", kwh: 704.2, hdd: 152 },
];

/* ------------------------------- ML metrics -------------------------------- */

export type ModelRow = {
  name: string;
  type: string;
  mae: number;
  rmse: number;
  r2: number;
  trainSec: number;
  active: boolean;
};

export const models: ModelRow[] = [
  {
    name: "LSTM (seq-48)",
    type: "Deep learning",
    mae: 12.4,
    rmse: 18.9,
    r2: 0.962,
    trainSec: 486,
    active: true,
  },
  {
    name: "Random Forest",
    type: "Ensemble",
    mae: 15.1,
    rmse: 22.6,
    r2: 0.941,
    trainSec: 38,
    active: false,
  },
  {
    name: "XGBoost",
    type: "Gradient boosting",
    mae: 14.2,
    rmse: 21.1,
    r2: 0.948,
    trainSec: 52,
    active: false,
  },
  {
    name: "Linear Regression",
    type: "Baseline",
    mae: 27.8,
    rmse: 39.4,
    r2: 0.812,
    trainSec: 1,
    active: false,
  },
];

export const featureImportance = [
  { feature: "Outdoor temperature", weight: 31 },
  { feature: "Hour of day", weight: 24 },
  { feature: "Occupancy count", weight: 17 },
  { feature: "Day of week", weight: 12 },
  { feature: "Season", weight: 9 },
  { feature: "Relative humidity", weight: 7 },
];

/* ----------------------------- recommendations ---------------------------- */

export type Recommendation = {
  id: string;
  title: string;
  detail: string;
  buildingId: string;
  impact: "high" | "medium" | "low";
  savingKwh: number;
  savingEur: number;
  comfortRisk: "none" | "low" | "moderate";
  status: "new" | "in_progress" | "applied" | "dismissed";
  createdAt: string;
};

export const recommendations: Recommendation[] = [
  {
    id: "rec-1",
    title: "Lower heating setpoint by 2°C between 14:00–16:00",
    detail:
      "Afternoon solar gain on the south façade keeps Block A at 23.4°C while the boiler still runs. Model predicts no comfort deviation above 0.4 PMV.",
    buildingId: "ubt-campus-a",
    impact: "high",
    savingKwh: 186,
    savingEur: 24.8,
    comfortRisk: "none",
    status: "new",
    createdAt: "2026-02-11",
  },
  {
    id: "rec-2",
    title: "Shift chiller pre-cooling to 05:00–07:00",
    detail:
      "Off-peak tariff window plus 6°C lower ambient temperature reduces compressor load by an estimated 19%.",
    buildingId: "albi-mall",
    impact: "high",
    savingKwh: 402,
    savingEur: 53.1,
    comfortRisk: "low",
    status: "in_progress",
    createdAt: "2026-02-10",
  },
  {
    id: "rec-3",
    title: "Dim atrium lighting to 65% after 20:00",
    detail:
      "Occupancy sensors report under 40 people in the atrium after 20:00 on weekdays; measured lux stays above code minimum at 65%.",
    buildingId: "meridian-offices",
    impact: "medium",
    savingKwh: 94,
    savingEur: 12.4,
    comfortRisk: "none",
    status: "applied",
    createdAt: "2026-02-08",
  },
  {
    id: "rec-4",
    title: "Stagger AHU start-up across Wing C zones",
    detail:
      "Simultaneous 06:00 start creates a 214 kW demand spike. Staggering in 10-minute steps flattens the peak without changing zone readiness.",
    buildingId: "regional-hospital",
    impact: "high",
    savingKwh: 148,
    savingEur: 19.6,
    comfortRisk: "none",
    status: "new",
    createdAt: "2026-02-12",
  },
  {
    id: "rec-5",
    title: "Enable weekend deep setback for Block A labs",
    detail:
      "Lab occupancy on weekends averages 4 people. A 4°C setback with 90-minute recovery keeps Monday readiness intact.",
    buildingId: "ubt-campus-a",
    impact: "medium",
    savingKwh: 132,
    savingEur: 17.4,
    comfortRisk: "low",
    status: "new",
    createdAt: "2026-02-09",
  },
  {
    id: "rec-6",
    title: "Replace corridor fixtures with LED (T8 retrofit)",
    detail:
      "148 fluorescent fixtures at 58W. Payback estimated at 14 months at current tariff of 0.132 €/kWh.",
    buildingId: "dardania-residences",
    impact: "low",
    savingKwh: 41,
    savingEur: 5.4,
    comfortRisk: "none",
    status: "dismissed",
    createdAt: "2026-02-04",
  },
  {
    id: "rec-7",
    title: "Tighten CO₂-based ventilation deadband to 850 ppm",
    detail:
      "Current 700 ppm target over-ventilates classrooms by roughly 22% of design airflow during morning blocks.",
    buildingId: "ubt-campus-a",
    impact: "medium",
    savingKwh: 108,
    savingEur: 14.2,
    comfortRisk: "moderate",
    status: "in_progress",
    createdAt: "2026-02-07",
  },
];

/* --------------------------------- alerts --------------------------------- */

export type Alert = {
  id: string;
  severity: "critical" | "warning" | "info";
  title: string;
  building: string;
  delta: string;
  time: string;
};

export const alerts: Alert[] = [
  {
    id: "a1",
    severity: "critical",
    title: "Consumption 34% above forecast band",
    building: "Regional Hospital — Wing C",
    delta: "+318 kWh",
    time: "Today 09:40",
  },
  {
    id: "a2",
    severity: "warning",
    title: "Night-time baseload drift detected",
    building: "Albi Retail Center",
    delta: "+62 kWh",
    time: "Today 03:15",
  },
  {
    id: "a3",
    severity: "warning",
    title: "HVAC short-cycling on floors 4–6",
    building: "Meridian Business Tower",
    delta: "+41 kWh",
    time: "Yesterday 18:02",
  },
  {
    id: "a4",
    severity: "info",
    title: "Sensor 14 offline for 3 hours",
    building: "UBT Campus — Block A",
    delta: "—",
    time: "Yesterday 11:27",
  },
];

/* ----------------------------- historical rows ---------------------------- */

export type ReadingRow = {
  timestamp: string;
  building: string;
  kwh: number;
  temperature: number;
  humidity: number;
  occupants: number;
  dayType: "Weekday" | "Weekend";
};

export const readings: ReadingRow[] = Array.from({ length: 64 }, (_, i) => {
  const d = new Date(TODAY.getTime() - i * 3600000 * 6);
  const b = buildings[i % buildings.length];
  const hour = d.getUTCHours();
  const weekend = d.getUTCDay() === 0 || d.getUTCDay() === 6;
  return {
    timestamp: `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(
      d.getUTCDate(),
    ).padStart(2, "0")} ${String(hour).padStart(2, "0")}:00`,
    building: b.name,
    kwh:
      Math.round(
        (b.currentKwh / 24) *
          (1 + Math.sin(((hour - 5) / 24) * Math.PI * 2) * 0.3 + (seeded(i, 13) - 0.5) * 0.12) *
          10,
      ) / 10,
    temperature: Math.round((3 + Math.sin(((hour - 6) / 24) * Math.PI * 2) * 6 + seeded(i, 3) * 4) * 10) / 10,
    humidity: Math.round(56 + seeded(i, 5) * 28),
    occupants: Math.round(b.occupants * (weekend ? 0.12 : 0.35 + seeded(i, 7) * 0.5)),
    dayType: weekend ? ("Weekend" as const) : ("Weekday" as const),
  };
});

/* --------------------------------- admin ---------------------------------- */

export type PlatformUser = {
  id: string;
  name: string;
  email: string;
  role: "Building Admin" | "Analyst" | "Viewer" | "Platform Admin";
  buildings: number;
  status: "active" | "suspended" | "pending";
  lastSeen: string;
};

export const platformUsers: PlatformUser[] = [
  {
    id: "u1",
    name: "Arber Krasniqi",
    email: "arber.krasniqi@ubt-uni.net",
    role: "Platform Admin",
    buildings: 5,
    status: "active",
    lastSeen: "2026-02-12 08:12",
  },
  {
    id: "u2",
    name: "Elira Hoxha",
    email: "elira.hoxha@hospital-ks.org",
    role: "Building Admin",
    buildings: 2,
    status: "active",
    lastSeen: "2026-02-12 07:48",
  },
  {
    id: "u3",
    name: "Dritan Berisha",
    email: "d.berisha@meridian.co",
    role: "Analyst",
    buildings: 3,
    status: "active",
    lastSeen: "2026-02-11 19:20",
  },
  {
    id: "u4",
    name: "Nora Gashi",
    email: "nora.gashi@albiretail.com",
    role: "Viewer",
    buildings: 1,
    status: "pending",
    lastSeen: "—",
  },
  {
    id: "u5",
    name: "Fitim Rexhepi",
    email: "fitim@dardania-res.eu",
    role: "Building Admin",
    buildings: 1,
    status: "suspended",
    lastSeen: "2026-01-28 14:05",
  },
  {
    id: "u6",
    name: "Blerta Musa",
    email: "blerta.musa@ubt-uni.net",
    role: "Analyst",
    buildings: 4,
    status: "active",
    lastSeen: "2026-02-12 06:31",
  },
];

export type AuditEntry = {
  id: string;
  actor: string;
  action: string;
  target: string;
  at: string;
  kind: "model" | "user" | "building" | "data";
};

export const auditLog: AuditEntry[] = [
  {
    id: "l1",
    actor: "Arber Krasniqi",
    action: "Promoted model version",
    target: "LSTM seq-48 → v4.2 (active)",
    at: "2026-02-12 08:15",
    kind: "model",
  },
  {
    id: "l2",
    actor: "system",
    action: "Anomaly alert raised",
    target: "Regional Hospital — Wing C",
    at: "2026-02-12 09:40",
    kind: "data",
  },
  {
    id: "l3",
    actor: "Elira Hoxha",
    action: "Uploaded dataset",
    target: "hospital_wingC_2025Q4.csv (18,240 rows)",
    at: "2026-02-11 16:04",
    kind: "data",
  },
  {
    id: "l4",
    actor: "Arber Krasniqi",
    action: "Suspended account",
    target: "fitim@dardania-res.eu",
    at: "2026-01-28 14:22",
    kind: "user",
  },
  {
    id: "l5",
    actor: "Dritan Berisha",
    action: "Edited building metadata",
    target: "Meridian Business Tower (area 11,600 m²)",
    at: "2026-02-10 10:37",
    kind: "building",
  },
  {
    id: "l6",
    actor: "system",
    action: "Nightly retraining finished",
    target: "MAE 12.4 kWh · R² 0.962",
    at: "2026-02-12 02:10",
    kind: "model",
  },
];

export const platformStats = {
  users: 148,
  buildings: 63,
  aggregatedGwh: 41.7,
  avgAccuracy: 94.2,
  sensors: 1284,
  datasetsRows: 2_940_000,
};

export const tariffEurPerKwh = 0.132;
