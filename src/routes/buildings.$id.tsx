import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { BuildingDetailContent } from "@/components/building-management";
export const Route = createFileRoute("/buildings/$id")({
  head: () => ({meta:[{title:"Building details | SmartEnergyAI"}]}), component: BuildingDetail,
});
function BuildingDetail() { const {id}=Route.useParams(); return <AppShell title="Building details" subtitle="Persisted metadata for your account"><BuildingDetailContent value={id} /></AppShell>; }
