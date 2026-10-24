import { Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/shell/AppShell";
import { CorrelationsPage } from "@/app/CorrelationsPage";
import { MacroContextPage } from "@/app/MacroContextPage";
import { MarketMapPage } from "@/app/MarketMapPage";
import { OverviewPage } from "@/app/OverviewPage";
import { ProvenancePage } from "@/app/ProvenancePage";

export function App() {
  return <Routes><Route element={<AppShell />}><Route index element={<OverviewPage />} /><Route path="market-map" element={<MarketMapPage />} /><Route path="macro-context" element={<MacroContextPage />} /><Route path="correlations" element={<CorrelationsPage />} /><Route path="provenance" element={<ProvenancePage />} /></Route></Routes>;
}
