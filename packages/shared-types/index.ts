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
export interface Model {
  name: string;
  size: number;
  details?: { parameter_size?: string; quantization_level?: string };
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
}
export type StreamEvent = {
  type: "start" | "delta" | "error" | "done" | "progress";
  text?: string;
  message_id?: string;
  message?: string;
  status?: string;
  metrics?: Metrics;
  completed?: number;
  total?: number;
  context_truncated?: boolean;
};
