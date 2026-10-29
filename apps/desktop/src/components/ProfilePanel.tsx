import { Brain, Wrench, Sparkles, ChevronRight } from "lucide-react";
import type { Preferences } from "../../../../packages/shared-types";
export function ProfilePanel({
  prefs,
  onChange,
  onIdentity,
  onMemory,
  onTools,
  model,
}: {
  prefs: Preferences;
  onChange: (prefs: Preferences) => void;
  onIdentity: () => void;
  onMemory: () => void;
  onTools: () => void;
  model: string;
}) {
  return (
    <div className="page-scroll identity-page">
      <div className="identity-hero">
        <div className="identity-sigil">
          <span />
          ALT
        </div>
        <div>
          <span className="eyebrow">IDENTITY // PERSONAL CORE</span>
          <h2>{prefs.personality.name}</h2>
          <p>Calma na voz. Incisiva nas ideias.</p>
          <span className="identity-badge">INTELIGÊNCIA PESSOAL</span>
        </div>
      </div>
      <div className="profile-editor feature-form">
        <label>
          Como você quer ser chamado?
          <input
            value={prefs.user_name}
            maxLength={60}
            placeholder="Seu nome ou apelido · opcional"
            onChange={(e) => onChange({ ...prefs, user_name: e.target.value })}
          />
        </label>
        <p className="setting-note">
          Este é um perfil local. Nome, personalidade e memórias selecionadas
          aparecem na prévia antes de qualquer envio à nuvem.
        </p>
      </div>
      <div className="identity-cards">
        <button onClick={onIdentity}>
          <Sparkles size={20} />
          <span>
            <strong>Personalidade</strong>
            <small>{prefs.personality.tone}</small>
          </span>
          <ChevronRight size={16} />
        </button>
        <button onClick={onMemory}>
          <Brain size={20} />
          <span>
            <strong>Memória</strong>
            <small>O que você decide guardar e compartilhar.</small>
          </span>
          <ChevronRight size={16} />
        </button>
        <button onClick={onTools}>
          <Wrench size={20} />
          <span>
            <strong>Alcance no Windows</strong>
            <small>Modos de autorização, sessões e revogação.</small>
          </span>
          <ChevronRight size={16} />
        </button>
      </div>
      <div className="engine-identity">
        <span className="eyebrow">MOTOR ATIVO</span>
        <strong>{model}</strong>
        <p>
          A ALT-AI é a assistente, com identidade, memória e ferramentas
          próprias. O modelo é o motor selecionável. Usar Qwen não significa que
          treinamos um modelo exclusivo do zero.
        </p>
      </div>
    </div>
  );
}
