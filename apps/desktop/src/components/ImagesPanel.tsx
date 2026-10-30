import { useEffect, useState } from "react";

type Status = {
  provider: "" | "local" | "openai";
  hardware: { label: string; variant: string; cpu_mode: boolean; cards: string[] };
  local: {
    installed: boolean; installing: boolean; running: boolean; stage: string; done: number; total: number;
    error: string; disk_free_gb: number; needed_gb: number; model: string; license: string;
  };
  api: { configured: boolean; model: string };
};

// Image generation: on this PC (graphics card or processor) installed from here, or a paid API.
export function ImagesPanel({ onError }: { onError: (e: unknown) => void }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => window.alt.request<Status>("GET", "/images/status").then(setStatus).catch(() => {});
  useEffect(() => {
    load();
    const timer = window.setInterval(() => { if (status?.local.installing) load(); }, 2000);
    return () => window.clearInterval(timer);
  }, [status?.local.installing]);
  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    try { const next = await action(); if (next && typeof next === "object" && "local" in next) setStatus(next as Status); else await load(); }
    catch (e) { onError(e); }
    finally { setBusy(false); }
  };
  const choose = (provider: Status["provider"]) => run(() => window.alt.request("PUT", "/images/provider", { provider }));
  if (!status?.local) return null;
  const local = status.local;
  const percent = local.total ? Math.round((local.done / local.total) * 100) : null;
  return (
    <>
      <div className="setting-heading">Imagens</div>
      <p className="setting-note">
        Peça no chat: "gera uma imagem de um gato astronauta". A ALT usa a opção escolhida abaixo.
      </p>
      <label>Como gerar
        <select value={status.provider} onChange={(e) => choose(e.target.value as Status["provider"])} disabled={busy}>
          <option value="">Desligado</option>
          <option value="local" disabled={!local.installed}>
            Neste PC — {status.hardware.cpu_mode ? "processador (lento)" : "placa de vídeo"}{local.installed ? "" : " (instale abaixo)"}
          </option>
          <option value="openai" disabled={!status.api.configured}>API paga da OpenAI{status.api.configured ? "" : " (salve a chave abaixo)"}</option>
        </select>
      </label>

      <div className="setting-heading small">1 e 2 · Neste PC (grátis, privado)</div>
      <p className="setting-note">
        Placa detectada: <b>{status.hardware.label}</b>.{" "}
        {status.hardware.cpu_mode
          ? "Sem placa compatível: gera pelo processador, o que leva minutos por imagem. No PC com placa de vídeo é bem mais rápido."
          : "Gera pela placa de vídeo, em segundos."}{" "}
        Usa o ComfyUI oficial e o modelo SD-Turbo (512×512). Precisa de ~{local.needed_gb} GB livres (há {local.disk_free_gb} GB).
      </p>
      {local.installing ? (
        <div className="button-row">
          <span className="setting-note">{local.stage}{percent !== null ? ` · ${percent}%` : "…"}</span>
          <button type="button" className="secondary" onClick={() => run(() => window.alt.request("POST", "/images/install/cancel"))}>Cancelar</button>
        </div>
      ) : local.installed ? (
        <div className="button-row">
          <span className="setting-note">{local.running ? "Gerador ligado." : "Instalado. Liga sozinho no primeiro pedido."}</span>
          {local.running
            ? <button type="button" className="secondary" disabled={busy} onClick={() => run(() => window.alt.request("POST", "/images/stop"))}>Desligar gerador</button>
            : <button type="button" className="secondary" disabled={busy} onClick={() => run(() => window.alt.request("POST", "/images/start"))}>Ligar agora</button>}
        </div>
      ) : (
        <div className="button-row">
          <button type="button" className="primary" disabled={busy || local.disk_free_gb < local.needed_gb} onClick={() => run(() => window.alt.installImages())}>
            Instalar gerador local
          </button>
        </div>
      )}
      {local.error && <p className="setting-note voice-error">{local.error}</p>}
      <p className="setting-note">{local.license}</p>

      <div className="setting-heading small">3 · API paga (OpenAI)</div>
      <p className="setting-note">
        Rápida e com imagens maiores (1024×1024), mas cada imagem é cobrada na sua conta OpenAI e a descrição sai do seu PC.
        Modelo: {status.api.model}.
      </p>
      {status.api.configured ? (
        <div className="button-row">
          <span className="setting-note">Chave salva no cofre do Windows.</span>
          <button type="button" className="secondary" disabled={busy} onClick={() => run(() => window.alt.setOpenAIKey(""))}>Remover chave</button>
        </div>
      ) : (
        <div className="button-row">
          <input type="password" placeholder="sk-..." value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" />
          <button type="button" className="secondary" disabled={busy || key.length < 30} onClick={() => run(async () => { const r = await window.alt.setOpenAIKey(key); setKey(""); return r; })}>
            Salvar chave
          </button>
        </div>
      )}
    </>
  );
}
