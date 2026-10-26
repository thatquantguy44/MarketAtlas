import { useState } from "react";
import { KnowledgeGraphWorkspace } from "@/app/KnowledgeGraphWorkspace";
import { LiveMacroGraph } from "@/app/LiveMacroGraph";

export function App() {
  const [mode, setMode] = useState<"fixture" | "live">("fixture");
  return <>
    <div className="fixed right-5 top-5 z-50 flex gap-1 rounded-lg border border-slate-700 bg-slate-950/95 p-1 text-xs shadow-lg"><button type="button" className={`rounded px-3 py-2 ${mode === "fixture" ? "bg-sky-900 text-white" : "text-slate-300"}`} onClick={() => setMode("fixture")}>Fixture graph</button><button type="button" className={`rounded px-3 py-2 ${mode === "live" ? "bg-emerald-900 text-white" : "text-slate-300"}`} onClick={() => setMode("live")}>Live macro graph</button></div>
    {mode === "fixture" ? <KnowledgeGraphWorkspace /> : <LiveMacroGraph />}
  </>;
}
