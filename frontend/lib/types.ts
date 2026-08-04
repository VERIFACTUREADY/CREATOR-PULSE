/**
 * Tipos que reflejan los esquemas de la API.
 *
 * Se mantienen sincronizados a mano con `backend/app/schemas`. La API expone
 * su OpenAPI en `/openapi.json` para poder generarlos automáticamente si el
 * proyecto crece.
 */

export type AnalysisStatus =
  | 'queued'
  | 'fetching'
  | 'preprocessing'
  | 'embedding'
  | 'clustering'
  | 'scoring'
  | 'recommending'
  | 'completed'
  | 'failed';

export type ConfidenceLevel = 'baja' | 'media' | 'alta';
export type TrendDirection = 'rising' | 'stable' | 'falling' | 'unknown';
export type SamplingStrategy = 'recent' | 'relevant' | 'mixed';
export type DataSource = 'youtube_api' | 'demo';

export interface ApiErrorBody {
  code: string;
  message: string;
  detail?: string;
  context?: Record<string, unknown>;
}

export interface ApiEnvelope {
  ok: boolean;
  data: unknown;
  error: ApiErrorBody | null;
  request_id: string | null;
}

export interface PublicConfig {
  app_name: string;
  app_env: string;
  demo_mode_enabled: boolean;
  youtube_configured: boolean;
  ai_enabled: boolean;
  ai_provider: string;
  owner_mode_enabled: boolean;
  toxicity_analysis_enabled: boolean;
  anonymize_comment_authors: boolean;
  data_retention_days: number;
  comment_retention_days: number;
  /** Fecha ISO de la última purga real; `null` si nunca se ha ejecutado. */
  last_purge_at: string | null;
  algorithm_version: string;
  embedding_backend: string;
  sentiment_backend: string;
  limits: {
    default_max_videos: number;
    default_max_comments_per_video: number;
    default_max_comments_per_channel: number;
    hard_max_videos: number;
    hard_max_comments_per_video: number;
    hard_max_comments_per_channel: number;
  };
  disclaimer_es: string;
  criticism_notice_es: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  components: { name: string; healthy: boolean; detail: string | null }[];
}

export interface Channel {
  id: string;
  youtube_channel_id: string;
  handle: string | null;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  subscriber_count: number | null;
  subscriber_count_hidden: boolean;
  video_count: number | null;
  view_count: number | null;
  country: string | null;
  published_at: string | null;
  source: DataSource;
  last_fetched_at: string | null;
  created_at: string;
}

export interface AnalysisRunBrief {
  id: string;
  status: AnalysisStatus;
  status_label_es: string;
  progress: number;
  created_at: string;
  completed_at: string | null;
  videos_fetched: number;
  comments_analysed: number;
  error_code: string | null;
  error_message_es: string | null;
  source: DataSource;
}

export interface ChannelListItem {
  channel: Channel;
  latest_run: AnalysisRunBrief | null;
  latest_completed_run: AnalysisRunBrief | null;
  top_opportunity_es: string | null;
}

export interface RunStatus {
  id: string;
  channel_id: string;
  status: AnalysisStatus;
  status_label_es: string;
  progress: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  videos_fetched: number;
  comments_fetched: number;
  comments_analysed: number;
  error_code: string | null;
  error_message_es: string | null;
  is_demo: boolean;
}

export interface RepresentativeComment {
  text: string;
  sentiment?: string;
  likes?: number;
  video_id?: string;
  video_title?: string;
  youtube_video_id?: string;
  published_at?: string | null;
}

export interface Topic {
  cluster_key: string;
  label_es: string;
  description_es: string | null;
  comment_count: number;
  unique_video_count: number;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  request_count: number;
  question_count: number;
  share_of_comments: number;
  mentions_per_1000: number;
  video_coverage: number;
  recent_share: number | null;
  previous_share: number | null;
  trend_score: number;
  trend_direction: TrendDirection;
  trend_label_es: string;
  coverage_score: number;
  confidence_score: number;
  confidence_level: ConfidenceLevel;
  dominant_video_share: number;
  top_aspects: string[] | null;
  keywords: string[] | null;
  representative_comments: RepresentativeComment[] | null;
  is_noise: boolean;
  ai_generated_label: boolean;
}

