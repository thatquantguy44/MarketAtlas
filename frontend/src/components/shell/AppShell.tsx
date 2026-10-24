import { Activity, ChartNoAxesCombined, GitBranch, Network, SearchCheck } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { fixtureReportSnapshot } from "@/data/reportSnapshot";

const navigation = [
  { to: "/", label: "Overview", icon: Activity },
  { to: "/market-map", label: "Market map", icon: Network },
  { to: "/macro-context", label: "Macro context", icon: GitBranch },
  { to: "/correlations", label: "Correlations", icon: ChartNoAxesCombined },
  { to: "/provenance", label: "Provenance", icon: SearchCheck }
];

export function AppShell() {
  return (
    <div className="min-h-screen bg-term-bg text-term-text">
      <header className="border-b border-term-border bg-term-panel px-5 py-3">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div><p className="eyebrow">MarketAtlas / demo terminal</p><h1 className="mt-1 text-lg font-semibold">Temporal market knowledge graph</h1></div>
          <div className="text-right font-mono text-xs text-term-muted"><p>SNAPSHOT {fixtureReportSnapshot.metadata.snapshotId}</p><p>FIXTURE ONLY · {fixtureReportSnapshot.metadata.publishedAt.slice(0, 10)}</p></div>
        </div>
      </header>
      <div className="mx-auto grid max-w-7xl md:grid-cols-[190px_1fr]">
        <nav aria-label="Primary" className="border-b border-term-border bg-term-panel p-3 md:min-h-[calc(100vh-73px)] md:border-b-0 md:border-r">
          <ul className="flex gap-2 overflow-x-auto md:block md:space-y-1">
            {navigation.map(({ to, label, icon: Icon }) => <li key={to}><NavLink end={to === "/"} to={to} className={({ isActive }) => `flex items-center gap-2 whitespace-nowrap rounded px-3 py-2 text-sm ${isActive ? "bg-amber-950 text-term-gold" : "text-term-muted hover:bg-term-panel2 hover:text-term-text"}`}><Icon size={16} />{label}</NavLink></li>)}
          </ul>
        </nav>
        <main className="p-5 md:p-7"><Outlet /></main>
      </div>
    </div>
  );
}
