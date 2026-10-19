import { createFileRoute } from "@tanstack/react-router";
import { PublicLayout } from "@/components/public-layout";
import { Panel } from "@/components/ui-kit";
import { ModelPerformance, FeatureImportance } from "@/components/research-dashboard";
export const Route = createFileRoute("/about")({
  head: () => ({ meta: [{ title: "About the prototype | SmartEnergyAI" }, {name: "description", content: "UCI Appliances Energy Prediction research: chronological validation, held-out test evaluation and forecast-based decision support."}] }),
  component: AboutPage,
});
function AboutPage() {
  return <PublicLayout><section className="mesh-bg border-b border-border"><div className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
    <p className="font-mono text-xs tracking-widest text-efficiency uppercase">Bachelor thesis research prototype</p><h1 className="mt-4 text-4xl font-bold">Forecasting with evidence</h1>
    <p className="mt-4 max-w-2xl text-muted-foreground">Artificial Intelligence for Prediction and Optimization of Energy Consumption in Smart Buildings. Optimization here means forecast-based decision support, not physical building control.</p>
  </div></section><section className="mx-auto max-w-7xl space-y-6 px-4 py-12 sm:px-6">
    <div className="grid gap-4 lg:grid-cols-2"><Panel title="Research scope"><div className="space-y-4 text-sm text-muted-foreground">
      <p>The UCI Appliances Energy Prediction dataset supplies historical observations from one building. The task is one-step-ahead Appliances energy prediction in Wh, ten minutes after the forecast origin.</p>
      <p>Chronological training and validation support model development. Final model selection precedes the selected model's held-out test evaluation. Preprocessing and feature timing avoid future observations in predictors.</p>
      <p>Persistence, Linear Regression, Random Forest and XGBoost were considered. The dashboard separates validation comparisons from final held-out test performance.</p>
    </div></Panel><Panel title="Prototype limitations"><div className="space-y-4 text-sm text-muted-foreground">
      <p>No operational sensor stream is connected. Valid forecasts require already-engineered readings with genuine historical lag and rolling context.</p>
      <p>No occupancy measurements, equipment-specific controls, calibrated prediction intervals, savings calculations, authentication service or database are provided.</p>
      <p>Feature importance describes predictive behavior and does not establish causal effects or intervention savings.</p>
    </div></Panel></div><ModelPerformance /><FeatureImportance />
  </section></PublicLayout>;
}
