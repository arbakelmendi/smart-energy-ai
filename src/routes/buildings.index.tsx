import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { BuildingsList } from "@/components/building-management";
export const Route = createFileRoute("/buildings/")({
  head: () => ({meta:[{title:"Your buildings | SmartEnergyAI"}]}), component: BuildingsPage,
});
function BuildingsPage() { return <AppShell title="Buildings" subtitle="Manage your persisted building metadata"><BuildingsList /></AppShell>; }
