import { useState } from "react";
import { Shield, Check, Wrench, ExternalLink, AlertTriangle } from "lucide-react";
export type ChatAction = {
  id: string;
  preview: Record<string, unknown>;
  result?: unknown;
  state: "proposed" | "complete" | "rejected" | "error" | "interrupted" | "cancelled";
};
// Low-risk targets the owner can allow once and for all; never commands, closing or writing.
const REMEMBERABLE = ["open_app", "open_url", "open_folder"];
export function ChatActionCard({
  action,
  onUpdate,
  onAnalyze,
  onError,
}: {
  action: ChatAction;
  onUpdate: (action: ChatAction, previousId?: string) => void;
  onAnalyze: () => void;
  onError: (error: unknown) => void;
}) {
  const [busy, setBusy] = useState(false);
  async function approve(remember = false) {
    setBusy(true);
    try {
      const permission = await window.alt.request<{ level: number }>(
        "GET",
        "/permissions",
      );
      if (permission.level < 2) {
        onError(
          new Error(
            "Escolha Pedir aprovação ou outro modo no seletor abaixo da mensagem antes de executar.",
          ),
        );
        return;
      }
      const result = await window.alt.request<{ result: unknown }>(
        "POST",
        `/tools/approve/${action.id}`,
      );
      if (remember) await window.alt.request("POST", `/tools/remember/${action.id}`);
      onUpdate({ ...action, state: "complete", result: result.result });
    } catch (e) {
      try {
        const state=await window.alt.request<{id:string;status:string}[]>("GET","/tools/history");
        const saved=state.find(a=>a.id===action.id);
        if(saved && ["cancelled","interrupted","error"].includes(saved.status))onUpdate({...action,state:saved.status as ChatAction["state"]});
      } catch { /* Preserve the visible proposal if its state cannot be checked. */ }
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  const preview = action.preview;
  // Opening things needs no analysis: once done it collapses to one line.
  const done = action.state === "complete" ? summary(preview, action.result) : null;
  // Only an observed result gets the check mark; "unverified" and "ask" say so plainly.
  const outcome = String(((action.result || {}) as Record<string, unknown>).status || "done");
  const detail = String(((action.result || {}) as Record<string, unknown>).notice || "");
  if (done && outcome === "done")
    return (
      <div className="chat-action-done">
        <Check size={14} />
        <span>{done}</span>
      </div>
    );
  if (done && (outcome === "unverified" || outcome === "ask" || outcome === "failed"))
    return (
      <div className={"chat-action-done " + outcome}>
        <AlertTriangle size={14} />
        <span>
          {outcome === "unverified" ? "Pedido enviado, não confirmado: " : outcome === "ask" ? "Preciso que você escolha: " : "Falhou: "}
          {detail || done}
        </span>
      </div>
    );
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
      {!!preview.element && (
        <p className="setting-note">
          Elemento:{" "}
          {String((preview.element as Record<string, unknown>).label || "")} ·{" "}
          {String(
            (preview.element as Record<string, unknown>).href ||
              preview.target ||
              "",
          )}
        </p>
      )}
      {preview.text !== undefined && <pre>{String(preview.text)}</pre>}
      {preview.command !== undefined && <pre>{String(preview.command)}</pre>}
      {!!preview.external_notice && (
        <p className="setting-note">{String(preview.external_notice)}</p>
      )}
      {preview.diff !== undefined && (
        <details>
          <summary>Revisar alteração</summary>
          <pre>{String(preview.diff) || "Sem alteração de conteúdo."}</pre>
        </details>
      )}
      {!!preview.taint && <p className="setting-note taint-note">{String(preview.taint)}</p>}
      {action.state === "proposed" && <p className="setting-note">Sem prazo. Execute ou recuse quando quiser; mudanças no alvo serão conferidas ao executar.</p>}
      {(action.state === "interrupted" || action.state === "error") && <div className="button-row"><button className="secondary" disabled={busy} onClick={async () => {
        setBusy(true);
        try {
          const renewed=await window.alt.request<{id:string;preview:Record<string,unknown>}>("POST",`/tools/renew/${action.id}`);
          onUpdate({...renewed,state:"proposed"},action.id);
        } catch(e) { onError(e); }
        finally { setBusy(false); }
      }}>Preparar nova proposta para revisar</button></div>}
      {action.state === "proposed" && (
        <div className="button-row">
          <button className="primary" disabled={busy} onClick={() => approve()}>
            <Shield size={13} />
            {busy ? "Executando…" : "Aprovar e executar"}
          </button>
          {REMEMBERABLE.includes(String(preview.tool)) && (
            <button className="secondary" disabled={busy} title="Na próxima vez, este mesmo programa, site ou pasta abre sem perguntar." onClick={() => approve(true)}>
              Aprovar e sempre permitir
            </button>
          )}
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
          <details>
            <summary>Resultado da ferramenta</summary>
            <pre>{JSON.stringify(action.result, null, 2)}</pre>
          </details>
          <div className="button-row">
            <button className="secondary" onClick={onAnalyze}>
              <Check size={13} />
              Pedir à ALT para analisar este resultado
            </button>
            {!!(action.result as Record<string, unknown> | undefined)?.undo_available && (
              <button className="secondary" disabled={busy} onClick={async () => {
                setBusy(true);
                try {
                  const undone = await window.alt.request<Record<string, unknown>>("POST", `/tools/undo/${action.id}`);
                  onUpdate({ ...action, result: { ...(action.result as Record<string, unknown>), undo_available: false, undone: undone.notice } });
                } catch (e) { onError(e); }
                finally { setBusy(false); }
              }}>Desfazer</button>
            )}
          </div>
          {!!(action.result as Record<string, unknown> | undefined)?.undone && <p className="setting-note">{String((action.result as Record<string, unknown>).undone)}</p>}
        </>
      )}
    </div>
  );
}

function summary(preview: Record<string, unknown>, result: unknown) {
  const value = (result || {}) as Record<string, unknown>;
  switch (preview.tool) {
    case "open_app":
      return value.already_running
        ? `${String(preview.app)} já estava aberto: trouxe para a frente`
        : `${String(preview.app)} aberto`;
    case "open_url":
      return `Aberto no navegador: ${String(value.opened || preview.url)}`;
    case "open_folder":
      return `Pasta aberta: ${String(preview.path)}`;
    case "close_app":
      if (value.status === "ask" && Array.isArray(value.options))
        return `mais de um programa corresponde (${value.options.join(", ")})`;
      return value.status === "done" ? `${String(preview.app)} fechado` : `Fechamento solicitado: ${String(preview.app)}`;
    case "calculate":
      return `${String(preview.expression)} = ${String(value.value)}`;
    case "windows_keys":
      return `${String(preview.keys)} enviado para ${String(preview.window_title)}`;
    default:
      return null;
  }
}
