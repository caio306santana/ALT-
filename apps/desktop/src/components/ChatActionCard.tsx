import { useState } from "react";
import { Shield, Check, Wrench, ExternalLink } from "lucide-react";
export type ChatAction = {
  id: string;
  preview: Record<string, unknown>;
  result?: unknown;
  state: "proposed" | "complete" | "rejected" | "error";
};
export function ChatActionCard({
  action,
  onUpdate,
  onAnalyze,
  onError,
}: {
  action: ChatAction;
  onUpdate: (action: ChatAction) => void;
  onAnalyze: () => void;
  onError: (error: unknown) => void;
}) {
  const [busy, setBusy] = useState(false);
  async function approve() {
    setBusy(true);
    try {
      const permission = await window.alt.request<{ level: number }>(
        "GET",
        "/permissions",
      );
      if (permission.level < 2) {
        onError(
          new Error(
            "Escolha um modo de autorização no painel Ferramentas antes de executar.",
          ),
        );
        return;
      }
      const result = await window.alt.request<{ result: unknown }>(
        "POST",
        `/tools/approve/${action.id}`,
      );
      onUpdate({ ...action, state: "complete", result: result.result });
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  const preview = action.preview;
  return (
    <div className="chat-action-card">
      <div className="chat-action-heading">
        <Wrench size={16} />
        <strong>{String(preview.tool).replaceAll("_", " ")}</strong>
        <span className="small-tag">
          {action.state === "complete"
            ? "CONFIRMADO"
            : action.state === "proposed"
              ? "AGUARDA AUTORIZAÇÃO"
              : action.state.toUpperCase()}
        </span>
      </div>
      <p>
        {String(
          preview.query ||
            preview.path ||
            preview.url ||
            preview.app ||
            preview.expression ||
            "Ação proposta pela ALT",
        )}
      </p>
      {!!preview.external_notice && (
        <p className="setting-note">{String(preview.external_notice)}</p>
      )}
      {preview.diff !== undefined && (
        <details>
          <summary>Revisar alteração</summary>
          <pre>{String(preview.diff) || "Sem alteração de conteúdo."}</pre>
        </details>
      )}
      {action.state === "proposed" && (
        <div className="button-row">
          <button className="primary" disabled={busy} onClick={approve}>
            <Shield size={13} />
            {busy ? "Executando…" : "Aprovar e executar"}
          </button>
          <button
            className="secondary"
            onClick={() =>
              window.alt
                .request("POST", `/tools/reject/${action.id}`)
                .then(() => onUpdate({ ...action, state: "rejected" }))
                .catch(onError)
            }
          >
            Recusar
          </button>
        </div>
      )}
      {action.state === "complete" && (
        <>
          <details open>
            <summary>Resultado da ferramenta</summary>
            <pre>{JSON.stringify(action.result, null, 2)}</pre>
          </details>
          <button className="secondary" onClick={onAnalyze}>
            <Check size={13} />
            Pedir à ALT para analisar este resultado
          </button>
        </>
      )}
    </div>
  );
}
