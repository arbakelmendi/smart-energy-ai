import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { BookOpenCheck, Clock, Github, LifeBuoy, Mail, MapPin } from "lucide-react";
import { PublicLayout } from "@/components/public-layout";
import { SectionHeading } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const Route = createFileRoute("/contact")({
  head: () => ({
    meta: [
      { title: "Contact & support — Smart Energy AI" },
      {
        name: "description",
        content:
          "Reach the Smart Energy AI research team for pilot enquiries, dataset questions or technical support.",
      },
      { property: "og:title", content: "Contact & support — Smart Energy AI" },
      { property: "og:description", content: "Pilot enquiries, dataset access and support." },
    ],
  }),
  component: ContactPage,
});

function ContactPage() {
  const [topic, setTopic] = useState("Pilot enquiry");
  const [sent, setSent] = useState(false);

  return (
    <PublicLayout>
      <section className="mesh-bg border-b border-border">
        <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6">
          <SectionHeading
            eyebrow="contact"
            title="Talk to the research team"
            description="Pilot enquiries, dataset access requests, thesis questions and technical support all land in the same inbox — usually answered within one working day."
          />
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_360px]">
        <div className="panel p-6 sm:p-8">
          {sent ? (
            <div className="py-10 text-center">
              <span className="mx-auto grid size-12 place-items-center rounded-2xl border border-efficiency/40 bg-efficiency/10">
                <BookOpenCheck className="size-6 text-efficiency" />
              </span>
              <h2 className="mt-5 text-xl font-semibold">Message received</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Ticket #SEA-2026-0417 opened. We'll reply to your address shortly.
              </p>
              <Button variant="wire" className="mt-6" onClick={() => setSent(false)}>
                Send another message
              </Button>
            </div>
          ) : (
            <form
              className="space-y-5"
              onSubmit={(e) => {
                e.preventDefault();
                const form = new FormData(e.currentTarget);
                const email = String(form.get("email") ?? "");
                const message = String(form.get("message") ?? "");
                if (!email.includes("@") || message.trim().length < 20) {
                  toast.error("A valid email and at least 20 characters of context are required.");
                  return;
                }
                setSent(true);
                toast.success("Message sent to the research team.");
              }}
            >
              <div className="grid gap-5 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="cname">Name</Label>
                  <Input id="cname" name="name" placeholder="Elira Hoxha" maxLength={100} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cemail">Email</Label>
                  <Input
                    id="cemail"
                    name="email"
                    type="email"
                    placeholder="you@organisation.org"
                    maxLength={255}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="corg">Organisation</Label>
                  <Input id="corg" name="org" placeholder="Regional Hospital" maxLength={120} />
                </div>
                <div className="space-y-2">
                  <Label>Topic</Label>
                  <Select value={topic} onValueChange={setTopic}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[
                        "Pilot enquiry",
                        "Dataset / research access",
                        "Technical support",
                        "Thesis / academic question",
                      ].map((t) => (
                        <SelectItem key={t} value={t}>
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="cmsg">How can we help?</Label>
                <Textarea
                  id="cmsg"
                  name="message"
                  rows={6}
                  maxLength={1000}
                  placeholder="Building type, floor area, how much historical data you have, and what you want to forecast…"
                />
              </div>
              <Button type="submit" variant="energy" size="lg">
                Send message
              </Button>
            </form>
          )}
        </div>

        <aside className="space-y-4">
          {[
            { icon: Mail, k: "Email", v: "research@smart-energy-ai.dev" },
            { icon: LifeBuoy, k: "Support SLA", v: "1 working day · Mon–Fri" },
            { icon: MapPin, k: "Campus", v: "UBT Innovation Campus, Lipjan, Kosovo" },
            { icon: Clock, k: "Office hours", v: "09:00 – 17:00 CET" },
            { icon: Github, k: "Repository", v: "github.com/smart-energy-ai" },
          ].map((i) => (
            <div key={i.k} className="panel flex items-start gap-3 p-4">
              <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-surface-2 text-efficiency">
                <i.icon className="size-4.5" strokeWidth={1.9} />
              </span>
              <div className="min-w-0">
                <p className="font-mono text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
                  {i.k}
                </p>
                <p className="mt-0.5 text-sm break-words">{i.v}</p>
              </div>
            </div>
          ))}
        </aside>
      </section>
    </PublicLayout>
  );
}
