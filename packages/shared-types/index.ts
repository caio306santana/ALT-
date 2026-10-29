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
  provider?:string;
  location?:'local'|'cloud';
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
  personality:Personality;
  secondary:string;
  appearance:'dark'|'light';
  scale:number;
  chat_opacity:number;
  effects:boolean;
  radius:number;
  shortcut:string;
  always_on_top:boolean;
}
export interface Personality {name:string;tone:string;irony:number;challenge:number;warmth:number;formality:number;instructions:string}
export interface Memory {id:string;title:string;content:string;category:'preferência'|'projeto'|'decisão'|'contexto';enabled:boolean;created:string;updated:string}
export interface ProviderStatus {id:string;name:string;available:boolean;location:string;billing:string;reason:string}
export interface CloudPreview {provider:ProviderStatus;messages:{role:string;content:string}[];consent_receipt:string;estimated_usd:number|null;billing_notice:string;context_truncated:boolean}
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
