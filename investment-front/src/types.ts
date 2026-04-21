export type ExperienceLevel = 'novice' | 'intermediate' | 'expert';
export type HoldingHorizon = 'short' | 'medium' | 'long';
export type RiskTolerance = 'low' | 'medium' | 'high';
export type BehaviorTag =
  | 'chasing_rise'
  | 'panic_sell'
  | 'frequent_trading'
  | 'stable_discipline';

export type AnalysisScenario =
  | 'single_stock_check'
  | 'pre_trade_check'
  | 'post_trade_review';

export type AnalysisStatus = 'processing' | 'partial_ready' | 'ready' | 'expired' | 'failed';
export type ReviewTaskStatus = 'pending' | 'completed' | 'expired';
export type OutputMarkType = 'data_fact' | 'model_inference' | 'uncertainty';

export interface UserProfile {
  experience_level: ExperienceLevel;
  holding_horizon: HoldingHorizon;
  risk_tolerance: RiskTolerance;
  behavior_tags: BehaviorTag[];
}

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  profile?: UserProfile | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface Stock {
  stock_id: string;
  stock_name: string;
  market: string;
  industry?: string | null;
}

export interface StockSearchItem extends Stock {
  stock_code: string;
  security_type?: string | null;
  pinyin?: string | null;
  quote_id?: string | null;
  matched_by?: string | null;
}

export interface StockQuoteSnapshot {
  latest_price?: number | null;
  change_amount?: number | null;
  change_percent?: number | null;
  open_price?: number | null;
  high_price?: number | null;
  low_price?: number | null;
  previous_close?: number | null;
  volume?: number | null;
  amount?: number | null;
  turnover_rate?: number | null;
  pe_ratio?: number | null;
  pb_ratio?: number | null;
  total_market_cap?: number | null;
  circulating_market_cap?: number | null;
  amplitude?: number | null;
  data_as_of?: string | null;
}

export interface StockHistoryPoint {
  date: string;
  open_price: number;
  close_price: number;
  high_price: number;
  low_price: number;
  volume: number;
}

export interface StockCompanyProfile {
  description?: string | null;
  business_scope?: string | null;
  board_name?: string | null;
  listing_date?: string | null;
  source_url?: string | null;
}

export interface StockEvent {
  title: string;
  event_type?: string | null;
  published_at?: string | null;
  url?: string | null;
  source: string;
}

export interface StockDetail extends StockSearchItem {
  quote_snapshot?: StockQuoteSnapshot | null;
  company_profile?: StockCompanyProfile | null;
  recent_events: StockEvent[];
  recent_history: StockHistoryPoint[];
  data_sources: string[];
}

export interface ReasonPoint {
  text: string;
  mark_type: OutputMarkType;
}

export interface UserFitSummary {
  fit: string;
  unfit: string;
}

export interface DecisionCard {
  headline_judgement: string;
  key_reason_summary: ReasonPoint[];
  user_fit_summary: UserFitSummary;
  next_step_actions: string[];
  primary_risks: string;
  review_at: string;
  valid_until?: string | null;
  data_as_of?: string | null;
  stock_snapshot?: StockQuoteSnapshot | null;
  company_profile?: StockCompanyProfile | null;
  recent_events: StockEvent[];
  data_sources: string[];
}

/** 六段式决策卡 V2（无附加行情数据，行情数据在顶层） */
export interface DecisionCardV2 {
  headline_judgement: string;
  key_reason_summary: Array<{ text: string; mark_type: OutputMarkType }>;
  user_fit_summary: { fit: string; unfit: string };
  next_step_actions: string[];
  primary_risks: string;
  review_at: string;
}

export interface BehaviorIntervention {
  behavior_type: string;
  severity: 'low' | 'medium' | 'high';
  questions: string[];
}

export interface MarketContext {
  market_event: string;
  impact_boundary: string;
  mark_type: OutputMarkType;
}

export interface ExplanationLayer {
  plain_text: string;
  case_example: string;
}

export interface AnalysisReason {
  id: number;
  analysis_id: number;
  text: string;
  order: number;
  mark_type: OutputMarkType;
  created_at: string;
  updated_at: string;
}

