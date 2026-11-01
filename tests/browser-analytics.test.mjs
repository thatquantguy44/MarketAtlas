import assert from "node:assert/strict";
import test from "node:test";
import {atDate, historyThrough, rankNodes, symmetricPairs, windowEvidence} from "../powerbi/browser/macroAnalytics.mjs";

test("group/date selections never admit future or other-group observations",()=>{
  const rows=[{group_id:"a",knowledge_date:"2024-01-31",dispersion:0},
    {group_id:"a",knowledge_date:"2024-02-29",dispersion:null},
    {group_id:"a",knowledge_date:"2024-03-31",dispersion:2},
    {group_id:"b",knowledge_date:"2024-02-29",dispersion:9}];
  assert.deepEqual(atDate(rows,"a","2024-02-29"),[rows[1]]);
  assert.deepEqual(historyThrough(rows,"a","2024-02-29"),rows.slice(0,2));
});
test("symmetric heatmap keeps missing pairs and omits invented self correlations",()=>{
  const rows=symmetricPairs([{series_low_id:"A",series_high_id:"B",correlation:null,pair_key:"A|B"}]);
  assert.equal(rows.length,2);
  assert.ok(rows.every(row=>row.column!==row.row && row.correlation===null));
});
test("ranking retains measured zero and excludes incomplete groups",()=>{
  const rows=[{series_id:"A",group_comparison_status:"supported",absolute_deviation_from_group_mean:0},
    {series_id:"B",group_comparison_status:"supported",absolute_deviation_from_group_mean:2},
    {series_id:"C",group_comparison_status:"incomplete_group",absolute_deviation_from_group_mean:null}];
  assert.deepEqual(rankNodes(rows).map(r=>r.series_id),["B","A"]);
  assert.equal(rankNodes(rows)[1].divergence,0);
});
test("pair window resolves exact selected point states without filling gaps",()=>{
  const evidence=[{series_id:"A",window_point_ids:"[0]"},{series_id:"B",window_point_ids:"[1]"}];
  const points=new Map([[0,{series_id:"A",reference_period:"2024-01-01",value:0,status:"supported",source_records:"[]"}],
    [1,{series_id:"B",reference_period:"2024-01-01",value:null,status:"source_missing",source_records:"[]"}]]);
  const result=windowEvidence(evidence,points,{series_low_id:"A",series_high_id:"B"});
  assert.equal(result.rows[0].left_value,0);
  assert.equal(result.rows[0].right_value,null);
  assert.equal(result.rows[0].right_status,"source_missing");
  assert.throws(()=>windowEvidence(evidence,new Map(),{series_low_id:"A",series_high_id:"B"}),/Invalid reviewed point/);
});
