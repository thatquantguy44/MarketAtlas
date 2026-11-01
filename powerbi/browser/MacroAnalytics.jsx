import React from "react";
import { Button, DataComponent, DataTable, Dropdown, EvidenceChart, Section,
  SortableItem, SortableRegion, useDataApp, useSectionFilters } from "../../data-app-public.jsx";
import { atDate, dateLabel, historyThrough, isSupported, numberLabel, queryId,
  rankNodes, statusLabel, symmetricPairs, windowEvidence } from "./macroAnalytics.mjs";

const numeric = (field, label) => ({field, label, renderCell: numberLabel});
const status = (field, label) => ({field, label, renderCell: statusLabel});
const dated = (field, label) => ({field, label, renderCell: dateLabel});

export function MacroAnalytics() {
  const { reviewedRows } = useDataApp();
  const groups = reviewedRows(queryId("groups"));
  return groups.length ? <ResearchViews groups={groups}/> :
    <p role="status">No validated analytics pack is attached to this report. Attach a macro research pack using the report refresh runbook.</p>;
}

function ResearchViews({groups}) {
  const groupScope = useSectionFilters([{id:"group", label:"Economic group", field:"group_id",
    defaultValue:groups.find(g=>g.group_id==="treasury_yields")?.group_id || groups[0].group_id,
    queryIds:[queryId("groups"),queryId("relationships"),queryId("dispersion"),queryId("nodes"),queryId("evidence")]}], {}, {id:"macro-research-group"});
  const group = groups.find(g=>g.group_id===groupScope.values.group);
  const controls = <Dropdown label="Economic group" showLabel value={groupScope.values.group}
    choices={groups.map(g=>g.group_id)} choiceLabels={Object.fromEntries(groups.map(g=>[g.group_id,g.group_label]))}
    onChange={value=>groupScope.setFilter("group",value)}/>;
  return group ? <GroupResearch key={group.group_id} group={group} groupControl={controls}/> :
    <Section id="macro-research-select" title="Relationship research" filters={controls}><p>Select a single economic group.</p></Section>;
}

