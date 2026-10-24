import { fixtureReportSnapshot, type ReportSnapshot } from "@/data/reportSnapshot";

/**
 * Demo adapter. A production server route will replace this fixture with the
 * T-011 `atlas_report.current_*` views; browser code never connects to Postgres.
 */
export async function loadReportSnapshot(): Promise<ReportSnapshot> {
  return fixtureReportSnapshot;
}
