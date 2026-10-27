# Operations and recovery handoff

Status: manual local demonstration only. There is no scheduler, alert channel,
or production service in scope. Do not represent this document as an operating
runbook for a scheduled pilot.

## Responsibility record

| Responsibility | Current status | Required before scheduling |
| --- | --- | --- |
| Local demo execution | Josh / project owner | Define a separate operator if scheduling is introduced |
| Upstream data rights and freshness | Josh / source and data owner; restricted internal-only | Document any external-provider terms before non-local sharing |
| Target PostgreSQL ownership | Josh / database owner | Define backup/restore authority and migration window before scheduling |
| Report/API ownership | Josh / report owner | Define host, consumers/SLA, and access review before scheduling |
| Quant methodology | Josh / methodology owner | Record method-change approval before analytical expansion |
| Incident and alert recipient | Josh / incident owner | Define alert destination and on-call/escalation path before scheduling |

This assignment is limited to the manual local pilot. It does not authorize
external redistribution or replace any third-party source terms.

## Safe manual refresh

1. Confirm the source contract still validates before an adapter run.
2. Run the extraction/publish command for the selected approved interface.
3. Run the appropriate validation, then `market-atlas release validate --samples 20` for the local release envelope.
4. Record publication name, snapshot ID, input manifest ID, command outcome,
   and any quarantines in an authorized incident/run record.
5. Expose results only through snapshot-pinned `atlas_report` views. Never
   point browser code at `macro_medallion`, and never write to `meta`,
   `silver`, `gold`, `bronze`, or `audit`.

For the public fixture, the exercised no-database commands are in
[contributor-demo.md](contributor-demo.md). This project has no configured
automatic refresh cadence.

For the restricted quality publication, extract only the configured approved IDs,
then run `revision-quality publish --input <ignored-extract-path>`. It writes
captured versions and report rows in dedicated schemas, retaining the original
manifest. Reusing the same extract and implementation reuses its snapshot. A
fresh capture receives a new manifest even when its metrics are unchanged.
Snapshot materialization failures retain a safe stage/type diagnostic and leave
the prior pointer unchanged; correcting the issue and replaying the same input
retries that failed build. Previously superseded snapshots are returned as
retained snapshots and are not silently republished. Graph and fixture pointers
are independent. The workspace displays the quality capture/publication times;
it has no automated freshness SLA or historical source-availability claim.

## Failure and recovery

The publication contract is atomic: a failed build must not move the current
publication pointer. T-013 demonstrated this for the fixture build. On a
failure, the responsible operator must:

1. Stop the manual/scheduled trigger and preserve the failure output; do not
   retry by editing upstream data.
2. Identify the last validated snapshot for the affected publication and keep
   consumers pinned to it. Record its as-of/published time and mark downstream
   output stale if a freshness expectation exists.
3. Correct the configuration, contract, or code in an isolated/reviewed change;
   rerun validation before publishing a new snapshot.
4. If a rollback is explicitly approved by the future database owner, use the
   existing atomic publication function against a known validated snapshot in a
   transaction. Do not change source schemas and do not delete failed evidence.

```sql
BEGIN;
SELECT atlas.publish_serving_snapshot('macro_economic_graph',
  '<known-validated-serving-snapshot-uuid>'::uuid);
COMMIT;
```

The SQL is a controlled database-owner action, not a browser or source-reader
operation. Select the publication name and snapshot only from retained
validated records; a migration rollback is not a substitute for repointing the
publication. Before any scheduler is enabled, rehearse this procedure in an
isolated environment with named owners and an alert destination.
