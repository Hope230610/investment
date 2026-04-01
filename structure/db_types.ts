/**
 * 数据库模型类型定义
 * 对应 database_design.md 中的表结构
 */

// 基础类型
export type UUID = string;
export type Timestamp = string;
export type JsonB = Record<string, any>;
export type ReviewStatus = 'pending' | 'completed' | 'expired';
export type ExperienceLevel = 'novice' | 'intermediate' | 'expert';
export type HoldingHorizon = 'short' | 'medium' | 'long';
export type RiskTolerance = 'low' | 'medium' | 'high';
export type BehaviorTag = 'chasing_rise' | 'panic_sell' | 'frequent_trading' | 'stable_discipline';
export type BehaviorType = 'chasing_rise' | 'panic_sell' | 'frequent_trading';
export type SeverityLevel = 'low' | 'medium' | 'high';
export type MarketCode = 'SH' | 'SZ' | 'BJ';
export type ExchangeCode = 'SSE' | 'SZSE' | 'BSE';
export type ProfileSource = 'user_input' | 'default_conservative' | 'imported';
export type ValidPeriod = 'short' | 'medium' | 'long';
export type PreTradeIntent = 'buy' | 'add' | 'reduce' | 'sell';
export type ActionTaken = 'buy' | 'add' | 'reduce' | 'sell';
export type InterventionActionTaken = 'continued' | 'delayed' | 'cancelled' | 'logged_only';
export type AttributionScore = 'low' | 'medium' | 'high';
export type DataSourceKey = 'quote' | 'announcement' | 'profile_snapshot' | 'manual_input';

// ============================================
// 用户相关
// ============================================

export interface User {
  id: UUID;
  created_at: Timestamp;
  updated_at: Timestamp;
  email: string | null;
  phone: string | null;
  hashed_password: string | null;
  is_active: boolean;
  last_login_at: Timestamp | null;
  signup_channel: string;
}

export interface UserProfile {
  id: UUID;
  user_id: UUID;
  created_at: Timestamp;
  updated_at: Timestamp;
  experience_level: ExperienceLevel;
  holding_horizon: HoldingHorizon;
  risk_tolerance: RiskTolerance;
  behavior_tags: BehaviorTag[];
  profile_source: ProfileSource;
}

// ============================================
// 股票相关
// ============================================

export interface Stock {
  id: UUID;
  created_at: Timestamp;
  updated_at: Timestamp;
  stock_code: string;
  stock_name: string;
  market: MarketCode;
  exchange: ExchangeCode;
  industry: string | null;
  sector: string | null;
  is_listed: boolean;
  list_date: string | null;
}

export interface Watchlist {
  id: UUID;
  user_id: UUID;
  stock_id: UUID;
  created_at: Timestamp;
  focus_reason: string | null;
  added_from_scenario: string | null;
  source_analysis_id: UUID | null;
  notify_on_events: boolean;
}

// ============================================
// 分析相关
// ============================================

export type AnalysisScenario = 'single_stock_check' | 'pre_trade_check' | 'post_trade_review';
export type AnalysisStatus = 'processing' | 'partial_ready' | 'ready' | 'expired' | 'failed';
export type AnalysisDegradeFlag =
  | 'missing_market_data'
  | 'missing_announcements'
  | 'model_fallback'
  | 'insufficient_evidence';

export interface UserProfileSnapshot {
  experience_level: ExperienceLevel;
  holding_horizon: HoldingHorizon;
  risk_tolerance: RiskTolerance;
  behavior_tags: BehaviorTag[];
  profile_source: ProfileSource;
}

export interface SingleStockScenarioPayload {
  primary_horizon?: HoldingHorizon;
  focus_reason?: string;
}

export interface PreTradeScenarioPayload {
  intent: PreTradeIntent;
  trigger_reason: string;
  emotion_level?: 1 | 2 | 3 | 4 | 5;
  original_plan?: string;
}

export interface PostTradeScenarioPayload {
  action_taken: ActionTaken;
  trigger_reason: string;
  outcome_summary: string;
  emotion_level?: 1 | 2 | 3 | 4 | 5;
  plan_deviation?: boolean;
}

export type ScenarioPayload =
  | SingleStockScenarioPayload
  | PreTradeScenarioPayload
  | PostTradeScenarioPayload;

export interface AnalysisTask {
  id: UUID;
  user_id: UUID;
  stock_id: UUID;
  created_at: Timestamp;
  updated_at: Timestamp;
  scenario: AnalysisScenario;
  status: AnalysisStatus;
  user_profile_snapshot: UserProfileSnapshot | null;
  scenario_payload: ScenarioPayload | null;
  started_at: Timestamp | null;
  completed_at: Timestamp | null;
  expired_at: Timestamp;
  error_message: string | null;
}

export interface UserFitSummary {
  fit: string;
  unfit: string;
}

export interface BehaviorIntervention {
  behavior_type: BehaviorType;
  severity: SeverityLevel;
  questions: string[];
  cooldown_minutes?: number;
  trigger_reason?: string;
}

export interface MarketContext {
  market_event: string;
  impact_boundary: string;
  data_sources?: DataSourceKey[];
}

