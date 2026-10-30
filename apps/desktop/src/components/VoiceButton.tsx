import { useEffect, useState } from "react";
import { Loader2, Mic, Square, Volume2 } from "lucide-react";

type Download = { installed: boolean; downloading: boolean; progress: number | null; error: string; size_mb: number };
export type VoiceStatus = Download & { whisper: Download; dora: Download; wake: Download; state: string; engine: string; speaking: boolean };
export type VoiceState = "off" | "sleeping" | "awake" | "listening" | "transcribing";

export function useVoiceStatus(trigger: unknown) {
  const [status, setStatus] = useState<VoiceStatus | null>(null);
  const refresh = () => window.alt.request<VoiceStatus>("GET", "/voice/status").then(setStatus).catch(() => {});
  useEffect(() => { refresh(); }, [trigger]);
  useEffect(() => {
    const busy = status?.whisper.downloading || status?.dora.downloading || status?.wake.downloading;
    if (!busy) return;
    const timer = setInterval(refresh, 1500);
    return () => clearInterval(timer);
  }, [status?.whisper.downloading, status?.dora.downloading, status?.wake.downloading]);
  return [status, refresh] as const;
}

// The microphone is the backend's: this button starts or stops one utterance and shows the state.
export function VoiceButton({ disabled, state, speaking, onError }: {
  disabled: boolean; state: VoiceState; speaking: boolean; onError: (e: unknown) => void;
}) {
  const [status, refresh] = useVoiceStatus(state);
  const [offer, setOffer] = useState(false);
  const whisper = status?.whisper;
  async function click() {
    try {
      if (state === "listening" || speaking) { await window.alt.request("POST", "/voice/stop"); return; }
      if (!whisper?.installed) { setOffer(!whisper?.downloading); return; }
      await window.alt.request("POST", "/voice/listen");
    } catch (e) { onError(e); }
  }
  const title = whisper?.downloading ? `Baixando voz local… ${Math.round((whisper.progress || 0) * 100)}%`
    : speaking ? "A ALT está falando: clique para cortar"
    : state === "listening" ? "Ouvindo… clique para parar"
    : state === "transcribing" ? "Transcrevendo no seu PC…"
    : state === "awake" ? "Acordada: pode falar sem apertar nada"
    : state === "sleeping" ? "Dormindo: diga a palavra de ativação ou clique"
    : "Falar com a ALT (voz local; segure Ctrl+Espaço de qualquer lugar)";
  return <span className="voice-control">
    <button type="button" className={"voice-button " + (speaking ? "speaking" : state)} disabled={disabled || !!whisper?.downloading || state === "transcribing"} title={title} aria-label={title} onClick={click}>
      {state === "transcribing" || whisper?.downloading ? <Loader2 size={18} className="spin" />
        : speaking ? <Volume2 size={18} />
        : state === "listening" ? <Square size={16} /> : <Mic size={18} />}
    </button>
    {offer && <div className="voice-offer" role="dialog" aria-label="Ativar voz local">
      <strong>Ativar voz local?</strong>
      <p>Baixa o Whisper small (~{whisper?.size_mb || 480} MB) uma vez. Sua fala é transcrita no seu PC; o áudio não vai para a internet.</p>
      {whisper?.error && <p className="voice-error">{whisper.error}</p>}
      <div>
        <button type="button" onClick={async () => {
          try { await window.alt.request("POST", "/voice/download", { kind: "whisper" }); await refresh(); } catch (e) { onError(e); }
          setOffer(false);
        }}>Baixar</button>
        <button type="button" onClick={() => setOffer(false)}>Agora não</button>
      </div>
    </div>}
  </span>;
}