export interface ReviewTask {
  id: number;
  user_id: number;
  analysis_task_id?: string;  // 新路径 UUID
  analysis_id?: number;        // 旧路径 Integer（向后兼容）
  stock_id?: string | null;
  stock_name: string;
  scenario: AnalysisScenario;
  review_at: string;
  status: ReviewTaskStatus;
  review_result?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisRecord {
  id: string;
  scenario: AnalysisScenario;
  stock_id: string;
  stock_name?: string | null;
  created_at: string;
  status: AnalysisStatus;
  headline?: string | null;
}

/**
 * 分析详情 V2（对应 GetAnalysisResponseV2）
 * stock_snapshot / company_profile / recent_events / data_sources 提至顶层
 */
export interface AnalysisDetail {
  analysis_id: string;
  user_id: number;
  stock_id: string;
  scenario: string;
  status: AnalysisStatus;
  degrade_flags: string[];
  decision_card: DecisionCardV2;
  fit_summary?: string | null;
  market_context?: MarketContext | null;
  explanation_layer?: ExplanationLayer | null;
  intervention?: BehaviorIntervention | null;
  review_task?: { id: number; review_at: string; status: string } | null;
  // 行情数据（从实时接口获取，提至顶层）
  stock_snapshot?: StockQuoteSnapshot | null;
  company_profile?: StockCompanyProfile | null;
  recent_events: StockEvent[];
  data_sources: string[];
  valid_until?: string | null;
  data_as_of?: string | null;
  // 股票基本信息（从 StockDetail 获取）
  stock_name?: string | null;
  stock_market?: string | null;
  stock_industry?: string | null;
  // 场景透传（intent / trigger_reason / emotion_level 等，用于标签推断）
  scenario_payload?: Record<string, unknown> | null;
}

export interface WatchlistItem {
  id: string;
  stock_id: string;
  stock_name: string;
  market: string;
  industry?: string | null;
  added_at: string;
  focus_reason?: string;
}

export interface FocusReason {
  id: string;
  analysis_id: string;
  stock_id: string;
  reason: string;
  created_at: string;
}

// ============================================================
// 新数据模型类型（Phase 1~3 迁移后启用）
// ============================================================

/** 用户画像快照（分析任务创建时留存） */
export interface UserProfileSnapshot {
  experience_level: ExperienceLevel;
  holding_horizon: HoldingHorizon;
  risk_tolerance: RiskTolerance;
  behavior_tags: BehaviorTag[];
}

/** 分析任务（UUID 主键，Phase 1 起使用） */
export interface AnalysisTask {
  id: string;
  user_id: number;
  stock_id: string;
  created_at: string;
  updated_at: string;
  scenario: AnalysisScenario;
  status: AnalysisStatus;
  user_profile_snapshot: UserProfileSnapshot | null;
  scenario_payload: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  expired_at: string;
  error_message: string | null;
}

/** 分析结果（六段式决策卡，Phase 1 起使用） */
export interface ReasonPointV2 {
  text: string;
  mark_type: OutputMarkType;
}

export interface DetailPanels {
  facts: string[];
  inferences: string[];
  uncertainties: string[];
}

export interface AnalysisResult {
  id: string;
  analysis_task_id: string;
  created_at: string;
  headline_judgement: string;
  key_reason_summary: ReasonPointV2[];
  user_fit_summary: UserFitSummary;
  next_step_actions: string[];
  primary_risks: string;
  review_at: string;
  intervention: BehaviorIntervention | null;
  fit_summary: string | null;
  market_context: MarketContext | null;
  explanation_layer: ExplanationLayer | null;
  detail_panels: DetailPanels | null;
  output_tags: OutputMarkType[];
  valid_period: 'short' | 'medium' | 'long';
}

/** 行为干预记录（独立表，Phase 1 起使用） */
export interface BehaviorInterventionRecord {
  id: string;
  user_id: number;
  analysis_task_id: string | null;
  created_at: string;
  behavior_type: 'chasing_rise' | 'panic_sell' | 'frequent_trading';
  severity: 'low' | 'medium' | 'high';
  cooldown_started_at: string | null;
  cooldown_ended_at: string | null;
  cooldown_questions: string[] | null;
  user_acknowledged: boolean;
  user_notes: string | null;
  action_taken: 'continued' | 'delayed' | 'cancelled' | 'logged_only' | null;
}

/** 合并后的观察列表（Phase 3，移除 focus_reasons 分离） */
export interface WatchlistItemV2 {
  id: string;
  user_id: number;
  stock_id: string;
  created_at: string;
  focus_reason: string | null;
  added_from_scenario: string | null;
}

/** 用户操作埋点（Phase 1 起使用） */
export type UserActionType =
  | 'scenario_selected'
  | 'analysis_submitted'
  | 'behavior_intervention_shown'
  | 'cooldown_started'
  | 'review_task_completed';

export interface UserAction {
  id: string;
  user_id: number;
  created_at: string;
  action_type: UserActionType;
  action_payload: Record<string, unknown> | null;
  stock_id: string | null;
  analysis_task_id: string | null;
  page_path: string | null;
  user_agent: string | null;
}
