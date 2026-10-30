import { useEffect, useRef, useState } from "react";
import { Loader2, Mic, Square } from "lucide-react";

type VoiceStatus = { installed: boolean; downloading: boolean; progress: number | null; error: string; size_mb: number };
const RATE = 16000;
const MAX_SECONDS = 30;

// Records until ~1.2 s of silence after speech (or a click), as 16 kHz mono 16-bit PCM for local Whisper.
async function record(stopRef: { current: (() => void) | null }): Promise<Uint8Array | null> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  const context = new AudioContext({ sampleRate: RATE });
  const source = context.createMediaStreamSource(stream);
  const node = context.createScriptProcessor(4096, 1, 1);
  const chunks: Float32Array[] = [];
  let samples = 0, spoke = false, quiet = 0;
  return new Promise((resolve) => {
    const finish = () => {
      stopRef.current = null;
      node.disconnect();
      source.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      context.close().catch(() => {});
      if (!spoke) return resolve(null);
      const pcm = new Int16Array(samples);
      let offset = 0;
      for (const chunk of chunks)
        for (const value of chunk) pcm[offset++] = Math.max(-1, Math.min(1, value)) * 0x7fff;
      resolve(new Uint8Array(pcm.buffer));
    };
    stopRef.current = finish;
    node.onaudioprocess = (event) => {
      const data = new Float32Array(event.inputBuffer.getChannelData(0));
      chunks.push(data);
      samples += data.length;
      const rms = Math.sqrt(data.reduce((sum, v) => sum + v * v, 0) / data.length);
      if (rms > 0.02) { spoke = true; quiet = 0; } else quiet += data.length;
      const seconds = samples / RATE;
      if ((spoke && quiet / RATE > 1.2) || seconds >= MAX_SECONDS || (!spoke && seconds > 6)) finish();
    };
    source.connect(node);
    node.connect(context.destination);
  });
}

export function VoiceButton({ disabled, onText, onError }: {
  disabled: boolean; onText: (text: string) => void; onError: (e: unknown) => void;
}) {
  const [status, setStatus] = useState<VoiceStatus | null>(null);
  const [state, setState] = useState<"idle" | "offer" | "listening" | "transcribing">("idle");
  const stopRef = useRef<(() => void) | null>(null);
  async function refresh() {
    const value = await window.alt.request<VoiceStatus>("GET", "/voice/status");
    setStatus(value);
    return value;
  }
  useEffect(() => { refresh().catch(() => {}); }, []);
  useEffect(() => {
    if (!status?.downloading) return;
    const timer = setInterval(() => refresh().catch(() => {}), 1500);
    return () => clearInterval(timer);
  }, [status?.downloading]);
  useEffect(() => { if (disabled) stopRef.current?.(); }, [disabled]);
  async function listen() {
    if (state === "listening") return stopRef.current?.();
    const current = status || (await refresh());
    if (!current.installed) return setState(current.downloading ? "idle" : "offer");
    setState("listening");
    try {
      const pcm = await record(stopRef);
      if (!pcm) return;
      setState("transcribing");
      const result = await window.alt.transcribe(pcm);
      if (result.text.trim()) onText(result.text.trim());
    } catch (e) { onError(e); }
    finally { setState("idle"); }
  }
  const downloading = !!status?.downloading;
  const title = downloading ? `Baixando voz local… ${Math.round((status?.progress || 0) * 100)}%`
    : state === "listening" ? "Ouvindo… clique para parar" : state === "transcribing" ? "Transcrevendo no seu PC…" : "Falar com a ALT (voz local)";
  return <span className="voice-control">
    <button type="button" className={"voice-button " + state} disabled={disabled || downloading || state === "transcribing"} title={title} aria-label={title} onClick={listen}>
      {state === "transcribing" || downloading ? <Loader2 size={18} className="spin" /> : state === "listening" ? <Square size={16} /> : <Mic size={18} />}
    </button>
    {state === "offer" && <div className="voice-offer" role="dialog" aria-label="Ativar voz local">
      <strong>Ativar voz local?</strong>
      <p>Baixa o Whisper small (~{status?.size_mb || 480} MB) uma vez. Sua fala é transcrita no seu PC; o áudio não vai para a internet.</p>
      {status?.error && <p className="voice-error">{status.error}</p>}
      <div>
        <button type="button" onClick={async () => {
          try { setStatus(await window.alt.request<VoiceStatus>("POST", "/voice/download")); } catch (e) { onError(e); }
          setState("idle");
        }}>Baixar</button>
        <button type="button" onClick={() => setState("idle")}>Agora não</button>
      </div>
    </div>}
  </span>;
}

// Spoken replies use a local Windows voice (pt-BR "Maria" when installed); nothing is sent online.
export function speak(text: string) {
  if (!("speechSynthesis" in window)) return;
  const clean = text.replace(/```[\s\S]*?```/g, " ").replace(/https?:\/\/\S+/g, " ").replace(/[*_#>`|]/g, "").replace(/\s+/g, " ").trim().slice(0, 700);
  if (!clean) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(clean);
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith("pt"));
  if (voice) utterance.voice = voice;
  utterance.lang = voice?.lang || "pt-BR";
  utterance.rate = 1.05;
  window.speechSynthesis.speak(utterance);
}
export function stopSpeaking() { if ("speechSynthesis" in window) window.speechSynthesis.cancel(); }