export interface Evidence {
  supporting_comments: number;
  supporting_videos: number;
  total_comments_analysed: number;
  total_videos_analysed: number;
  share_of_comments: number;
  mentions_per_1000: number;
  video_coverage: number;
  trend_direction: TrendDirection;
  trend_change: number | null;
  dominant_video_share: number;
  positive_count: number;
  negative_count: number;
  request_count: number;
  question_count: number;
  performance_association: Record<string, unknown>;
  representative_comments: RepresentativeComment[];
  confidence_penalties_es: string[];
  source_es: string;
}

export interface Recommendation {
  id: string;
  category: string;
  category_label_es: string;
  title_es: string;
  explanation_es: string;
  reason_es: string;
  evidence: Evidence;
  confidence_score: number;
  confidence_level: ConfidenceLevel;
  priority: number;
  suggested_format: string | null;
  suggested_format_label_es: string | null;
  suggested_hook_es: string | null;
  suggested_experiment_es: string | null;
  kpi_es: string | null;
  caveat_es: string | null;
  topic_cluster_key: string | null;
  ai_enriched: boolean;
}

export interface ContentIdea {
  id: string;
  title_es: string;
  concept_es: string;
  why_es: string;
  evidence: { bullets_es?: string[] } & Record<string, unknown>;
  suggested_format: string;
  suggested_format_label_es: string;
  hook_es: string;
  call_to_action_es: string;
  experiment_es: string;
  kpi_es: string;
  confidence_score: number;
  confidence_level: ConfidenceLevel;
  overinterpretation_risk_es: string;
  topic_cluster_key: string | null;
}

export interface VideoRow {
  youtube_video_id: string;
  title: string;
  thumbnail_url: string | null;
  published_at: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  comments_disabled: boolean;
  likes_per_1000_views: number | null;
  comments_per_1000_views: number | null;
  engagement_actions_per_1000_views: number | null;
  views_relative_to_median: number | null;
  performance_band: string;
  age_caveat: boolean;
  age_days: number | null;
  analysed_comment_count: number;
  dominant_topics: { cluster_key: string; label_es: string; comment_count: number }[] | null;
  sentiment_breakdown: Record<string, number> | null;
  youtube_url: string;
}

export interface RequestItem {
  cluster_key: string | null;
  label_es: string;
  kind: string;
  kind_label_es: string;
  count: number;
  unique_video_count: number;
  confidence_level: ConfidenceLevel;
  examples: RepresentativeComment[];
}

export interface StrengthItem {
  aspect: string;
  label_es: string;
  count: number;
  unique_video_count: number;
  share_of_positive: number;
  confidence_level: ConfidenceLevel;
  examples: RepresentativeComment[];
}

export interface CriticismGroup {
  kind: 'constructive' | 'subjective' | 'harassment' | 'spam';
  label_es: string;
  description_es: string;
  count: number;
  items: (RepresentativeComment & {
    label_es?: string;
    count?: number;
    unique_video_count?: number;
    actionable?: boolean;
    examples?: RepresentativeComment[];
  })[];
}

export interface DataQuality {
  videos_sampled: number;
  comments_sampled: number;
  comments_analysed: number;
  comments_discarded_spam: number;
  comments_discarded_duplicate: number;
  comments_discarded_empty: number;
  videos_with_comments_disabled: number;
  videos_with_zero_comments: number;
  videos_missing_views: number;
  videos_missing_likes: number;
  sampling_strategy: string;
  sampling_buckets: Record<string, number>;
  date_coverage: Record<string, unknown>;
  language_distribution: Record<string, number>;
  dominant_video_share: number;
  viral_view_concentration: number;
  clustering_strategy: string;
  topics_found: number;
  noise_share: number;
  ai_used: boolean;
  ai_provider: string;
  algorithm_version: string;
  embedding_backend: string;
  sentiment_backend: string;
  is_demo: boolean;
  score: number;
  level: ConfidenceLevel;
  warnings_es: string[];
  biases_es: string[];
}

export interface TopicBrief {
  cluster_key: string;
  label_es: string;
  comment_count: number;
  unique_video_count: number;
  positive_count: number;
  negative_count: number;
  request_count: number;
  share_of_comments: number;
  trend_direction: TrendDirection;
  trend_change: number | null;
  confidence_level: ConfidenceLevel;
}

