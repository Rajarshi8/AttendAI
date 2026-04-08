import Link from "next/link";
import { Activity, Camera, ShieldCheck, Users } from "lucide-react";

import { AuthPanel } from "@/components/AuthPanel";

const features = [
  {
    icon: Camera,
    title: "AI Face Capture",
    description: "Capture 10-20 samples and generate a stable averaged embedding per user.",
  },
  {
    icon: Activity,
    title: "Live Recognition",
    description: "Real-time matching with cosine similarity and stride-based frame optimization.",
  },
  {
    icon: ShieldCheck,
    title: "Basic Liveness",
    description: "Head movement check to reduce spoofing from static images.",
  },
  {
    icon: Users,
    title: "Admin Insights",
    description: "Search, filter, export CSV, and monitor attendance logs in one place.",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <section className="animate-rise rounded-3xl border border-border bg-panel p-6 shadow-glow md:p-10">
        <p className="text-sm uppercase tracking-[0.2em] text-muted">Production-ready suite</p>
        <h1 className="mt-3 text-3xl font-bold leading-tight md:text-5xl">Face Recognition Attendance System</h1>
        <p className="mt-4 max-w-3xl text-muted md:text-lg">
          Register users with robust embeddings, run real-time recognition with liveness checks, and maintain clean attendance records with duplicate prevention.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/register" className="rounded-full bg-accent px-5 py-2.5 font-semibold text-accent-foreground">
            Register User
          </Link>
          <Link href="/attendance" className="rounded-full border border-border px-5 py-2.5 font-semibold">
            Start Attendance
          </Link>
          <Link href="/admin" className="rounded-full border border-border px-5 py-2.5 font-semibold">
            Open Admin
          </Link>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {features.map(({ icon: Icon, title, description }) => (
          <article key={title} className="animate-rise rounded-2xl border border-border bg-panel p-5">
            <Icon className="h-6 w-6" />
            <h2 className="mt-3 text-xl font-semibold">{title}</h2>
            <p className="mt-2 text-muted">{description}</p>
          </article>
        ))}
      </section>

      <AuthPanel />
    </div>
  );
}
