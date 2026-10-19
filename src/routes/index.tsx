import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Brain, Clock, Lightbulb } from "lucide-react";
import { PublicLayout } from "@/components/public-layout";
import { EnergyWave } from "@/components/energy-wave";
import { Button } from "@/components/ui/button";
import heroImage from "@/assets/hero-control-room.jpg";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "SmartEnergyAI | Energy forecasting research prototype" },
    { name: "description", content: "Appliances energy forecasting and transparent decision support. Verified research results; no operational sensor feed connected." }] }),
  component: HomePage,
});
function HomePage() {
  return <PublicLayout>
    <section className="mesh-bg relative overflow-hidden border-b border-border">
      <img src={heroImage} alt="Illustrative building control room; not a connected installation" className="absolute inset-0 h-full w-full object-cover opacity-15" />
      <EnergyWave className="absolute inset-x-0 bottom-0 h-40 opacity-30" />
      <div className="relative mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:py-32">
        <p className="font-mono text-xs tracking-widest text-efficiency uppercase">Academic research prototype</p>
        <h1 className="mt-5 max-w-3xl text-4xl font-bold leading-tight sm:text-6xl">Understand energy forecasts.<br />Review decisions with evidence.</h1>
        <p className="mt-6 max-w-xl text-muted-foreground">Explore verified Appliances energy forecasting results and transparent recommendations. Live building measurements and automatic equipment control are not connected.</p>
        <div className="mt-8 flex flex-wrap gap-3"><Button asChild variant="energy" size="lg"><Link to="/dashboard">View verified results <ArrowRight className="size-4" /></Link></Button>
          <Button asChild variant="outline" size="lg"><Link to="/about">About the prototype</Link></Button></div>
      </div>
    </section>
    <section className="mx-auto grid max-w-7xl gap-4 px-4 py-16 sm:px-6 lg:grid-cols-3">
      {[{icon: Brain, title: "Verified model results", text: "Validation comparison and the selected model's held-out test performance are available in the research dashboard."},
        {icon: Clock, title: "Short-horizon energy forecasting", text: "The model predicts Appliances energy in Wh, ten minutes ahead. Current readings and valid historical context are required."},
        {icon: Lightbulb, title: "Transparent decision support", text: "Development-calibrated consumption bands guide review of flexible loads. No measured or guaranteed savings are claimed."}].map(item =>
          <article key={item.title} className="panel p-6"><item.icon className="size-6 text-efficiency" /><h2 className="mt-4 text-lg font-semibold">{item.title}</h2><p className="mt-2 text-sm text-muted-foreground">{item.text}</p></article>)}
    </section>
  </PublicLayout>;
}