function GroupResearch({group, groupControl}) {
  const { reviewedRows } = useDataApp();
  const detailRef = React.useRef(null);
  const id = group.group_id;
  const members = JSON.parse(group.members_json);
  const allDispersion = reviewedRows(queryId("dispersion")).filter(r=>r.group_id===id);
  const dates = allDispersion.map(r=>r.knowledge_date).sort();
  const dateScope = useSectionFilters([{id:"date",label:"Known by",field:"knowledge_date",defaultValue:dates.at(-1),
    queryIds:[queryId("relationships"),queryId("dispersion"),queryId("nodes"),queryId("evidence")]}], {}, {id:`macro-research-date:${id}`});
  const date = dateScope.values.date;
  const pairs = atDate(reviewedRows(queryId("relationships")), id, date);
  const nodes = atDate(reviewedRows(queryId("nodes")), id, date);
  const evidence = atDate(reviewedRows(queryId("evidence")), id, date);
  const timeline = historyThrough(allDispersion, id, date);
  const current = allDispersion.find(r=>r.knowledge_date===date);
  const pairScope = useSectionFilters([{id:"pair",label:"Pair",field:"pair_key",defaultValue:pairs[0]?.pair_key,
    queryIds:[queryId("relationships")]}], {}, {id:`macro-research-pair:${id}`});
  const pair = pairs.find(r=>r.pair_key===pairScope.values.pair) || pairs[0];
  const pointIndex = new Map(reviewedRows(queryId("points")).map(p=>[p.point_id,p]));
  const window = windowEvidence(evidence, pointIndex, pair);
  const selectedEvidence = evidence.filter(r=>r.series_id===pair?.series_low_id || r.series_id===pair?.series_high_id);
  const ranked = rankNodes(nodes);
  const completeDate = timeline.filter(isSupported).at(-1)?.knowledge_date;
  const scopeFilters = [{field:"group_id",label:"Economic group",value:id},
    {field:"knowledge_date",label:"Known by",value:date}];
  const pairLabels = Object.fromEntries(pairs.map(p=>[p.pair_key,`${p.series_low_id} / ${p.series_high_id}`]));
  const inspect = row => [{label:"Inspect pair observations", onSelect:()=>{
    pairScope.setFilter("pair",row.pair_key);
    requestAnimationFrame(()=>detailRef.current?.scrollIntoView({block:"start"}));
  }}];
  const rowOrder = members.map(m=>m.series_id);
  const blocks = [
    {id:"macro-relationship-heatmap", title:"Relationships", span:6, content:
      <EvidenceChart id="macro-relationship-heatmap" variant="card" queryId={queryId("relationships")}
        title="Relationship heatmap" sourceRows={pairs} displayRows={symmetricPairs(pairs)} rows={symmetricPairs(pairs)}
        scopeFilters={scopeFilters} height={360}
        spec={{type:"heatmap",x:"column",series:"row",y:"correlation",colorDomain:[-1,1],
          showValues:true,missingValues:"gap",reverseRows:false,valueDecimals:3,categoryOrder:rowOrder,seriesOrder:rowOrder,
          tooltipFields:[{field:"paired_count",label:"Paired changes"},{field:"window_count",label:"Window periods"},
            {field:"distance",label:"Distance"},{field:"distance_change",label:"Distance change"},{field:"estimate_status",label:"Status"}]}}
        chartOptions={{getMarkActions:({row})=>inspect(row)}}>
        <p data-editable-id="macro-heatmap-definition" data-editable-narrative>
          Correlation runs from −1 (opposite movement) to +1 (moving together). Self-comparisons are omitted; gaps are unavailable estimates.
        </p>
        <p data-reviewed-rows>{pairs.filter(isSupported).length} of {pairs.length} pairs supported · {group.minimum_pairs} paired changes required in {group.window} {group.frequency==="m"?"months":"weekdays"}.</p>
      </EvidenceChart>},
    {id:"macro-dispersion-timeline", title:"Dispersion over time", span:6, content:
      <EvidenceChart id="macro-dispersion-timeline" variant="card" queryId={queryId("dispersion")}
        title="Dispersion timeline" sourceRows={timeline} displayRows={timeline} rows={timeline}
        scopeFilters={[scopeFilters[0],{field:"knowledge_date",label:"History through",value:date}]} height={360}
        spec={{type:"line",x:"knowledge_date",y:"dispersion",valueDecimals:3,stackable:false,colors:{dispersion:"var(--chart-1)"}}}>
        <p data-editable-id="macro-dispersion-definition" data-editable-narrative>
          Dispersion measures disagreement among standardized changes: each indicator is compared with its own preceding baseline. Higher values mean more disagreement, in standardized units.
        </p>
        <p data-reviewed-rows>{isSupported(current) ? `Selected-date dispersion: ${numberLabel(current.dispersion)}.` :
          `Selected-date dispersion unavailable: ${current?.usable_member_count ?? 0} of ${members.length} members have usable standardized changes.`} No lines bridge unavailable evaluations.</p>
        {!isSupported(current) && completeDate && <Button onClick={()=>dateScope.setFilter("date",completeDate)}>View latest complete date: {dateLabel(completeDate)}</Button>}
      </EvidenceChart>},
    {id:"macro-node-divergence", title:"Indicator divergence", span:12, content:
      <EvidenceChart id="macro-node-divergence" variant="card" queryId={queryId("nodes")}
        title="Indicator divergence ranking" sourceRows={nodes} displayRows={ranked} rows={ranked}
        scopeFilters={scopeFilters} height={250}
        spec={{type:"horizontalBar",x:"series_id",y:"divergence",sortOrder:"descending",valueDecimals:3,stackable:false}}>
        <p data-editable-id="macro-divergence-definition" data-editable-narrative>
          Absolute distance from the complete group's mean standardized change. Larger values identify indicators disagreeing most with their group; they do not establish a forecast.
        </p>
        {!ranked.length && <p role="status">Ranking unavailable for this date. Every configured group member must have a usable standardized change.</p>}
        <details><summary>Series values and availability</summary>
          <DataTable rows={nodes} label="Indicator values and availability" searchable={false}
            columns={[{field:"series_id",label:"Series"},numeric("zscore","Standardized change"),
              numeric("deviation_from_group_mean","Deviation from mean"),numeric("mean_peer_distance","Mean peer distance"),
              status("zscore_status","Availability"),{field:"baseline_count",label:"Baseline changes"}]}/>
        </details>
      </EvidenceChart>},
    {id:"macro-pair-details", title:"Pair evidence", span:12, kind:"table", content:
      <div ref={detailRef}><DataComponent id="macro-pair-details" variant="card" kind="table" queryId={queryId("points")}
        queryIds={[queryId("points"),queryId("relationships"),queryId("evidence")]}
        sourceRowsByQuery={{[queryId("points")]:window.points,[queryId("relationships")]:pair?[pair]:[],[queryId("evidence")]:selectedEvidence}}
        displayRows={window.rows} title="Pair evidence" scopeFilters={scopeFilters}
        headerControls={<Dropdown label="Inspect pair" value={pair?.pair_key} choices={pairs.map(p=>p.pair_key)}
          choiceLabels={pairLabels} onChange={value=>pairScope.setFilter("pair",value)}/>}>
        {pair ? <div data-reviewed-rows>
          <p>{pair.series_low_id} / {pair.series_high_id} · {dateLabel(pair.reference_start)}–{dateLabel(pair.reference_end)} ·
            {pair.paired_count}/{pair.window_count} paired changes · {statusLabel(pair.estimate_status)}.</p>
          <p>Correlation {numberLabel(pair.correlation)} · distance {numberLabel(pair.distance)} ·
            distance change {numberLabel(pair.distance_change)} ({statusLabel(pair.distance_change_status)};
            comparison {dateLabel(pair.comparison_knowledge_date)}).</p>
          <p data-editable-id="macro-distance-definition" data-editable-narrative>Distance converts correlation to a 0–2 scale: lower means more similar movement; higher means more opposing movement.</p>
          <DataTable rows={window.rows} label="Aligned transformed pair observations"
            columns={[dated("reference_period","Reference period"),numeric("left_value",pair.series_low_id),
              numeric("right_value",pair.series_high_id),status("left_status",`${pair.series_low_id} status`),
              status("right_status",`${pair.series_high_id} status`),
              {field:"left_source_records",label:`${pair.series_low_id} source records`},
              {field:"right_source_records",label:`${pair.series_high_id} source records`}]}/>
          <details><summary>Baseline and availability diagnostics</summary>
            <DataTable rows={selectedEvidence} label="Pair baseline diagnostics" searchable={false}
              columns={[{field:"series_id",label:"Series"},{field:"usable_change_count",label:"Usable window changes"},
                {field:"baseline_count",label:"Baseline changes"},numeric("baseline_mean","Baseline mean"),numeric("baseline_sd","Baseline SD"),
                {field:"point_status_counts",label:"Window availability"},status("zscore_status","Standardization status")]}/>
          </details>
        </div> : <p role="status">No pair evaluation is available for this selection.</p>}
      </DataComponent></div>},
  ];
  return <>
    <DataComponent id="macro-research-provenance" queryId={queryId("groups")} kind="table" title="Research pack" sourceRows={[group]} displayRows={[group]}>
      <p data-reviewed-rows>Analysis cutoff {dateLabel(group.as_of)} · captured {new Date(group.captured_at).toLocaleString(undefined,{timeZoneName:"short"})}.
        This independent research pack is retained separately from the daily publication refresh.</p>
    </DataComponent>
    <Section id="macro-research-section" title="Relationships and disagreement" filters={<>
      {groupControl}<Dropdown label="Known by" showLabel searchable value={date} choices={dates} formatChoice={dateLabel}
        onChange={value=>dateScope.setFilter("date",value)}/>
      <Button onClick={()=>dateScope.setFilter("date",dates.at(-1))}>Latest date</Button>
    </>}>
      <p data-editable-id={`macro-method:${id}`} data-editable-narrative>
        {group.frequency==="m" ? "Monthly changes; " : "Daily yield changes on a conservative weekday grid; "}
        {members.every(m=>m.transform==="log_change") ? "100 × log changes in positive price indexes, without annualizing." : "percentage-point changes."}
        {members.some(m=>m.orientation===-1) && " Unemployment measures are inverted so positive changes indicate strengthening labor conditions."}
        {` Baselines use ${group.baseline} preceding changes, requiring ${group.minimum_baseline}. Source dates have day precision.`}
      </p>
      <details><summary>Group members and transformations</summary><ul>{members.map(m=><li key={m.series_id}>
        <strong>{m.series_id}</strong> — {m.label}; {statusLabel(m.transform)}, orientation {m.orientation>0?"+1":"−1"}.
      </li>)}</ul></details>
      <SortableRegion id="macro-research-canvas" variant="canvas" columns={12} spacing="standard"
        rows={[{id:"row:macro-research-charts",items:blocks.slice(0,2).map(b=>b.id)},
          ...blocks.slice(2).map(b=>({id:`row:${b.id}`,items:[b.id]}))]}>
        {blocks.map(block=><SortableItem key={block.id} id={block.id} label={block.title} kind={block.kind||"chart"} span={block.span}>{block.content}</SortableItem>)}
      </SortableRegion>
    </Section>
  </>;
}
