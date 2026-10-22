import { useState } from "react";
import {
  ModelPerformance,
  ValidationComparison,
  FeatureImportance,
  RecommendationBands,
} from "@/components/research-dashboard";
export function ResearchInformation() {
  const [open, setOpen] = useState(false);
  return (
    <details
      data-research-information
      className="panel p-5"
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary className="cursor-pointer font-semibold">Model / Research Information</summary>
      <p className="my-4 text-sm text-muted-foreground">
        Research evaluation on the UCI reference dataset. These results are not operational
        measurements or accuracy estimates for your selected building.
      </p>
      {open ? (
        <div className="space-y-5">
          <ModelPerformance />
          <ValidationComparison />
          <FeatureImportance />
          <RecommendationBands />
        </div>
      ) : null}
    </details>
  );
}
