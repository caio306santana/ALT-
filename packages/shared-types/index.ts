export interface Conversation {
  id: string;
  title: string;
  created: string;
  updated: string;
}
export interface Metrics {
  tokens: number | null;
  tokens_per_second: number | null;
  first_token_seconds: number | null;
  total_seconds: number | null;
  prompt_tokens: number | null;
  request_first_token_seconds?: number | null;
  request_total_seconds?: number | null;
  preparation_seconds?: number | null;
  model_load_seconds?: number | null;
  prompt_eval_seconds?: number | null;
  generation_seconds?: number | null;
  provider_total_seconds?: number | null;
  tools_offered?: number;
  verification?: Verification;
  speed?: { reference: number; ratio: number; warning?: string };
  route?: { band: string; reason: string };
}
export interface Verification {
  calculations: { claim: string; expression: string; stated: string; actual: number; ok: boolean; rounded?: boolean }[];
  sources: { url: string; confirmed: boolean }[];
  issues: number;
  notice: string;
}
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  model: string | null;
  status: "complete" | "streaming" | "interrupted" | "error";
  created: string;
  metrics: Metrics | null;
}
export interface ModelInfo {
  source: 'ollama' | 'unknown';
  capabilities: {text:boolean|null;vision:boolean|null;tools:boolean|null;thinking:boolean|null};
  max_context: number|null;
  thinking_values: (boolean|string)[]|null;
  thinking_default: boolean|string|null;
  active_context?: number;
  profile?: string;
  context_limited_by_model?: boolean;
}
export interface Model {
  name: string;
  size: number;
  details?: { parameter_size?: string; quantization_level?: string };
  provider?: string;
  location?: "local" | "cloud" | "auto";
  info?: ModelInfo;
}
export interface Preferences {
  accent: string;
  theme: string;
  opacity: number;
  font_size: number;
  glow: number;
  compact: boolean;
  animations: boolean;
  model: string;
  performance: "auto" | "notebook" | "desktop";
  personality: Personality;
  secondary: string;
  appearance: "dark" | "light";
  scale: number;
  chat_opacity: number;
  effects: boolean;
  radius: number;
  shortcut: string;
  always_on_top: boolean;
  user_name: string;
  tool_routing?: "stable" | "filtered";
  gpu_light_auto?: boolean;
  learned_examples?: boolean;
  voice_engine?: "dora" | "maria";
  voice_speed?: number;
  voice_input?: string;
  voice_output?: string;
  voice_ptt?: string;
  wake_mode?: "off" | "hey_jarvis" | "ei_alt";
  voice_replies?: boolean;
  memory_suggestions?: boolean;
  briefing_enabled?: boolean;
  briefing_time?: string;
  weather_city?: string;
  briefing_voice?: boolean;
  proactive_enabled?: boolean;
  proactive_daily_cap?: number;
  quiet_start?: string;
  quiet_end?: string;
  topics?: string[];
  pc_alerts?: boolean;
}
export interface Personality {
  name: string;
  tone: string;
  irony: number;
  challenge: number;
  warmth: number;
  formality: number;
  instructions: string;
}
export interface Memory {
  id: string;
  title: string;
  content: string;
  category: "preferência" | "projeto" | "decisão" | "contexto";
  enabled: boolean;
  created: string;
  updated: string;
}
export interface ProviderStatus {
  id: string;
  name: string;
  available: boolean;
  location: string;
  billing: string;
  reason: string;
}
export interface CloudPreview {
  provider: ProviderStatus;
  messages: { role: string; content: string }[];
  consent_receipt: string;
  estimated_usd: number | null;
  billing_notice: string;
  tools_offered?: string[];
  context_truncated: boolean;
  tool_result_truncated?: boolean;
  recalled_memories?: {id:string;title:string;kind?:string;score?:number|null;mode?:string}[];
}
export type StreamEvent = {
  model?: string;
  execution?: "direct" | "model";
  type:
    | "start"
    | "delta"
    | "error"
    | "done"
    | "progress"
    | "tool_proposal"
    | "tool_result"
    | "notice";
  proposal?: { id: string; preview: Record<string, unknown> };
  action_id?: string;
  result?: unknown;
  text?: string;
  message_id?: string;
  message?: string;
  status?: string;
  metrics?: Metrics;
  completed?: number;
  total?: number;
  context_truncated?: boolean;
  tool_result_truncated?: boolean;
  recalled_memories?: {id:string;title:string}[];
};
