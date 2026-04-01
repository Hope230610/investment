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

export type AnalysisStatus = 'processing' | 'ready' | 'expired' | 'failed';
export type ReviewTaskStatus = 'pending' | 'completed' | 'expired';
export type OutputMarkType = 'data_fact' | 'model_inference' | 'uncertainty';

export interface UserProfile {
  experience_level: ExperienceLevel;
  holding_horizon: HoldingHorizon;
  risk_tolerance: RiskTolerance;
  behavior_tags: BehaviorTag[];
  investment_goals?: string | null;
  portfolio_size?: string | null;
  preferred_sectors?: string[] | null;
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
  tag: OutputMarkType;
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

export interface BehaviorIntervention {
  behavior_type: string;
  severity: 'low' | 'medium' | 'high';
  questions: string[];
}

export interface MarketContext {
  market_event: string;
  impact_boundary: string;
  tag: OutputMarkType;
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
  analysis_id: number;
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
  id: number;
  scenario: AnalysisScenario;
  stock_id: string;
  stock_name?: string | null;
  created_at: string;
  status: AnalysisStatus;
  headline?: string | null;
}

export interface AnalysisDetail {
  id: number;
  user_id: number;
  stock_id: string;
  stock_name?: string | null;
  stock_market?: string | null;
  stock_industry?: string | null;
  scenario: AnalysisScenario;
  status: AnalysisStatus;
  headline?: string | null;
  decision_card?: DecisionCard | null;
  fit_summary?: string | null;
  market_context?: MarketContext | null;
  explanation_layer?: ExplanationLayer | null;
  intervention?: BehaviorIntervention | null;
  review_at?: string | null;
  valid_until?: string | null;
  created_at: string;
  updated_at: string;
  reasons: AnalysisReason[];
  review_tasks: ReviewTask[];
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
