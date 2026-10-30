import { useEffect, useState } from "react";
import type { Preferences } from "../../../../packages/shared-types";
import { useVoiceStatus } from "./VoiceButton";

type Devices = { inputs: string[]; outputs: string[] };
type Update = <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;

// Voice settings: devices with a live TEST meter (Mark LVI), the Dora/Windows voice, push-to-talk and wake word.
export function VoicePanel({ prefs, update, level, onError }: { prefs: Preferences; update: Update; level: number; onError: (e: unknown) => void }) {
  const [devices, setDevices] = useState<Devices>({ inputs: [], outputs: [] });
  const [test, setTest] = useState<{ verdict: string; ok: boolean } | null>(null);
  const [testing, setTesting] = useState(false);
  const [status, refresh] = useVoiceStatus(prefs.wake_mode);
  useEffect(() => { window.alt.request<Devices>("GET", "/voice/devices").then(setDevices).catch(() => {}); }, []);
  const download = (kind: string) => window.alt.request("POST", "/voice/download", { kind }).then(refresh).catch(onError);
  const progress = (d?: { downloading: boolean; progress: number | null }) => d?.downloading ? ` · baixando ${Math.round((d.progress || 0) * 100)}%` : "";
  return (
    <>
      <div className="setting-heading">Voz</div>
      <p className="setting-note">
        Tudo roda no seu PC: o Whisper ouve, a voz Dora (ou a do Windows) fala. Segure o atalho de qualquer lugar do
        Windows para falar; com a palavra de ativação, a ALT dorme e só acorda quando chamada.
      </p>
      <label>Microfone
        <select value={prefs.voice_input || ""} onChange={(e) => update("voice_input", e.target.value)}>
          <option value="">Padrão do Windows</option>
          {devices.inputs.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
      </label>
      <div className="button-row">
        <button type="button" className="secondary" disabled={testing} onClick={async () => {
          setTesting(true); setTest(null);
          try { setTest(await window.alt.request("POST", "/voice/test")); } catch (e) { onError(e); }
          finally { setTesting(false); }
        }}>{testing ? "Fale algo…" : "Testar microfone"}</button>
        <meter className="mic-meter" min={0} max={32767} low={1500} value={testing ? level : 0} />
      </div>
      {test && <p className={"setting-note " + (test.ok ? "" : "voice-error")}>{test.verdict}</p>}
      <label>Alto-falante
        <select value={prefs.voice_output || ""} onChange={(e) => update("voice_output", e.target.value)}>
          <option value="">Padrão do Windows</option>
          {devices.outputs.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
      </label>
      <label>Voz da ALT
        <select value={prefs.voice_engine || "dora"} onChange={(e) => update("voice_engine", e.target.value as Preferences["voice_engine"])}>
          <option value="dora">Dora (natural, pt-BR){status?.dora.installed ? "" : " — precisa baixar"}</option>
          <option value="maria">Voz do Windows</option>
        </select>
      </label>
      {!status?.dora.installed && <div className="button-row">
        <button type="button" className="secondary" disabled={!!status?.dora.downloading} onClick={() => download("dora")}>
          Baixar voz Dora (~{status?.dora.size_mb || 115} MB){progress(status?.dora)}
        </button>
      </div>}
      <label>Velocidade da fala: {(prefs.voice_speed || 1.05).toFixed(2)}x
        <input type="range" min={0.8} max={1.4} step={0.05} value={prefs.voice_speed || 1.05} onChange={(e) => update("voice_speed", Number(e.target.value))} />
      </label>
      <div className="button-row">
        <button type="button" className="secondary" onClick={() => window.alt.request("POST", "/voice/speak", { text: "Olá. Eu sou a ALT. Estou pronta quando você precisar." }).catch(onError)}>Ouvir exemplo</button>
      </div>
      <label>Segurar para falar (de qualquer lugar)
        <select value={prefs.voice_ptt || "Control+Space"} onChange={(e) => update("voice_ptt", e.target.value)}>
          {["Control+Space", "Control+Alt+Space", "Alt+Shift+V", "Control+Shift+F12"].map((key) => <option key={key} value={key}>{key.replaceAll("+", " + ")}</option>)}
        </select>
      </label>
      <label>Palavra de ativação
        <select value={prefs.wake_mode || "off"} onChange={(e) => update("wake_mode", e.target.value as Preferences["wake_mode"])}>
          <option value="off">Desligada (só o atalho e o botão)</option>
          <option value="hey_jarvis">“Hey Jarvis”{status?.wake.installed ? "" : " — precisa baixar"}</option>
          <option value="ei_alt">“Ei ALT” (experimental, usa o Whisper)</option>
        </select>
      </label>
      {prefs.wake_mode === "hey_jarvis" && !status?.wake.installed && <div className="button-row">
        <button type="button" className="secondary" disabled={!!status?.wake.downloading} onClick={() => download("wake")}>
          Baixar “Hey Jarvis” (~4 MB, uso pessoal){progress(status?.wake)}
        </button>
      </div>}
      <p className="setting-note">
        Com a palavra ligada, o microfone fica aberto e o áudio é analisado só na memória; a ALT dorme sozinha depois de
        2 minutos sem fala. “Ei ALT” transcreve cada fala curta para reconhecer o nome: mais processador e pode errar.
      </p>
    </>
  );
}
