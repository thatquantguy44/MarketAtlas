import { StatusPill } from "@/components/ui/StatusPill";
import { fixtureReportSnapshot } from "@/data/reportSnapshot";
import { useDemoStore } from "@/lib/demoStore";

export function MacroContextPage() {
  const selectSubject = useDemoStore((state) => state.selectSubject);
  return <section className="space-y-6"><div><p className="eyebrow">Curated macro context</p><h2 className="mt-2 text-3xl font-semibold">Synthetic Growth Index</h2><p className="mt-2 text-term-muted">Mappings are explanatory context. They never express measured sensitivity or causality.</p></div><div className="grid gap-4 lg:grid-cols-3">{fixtureReportSnapshot.contexts.map((context) => <article key={context.id} className="panel rounded p-5"><div className="flex items-start justify-between gap-3"><p className="font-mono text-xs text-term-gold">{context.kind}</p><StatusPill tone={context.basis === "source_backed" ? "green" : "amber"}>{context.basis}</StatusPill></div><h3 className="mt-4 text-xl font-semibold">{context.target}</h3><p className="mt-3 text-sm text-term-muted">{context.rationale}</p><p className="mt-4 rounded bg-amber-950 p-3 text-xs text-term-gold">{context.label}</p><dl className="mt-4 space-y-2 text-xs"><div className="flex justify-between gap-3"><dt className="text-term-muted">Owner</dt><dd>{context.owner}</dd></div><div className="flex justify-between gap-3"><dt className="text-term-muted">Evidence</dt><dd><button className="font-mono text-term-amber" onClick={() => selectSubject(context.id)}>{context.sourceRecord}</button></dd></div></dl></article>)}</div></section>;
}