export interface ExplanationLayer {
  plain_text: string;
  case_example: string;
}

export interface DetailPanels {
  facts: string[];
  inferences: string[];
  uncertainties: string[];
  data_sources: DataSourceKey[];
  degrade_flags?: AnalysisDegradeFlag[];
}

export interface AnalysisResult {
  id: UUID;
  analysis_task_id: UUID;
  created_at: Timestamp;
  headline_judgement: string;
  key_reason_summary: string[];
  user_fit_summary: UserFitSummary;
  next_step_actions: string[];
  primary_risks: string;
  review_at: Timestamp;
  intervention: BehaviorIntervention | null;
  fit_summary: string | null;
  market_context: MarketContext | null;
  explanation_layer: ExplanationLayer | null;
  detail_panels: DetailPanels | null;
  output_tags: ('data_fact' | 'model_inference' | 'uncertainty')[];
  valid_period: ValidPeriod;
}

// ============================================
// 行为干预与复盘
// ============================================

export interface BehaviorInterventionRecord {
  id: UUID;
  user_id: UUID;
  analysis_task_id: UUID | null;
  created_at: Timestamp;
  behavior_type: BehaviorType;
  severity: SeverityLevel;
  cooldown_started_at: Timestamp | null;
  cooldown_ended_at: Timestamp | null;
  cooldown_questions: string[] | null;
  user_acknowledged: boolean;
  user_notes: string | null;
  action_taken: InterventionActionTaken | null;
}

export interface ReviewAttribution {
  judgement_quality: AttributionScore;
  execution_quality: AttributionScore;
  luck_factor: AttributionScore;
  summary?: string;
}

export interface ReviewTask {
  id: UUID;
  user_id: UUID;
  analysis_task_id: UUID;
  stock_id: UUID;
  created_at: Timestamp;
  review_at: Timestamp;
  scenario: AnalysisScenario;
  status: ReviewStatus;
  review_notes: string | null;
  reviewed_at: Timestamp | null;
  attribution: ReviewAttribution | null;
  improvement_actions: string[] | null;
}

// ============================================
// 用户操作记录
// ============================================

export interface UserAction {
  id: UUID;
  user_id: UUID;
  created_at: Timestamp;
  action_type: string;
  action_payload: JsonB | null;
  stock_id: UUID | null;
  analysis_task_id: UUID | null;
  page_path: string | null;
  user_agent: string | null;
}

// ============================================
// 系统配置
// ============================================

export interface SystemConfig {
  id: UUID;
  config_key: string;
  config_value: JsonB;
  description: string | null;
  updated_at: Timestamp;
}

// ============================================
// 视图类型
// ============================================

export interface VUserAnalysisSummary {
  user_id: UUID;
  total_analyses: number;
  single_stock_count: number;
  pre_trade_count: number;
  post_trade_count: number;
  intervention_count: number;
  completed_reviews: number;
  watchlist_count: number;
}

export interface VPendingReview {
  id: UUID;
  user_id: UUID;
  analysis_task_id: UUID;
  stock_code: string;
  stock_name: string;
  scenario: AnalysisScenario;
  review_at: Timestamp;
  status: string;
  headline_judgement: string | null;
  display_status: string;
}

export interface VRecentAnalysis {
  id: UUID;
  user_id: UUID;
  scenario: AnalysisScenario;
  stock_id: UUID;
  stock_code: string;
  stock_name: string;
  created_at: Timestamp;
  status: AnalysisStatus;
  headline_judgement: string | null;
}

// ============================================
// API 请求/响应类型
// ============================================

// 分析任务创建请求
export interface CreateAnalysisRequest {
  scenario: AnalysisScenario;
  stock_id: UUID;
  user_profile?: UserProfileSnapshot;
  scenario_payload?: ScenarioPayload;
}

// 分析任务创建响应
export interface CreateAnalysisResponse {
  analysis_id: UUID;
  status: AnalysisStatus;
  estimated_ready_in_ms: number;
}

// 获取分析结果响应
export interface GetAnalysisResponse {
  analysis_id?: UUID;
  status: AnalysisStatus;
  degrade_flags?: AnalysisDegradeFlag[];
  intervention: BehaviorIntervention | null;
  decision_card: {
    headline_judgement: string;
    key_reason_summary: string[];
    user_fit_summary: UserFitSummary;
    next_step_actions: string[];
    primary_risks: string;
    review_at: Timestamp;
  };
  fit_summary: string | null;
  market_context: MarketContext | null;
  explanation_layer: ExplanationLayer | null;
  detail_panels: DetailPanels | null;
  review_task: {
    id: UUID;
    review_at: Timestamp;
    status: ReviewStatus;
  } | null;
}

export interface ApiError {
  code: string;
  message: string;
  request_id: string;
  retryable: boolean;
}

export interface ErrorResponse {
  error: ApiError;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

// 复盘提交请求
export interface SubmitReviewRequest {
  review_notes: string;
  attribution?: ReviewAttribution;
  improvement_actions?: string[];
}

// 用户操作埋点请求
export interface TrackUserActionRequest {
  action_type: string;
  action_payload?: JsonB;
  stock_id?: UUID;
  analysis_task_id?: UUID;
  page_path?: string;
}
