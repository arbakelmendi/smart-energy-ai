import { createFileRoute, Link } from "@tanstack/react-router";
import { PublicLayout } from "@/components/public-layout";
import { Panel } from "@/components/ui-kit";
export const Route = createFileRoute("/contact")({head: () => ({meta: [{title: "Contact | SmartEnergyAI prototype"}, {name: "description", content: "Contact delivery is not connected in this research prototype."}]}), component: ContactPage});
function ContactPage() {
  return <PublicLayout><section className="mx-auto w-full max-w-4xl px-4 py-16 sm:px-6"><h1 className="mb-6 text-3xl font-semibold">Contact availability</h1><Panel title="Contact delivery not connected" subtitle="Research prototype">
    <p className="text-sm text-muted-foreground">This prototype does not send contact messages or provide a support service. No message has been submitted, and no account or pilot installation is required to inspect the research results.</p>
    <Link to="/dashboard" className="mt-5 inline-block text-sm text-efficiency underline">View verified research results</Link>
  </Panel></section></PublicLayout>;
}
