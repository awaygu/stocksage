// The canonical StockSage agent DAG.
// agent_ids here are the *real* ids the backend publishes over WS
// (verified against backend/graph/nodes/* and agents/router.py),
// fixing the P1-7 misalignment where the old UI used
// router/news_sentiment/synthesis which the backend never sends.
//
// Edges encode the plan-and-execute dependency graph from
// backend/graph/router.py build_plan(): market_data feeds the
// analysis agents, which feed risk, which feeds report.

export type AgentId =
  | 'planner'
  | 'market_data'
  | 'technical'
  | 'fundamental'
  | 'news'
  | 'macro'
  | 'industry'
  | 'risk'
  | 'report'

export interface StageMeta {
  id: AgentId
  label: string
  // short id shown in mono — the terminal's "ticker" for each desk
  code: string
}

// ordered left-to-right as they typically execute (planner → fan-out → join → report)
export const STAGES: StageMeta[] = [
  { id: 'planner', label: '意图解析', code: 'PLAN' },
  { id: 'market_data', label: '市场数据', code: 'MKT' },
  { id: 'technical', label: '技术面', code: 'TECH' },
  { id: 'fundamental', label: '基本面', code: 'FUND' },
  { id: 'news', label: '新闻情绪', code: 'NEWS' },
  { id: 'macro', label: '宏观', code: 'MACRO' },
  { id: 'industry', label: '行业', code: 'IND' },
  { id: 'risk', label: '风险评估', code: 'RISK' },
  { id: 'report', label: '报告生成', code: 'RPT' },
]

// which stages depend on which — drives the arrow connectors.
// market_data is the fan-out root; risk joins technical+fundamental; report joins all.
export const EDGES: Record<AgentId, AgentId[]> = {
  planner: ['market_data'],
  market_data: ['technical', 'fundamental', 'news', 'industry'],
  technical: ['risk'],
  fundamental: ['risk'],
  news: ['report'],
  macro: ['report'],
  industry: ['report'],
  risk: ['report'],
  report: [],
}

// human labels for any other backend id we didn't enumerate (defensive)
export const LABELS: Record<string, string> = Object.fromEntries(
  STAGES.map((s) => [s.id, s.label]),
)
