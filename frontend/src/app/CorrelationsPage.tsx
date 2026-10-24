import { StatusPill } from "@/components/ui/StatusPill";
import { fixtureReportSnapshot } from "@/data/reportSnapshot";
import { useDemoStore } from "@/lib/demoStore";

function CorrelationSparkline() {
  const values = fixtureReportSnapshot.correlations.filter((item) => item.correlation !== null).map((item) => item.correlation ?? 0);
  const points = values.map((value, index) => `${index * 60},${90 - ((value - 0.98) / 0.02) * 70}`).join(" ");
  return <svg aria-label="Synthetic Alpha and Beta correlation history" className="h-28 w-full" role="img" viewBox="0 0 240 100"><path d="M0 90H240" stroke="#26262B" /><polyline fill="none" points={points} stroke="#FFB400" strokeWidth="3" /></svg>;
}

export function CorrelationsPage() {
  const selectSubject = useDemoStore((state) => state.selectSubject);
  const correlations = fixtureReportSnapshot.correlations;
  return <section className="space-y-6"><div><p className="eyebrow">Rolling Pearson correlation</p><h2 className="mt-2 text-3xl font-semibold">Configured comparable pairs</h2><p className="mt-2 text-term-muted">Simple adjusted-close returns, a fixed 60-session window, and at least 45 paired observations. No forward fill or window expansion.</p></div><div className="panel rounded p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-semibold">Synthetic Alpha / Synthetic Beta</p><p className="mt-1 font-mono text-xs text-term-muted">rolling-pearson-simple-return-v1</p></div><StatusPill tone="green">supported</StatusPill></div><CorrelationSparkline /><div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4"><p><span className="block text-term-muted">Latest</span><strong>0.9945</strong></p><p><span className="block text-term-muted">Paired returns</span><strong>55</strong></p><p><span className="block text-term-muted">Window</span><strong>60 sessions</strong></p><p><span className="block text-term-muted">Cutoff</span><strong>Current context</strong></p></div></div><div className="panel overflow-hidden rounded"><table className="w-full text-left text-sm"><thead className="bg-term-panel2 font-mono text-xs uppercase text-term-muted"><tr><th className="p-4">Endpoint</th><th className="p-4">Pair</th><th className="p-4">Correlation</th><th className="p-4">Sample</th><th className="p-4">Status</th></tr></thead><tbody>{correlations.map((correlation) => <tr key={correlation.id} className="border-t border-term-border"><td className="p-4 font-mono text-xs">{correlation.endpoint}</td><td className="p-4"><button className="text-left hover:text-term-gold" onClick={() => selectSubject(correlation.id)}>{correlation.pair}</button></td><td className="p-4 font-mono">{correlation.correlation?.toFixed(4) ?? "—"}</td><td className="p-4">{correlation.pairedReturns}</td><td className="p-4"><StatusPill tone={correlation.status === "supported" ? "green" : "amber"}>{correlation.status.replace("_", " ")}</StatusPill></td></tr>)}</tbody></table></div></section>;
}