export interface DashboardSummary {
  videos_analysed: number;
  comments_analysed: number;
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
    mixed: number;
    uncertain: number;
    positive_share: number;
    negative_share: number;
    overall_es: string;
  };
  questions: number;
  requests: number;
  toxic_comments: number;
  spam_comments: number;
  top_strength: TopicBrief | null;
  top_request: TopicBrief | null;
  top_criticism: TopicBrief | null;
  fastest_growing: TopicBrief | null;
  top_recommendation: {
    title_es: string;
    category: string;
    category_label_es: string;
    confidence_level: ConfidenceLevel;
    priority: number;
  } | null;
  data_quality_level: ConfidenceLevel;
  data_quality_score: number;
  primary_warning_es: string | null;
  intent_counts: Record<string, number>;
  median_views: number;
  median_comments_per_1000: number;
  median_likes_per_1000: number;
}

export interface Dashboard {
  run: RunStatus;
  channel: Channel;
  summary: DashboardSummary;
  topics: Topic[];
  recommendations: Recommendation[];
  content_ideas: ContentIdea[];
  videos: VideoRow[];
  requests: RequestItem[];
  strengths: StrengthItem[];
  criticism: CriticismGroup[];
  data_quality: DataQuality;
  disclaimer_es: string;
}

export interface ComparisonChannelRow {
  run_id: string;
  channel_id: string;
  channel_title: string;
  handle: string | null;
  thumbnail_url: string | null;
  is_demo: boolean;
  subscriber_count: number | null;
  subscriber_count_hidden: boolean;
  videos_analysed: number;
  comments_analysed: number;
  median_views: number;
  median_likes_per_1000: number;
  median_comments_per_1000: number;
  positive_share: number;
  negative_share: number;
  request_share: number;
  top_topics: { label_es: string; comment_count: number; share_of_comments: number }[];
  data_quality_score: number;
  data_quality_level: ConfidenceLevel;
}

export interface Comparison {
  id: string | null;
  channels: ComparisonChannelRow[];
  warnings_es: string[];
  created_at: string | null;
}

export interface DemoChannel {
  handle: string;
  youtube_channel_id: string;
  title: string;
  videos: number;
  comments: number;
}

export interface ResolvedChannel {
  kind: string;
  value: string;
  display: string;
  is_demo: boolean;
  channel: Channel | null;
  message_es: string | null;
}

export interface AnalyseAccepted {
  run_id: string;
  channel_id: string;
  status: AnalysisStatus;
  queued: boolean;
  is_demo: boolean;
  estimated_quota_units: number;
  message_es: string;
}

export interface WorkloadEstimate {
  estimated_quota_units: number;
  daily_quota_reference: number;
  estimated_seconds: number;
  note_es: string;
}

export interface UsageSummary {
  window_days: number;
  by_endpoint: { endpoint: string; requests: number; estimated_quota_units: number; calls: number }[];
  estimated_units_today: number;
  estimated_units_window: number;
  failed_calls_window: number;
  cached_calls_window: number;
  daily_quota_reference: number;
  note_es: string;
}

// --- Modo propietario -------------------------------------------------------

export interface OwnerConnectionInfo {
  provider: string;
  channel_id: string | null;
  channel_title: string | null;
  external_account_id: string;
  scopes: string[];
  expires_at: string | null;
  last_refreshed_at: string | null;
  connected_at: string | null;
  has_refresh_token: boolean;
}

export interface OwnerStatus {
  enabled: boolean;
  configured: boolean;
  encryption_ready: boolean;
  ready: boolean;
  missing_config: string[];
  scopes: string[];
  owner_only_metrics: string[];
  connections: OwnerConnectionInfo[];
  message_es: string;
}

export interface StartAuthorization {
  authorization_url: string;
  state: string;
  scopes: string[];
  message_es: string;
}

/** `null` significa «no disponible», nunca cero. */
export interface OwnerAnalytics {
  channel_id: string;
  channel_title: string;
  start_date: string;
  end_date: string;
  views: number | null;
  estimated_minutes_watched: number | null;
  average_view_duration_seconds: number | null;
  average_view_percentage: number | null;
  subscribers_gained: number | null;
  subscribers_lost: number | null;
  net_subscribers: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  impressions: number | null;
  impressions_ctr: number | null;
  daily: Record<string, unknown>[];
  traffic_sources: Record<string, unknown>[];
  geography: Record<string, unknown>[];
  top_videos: Record<string, unknown>[];
  unavailable_es: string[];
  note_es: string;
}
