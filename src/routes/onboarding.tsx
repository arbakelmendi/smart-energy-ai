import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Check, Cpu, FileSpreadsheet, Radio, Target } from "lucide-react";
import { Logo } from "@/components/public-layout";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/onboarding")({
  head: () => ({
    meta: [
      { title: "Set up your first building — Smart Energy AI" },
      {
        name: "description",
        content:
          "Add a building, connect a data source and set a savings goal to start generating forecasts.",
      },
      { property: "og:title", content: "Set up your first building — Smart Energy AI" },
      { property: "og:description", content: "Three steps from signup to your first forecast." },
    ],
  }),
  component: OnboardingPage,
});

const stepLabels = ["Your building", "Data source", "Savings goal"];

function OnboardingPage() {
  const navigate = useNavigate();
  const { update } = useAuth();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [type, setType] = useState("Office");
  const [area, setArea] = useState("");
  const [address, setAddress] = useState("");
  const [source, setSource] = useState<"csv" | "sensor" | null>(null);
  const [goal, setGoal] = useState([12]);

  const next = () => {
    if (step === 0 && (!name.trim() || !area)) {
      toast.error("Building name and floor area are required.");
      return;
    }
    if (step === 1 && !source) {
      toast.error("Pick a data source to continue.");
      return;
    }
    if (step === 2) {
      update({ onboarded: true });
      toast.success("Building registered — training the baseline model.");
      navigate({ to: "/dashboard" });
      return;
    }
    setStep((s) => s + 1);
  };

  return (
    <div className="mesh-bg flex min-h-screen flex-col">
      <header className="flex items-center justify-between px-4 py-4 sm:px-6">
        <Logo />
        <ThemeToggle />
      </header>
      <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
        <ol className="flex items-center gap-2">
          {stepLabels.map((l, i) => (
            <li key={l} className="flex min-w-0 flex-1 items-center gap-2">
              <span
                className={cn(
                  "grid size-7 shrink-0 place-items-center rounded-full border text-xs font-semibold",
                  i < step
                    ? "border-efficiency bg-efficiency text-efficiency-foreground"
                    : i === step
                      ? "border-efficiency text-efficiency"
                      : "border-border text-muted-foreground",
                )}
              >
                {i < step ? <Check className="size-3.5" /> : i + 1}
              </span>
              <span
                className={cn(
                  "hidden truncate text-xs sm:block",
                  i === step ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {l}
              </span>
              {i < stepLabels.length - 1 ? (
                <span
                  className={cn("h-px flex-1", i < step ? "bg-efficiency" : "bg-border")}
                />
              ) : null}
            </li>
          ))}
        </ol>

        <div className="panel mt-8 p-6 sm:p-8">
          {step === 0 ? (
            <div className="space-y-5">
              <div>
                <h1 className="text-xl font-semibold">Add your building</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  Metadata feeds the model: floor area normalises consumption, type sets the
                  occupancy prior.
                </p>
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="bname">Building name</Label>
                  <Input
                    id="bname"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="UBT Campus — Block A"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Building type</Label>
                  <Select value={type} onValueChange={setType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {["School", "Hospital", "Office", "Shopping Center", "Residential"].map((t) => (
                        <SelectItem key={t} value={t}>
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="area">Floor area (m²)</Label>
                  <Input
                    id="area"
                    inputMode="numeric"
                    value={area}
                    onChange={(e) => setArea(e.target.value.replace(/[^\d]/g, ""))}
                    placeholder="8400"
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="addr">Address</Label>
                  <Input
                    id="addr"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="Rr. Rexhep Krasniqi 56, Prishtinë"
                  />
                </div>
              </div>
            </div>
          ) : null}

          {step === 1 ? (
            <div className="space-y-5">
              <div>
                <h1 className="text-xl font-semibold">Connect a data source</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  At least 60 days of readings produce a usable forecast; 12 months captures full
                  seasonality.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setSource("csv")}
                  className={cn(
                    "rounded-2xl border p-5 text-left transition-colors",
                    source === "csv" ? "border-efficiency/60 bg-efficiency/10" : "border-border hover:bg-muted",
                  )}
                >
                  <FileSpreadsheet className="size-6 text-efficiency" />
                  <p className="mt-3 font-semibold">Upload CSV</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    timestamp, kwh, temperature, humidity, occupants
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => setSource("sensor")}
                  className={cn(
                    "rounded-2xl border p-5 text-left transition-colors",
                    source === "sensor"
                      ? "border-efficiency/60 bg-efficiency/10"
                      : "border-border hover:bg-muted",
                  )}
                >
                  <Radio className="size-6 text-efficiency" />
                  <p className="mt-3 font-semibold">Connect sensor gateway</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Modbus / MQTT bridge — simulated in demo mode
                  </p>
                </button>
              </div>
              {source ? (
                <div className="rounded-xl border border-border bg-surface-2/60 p-4 font-mono text-[11px] text-muted-foreground">
                  {source === "csv"
                    ? "› parsed 18,240 rows · 2025-01-01 → 2025-12-31 · 4 missing intervals interpolated"
                    : "› gateway handshake ok · 42 sensors discovered · streaming at 15-min interval"}
                </div>
              ) : null}
            </div>
          ) : null}

          {step === 2 ? (
            <div className="space-y-6">
              <div>
                <h1 className="text-xl font-semibold">Set your savings goal</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  The optimizer ranks recommendations against this target and flags anything that
                  risks comfort.
                </p>
              </div>
              <div className="rounded-2xl border border-border bg-surface-2/50 p-6">
                <div className="flex items-end justify-between">
                  <span className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Target className="size-4 text-efficiency" /> Annual reduction target
                  </span>
                  <span className="stat-number text-3xl font-bold text-efficiency">{goal[0]}%</span>
                </div>
                <Slider
                  value={goal}
                  onValueChange={setGoal}
                  min={3}
                  max={30}
                  step={1}
                  className="mt-6"
                />
                <p className="mt-4 text-xs text-muted-foreground">
                  Estimated annual saving at 0.132 €/kWh:{" "}
                  <span className="text-foreground">
                    €{(Number(area || 8400) * 0.11 * (goal[0]! / 100) * 12).toFixed(0)}
                  </span>
                </p>
              </div>
              <div className="flex items-start gap-3 rounded-xl border border-efficiency/30 bg-efficiency/8 p-4">
                <Cpu className="mt-0.5 size-5 shrink-0 text-efficiency" />
                <p className="text-sm text-muted-foreground">
                  A baseline Random Forest trains immediately; the LSTM takes about 8 minutes and
                  replaces it automatically if it wins on held-out RMSE.
                </p>
              </div>
            </div>
          ) : null}

          <div className="mt-8 flex items-center justify-between gap-3">
            <Button
              variant="ghost"
              onClick={() => (step === 0 ? navigate({ to: "/login" }) : setStep((s) => s - 1))}
            >
              Back
            </Button>
            <Button variant="energy" size="lg" onClick={next}>
              {step === 2 ? "Finish setup" : "Continue"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
