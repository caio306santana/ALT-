import { useState } from "react";
import { Shield, Check, Wrench, AlertTriangle, FolderOpen, Download, ExternalLink } from "lucide-react";
export type ChatAction = {
  id: string;
  preview: Record<string, unknown>;
  result?: unknown;
  state: "proposed" | "complete" | "rejected" | "error" | "interrupted" | "cancelled";
};
type Data = Record<string, unknown>;
// Low-risk targets the owner can allow once and for all; never commands, closing or writing.
const REMEMBERABLE = ["open_app", "open_url", "open_folder"];
// What the tool observed, not just that it ran: only "done" earns the green badge.
const OUTCOME_LABEL: Record<string, string> = {
  done: "Concluído",
  unverified: "Não confirmado",
  failed: "Falhou",
  ask: "Precisa de escolha",
  started: "Em andamento",
};
const STATE_LABEL: Record<string, string> = {
  proposed: "Aguarda autorização",
  rejected: "Recusada",
  error: "Erro",
  interrupted: "Interrompida",
  cancelled: "Cancelada",
};
export function badge(action: ChatAction): { label: string; tone: "ok" | "warn" | "bad" | "info" | "muted" } {
  if (action.state !== "complete")
    return {
      label: STATE_LABEL[action.state] || action.state,
      tone: action.state === "proposed" ? "info" : action.state === "error" ? "bad" : "muted",
    };
  const result = (action.result || {}) as Data;
  if (action.preview.tool === "web_search" && result.found === false) return { label: "Sem resultados", tone: "warn" };
  const status = String(result.status || "done");
  return {
    label: OUTCOME_LABEL[status] || status,
    tone: status === "done" ? "ok" : status === "failed" ? "bad" : "warn",
  };
}
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
  const outcome = String(((action.result || {}) as Data).status || "done");
  const detail = String(((action.result || {}) as Data).notice || "");
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
  const state = badge(action);
  return (
    <div className="chat-action-card">
      <div className="chat-action-heading">
        <Wrench size={16} />
        <strong>{String(preview.tool).replaceAll("_", " ")}</strong>
        <span className={"small-tag outcome-" + state.tone}>{state.label}</span>
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
          {String((preview.element as Data).label || "")} ·{" "}
          {String(
            (preview.element as Data).href ||
              preview.target ||
              "",
          )}
        </p>
      )}
      {action.state !== "complete" && preview.text !== undefined && <pre>{String(preview.text)}</pre>}
      {action.state !== "complete" && preview.command !== undefined && <pre>{String(preview.command)}</pre>}
      {!!preview.external_notice && action.state !== "complete" && (
        <p className="setting-note">{String(preview.external_notice)}</p>
      )}
      {preview.diff !== undefined && (
        <details>
          <summary>Revisar alteração</summary>
          <pre>{String(preview.diff) || "Sem alteração de conteúdo."}</pre>
        </details>
      )}
      {!!preview.taint && <p className="setting-note taint-note">{String(preview.taint)}</p>}
      {action.state === "proposed" && (
        <p className="setting-note">
          {preview.critical
            ? "Gravação ampla: confirme em até 90 s. Depois disso a proposta expira e pode ser preparada de novo."
            : "Sem prazo. Execute ou recuse quando quiser; mudanças no alvo serão conferidas ao executar."}
        </p>
      )}
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
          <ResultView action={action} onError={onError} />
          <details>
            <summary>Dados técnicos</summary>
            <pre>{JSON.stringify(action.result, null, 2)}</pre>
          </details>
          <div className="button-row">
            <button className="secondary" onClick={onAnalyze}>
              <Check size={13} />
              Pedir à ALT para analisar este resultado
            </button>
            {!!(action.result as Data | undefined)?.undo_available && (
              <button className="secondary" disabled={busy} onClick={async () => {
                setBusy(true);
                try {
                  const undone = await window.alt.request<Data>("POST", `/tools/undo/${action.id}`);
                  onUpdate({ ...action, result: { ...(action.result as Data), undo_available: false, undone: undone.notice } });
                } catch (e) { onError(e); }
                finally { setBusy(false); }
              }}>Desfazer</button>
            )}
          </div>
          {!!(action.result as Data | undefined)?.undone && <p className="setting-note">{String((action.result as Data).undone)}</p>}
        </>
      )}
    </div>
  );
}

// Readable view of a confirmed result; the raw JSON stays under "Dados técnicos".
function ResultView({ action, onError }: { action: ChatAction; onError: (error: unknown) => void }) {
  const tool = String(action.preview.tool);
  const result = (action.result || {}) as Data;
  const notice = result.notice ? <p className="setting-note">{String(result.notice)}</p> : null;
  if (tool === "web_search") {
    const results = Array.isArray(result.results) ? (result.results as Data[]) : [];
    return (
      <div className="result-view">
        {results.length > 0 && (
          <ol className="source-list">
            {results.map((source, index) => (
              <li key={index}>
                <button className="link-button" title={String(source.url)} onClick={() => window.alt.openSource(action.id, String(source.url)).catch(onError)}>
                  {String(source.title || source.url)}
                  <ExternalLink size={11} />
                </button>
                <span className="source-domain">{domain(String(source.url))}</span>
                {!!source.snippet && <p>{String(source.snippet)}</p>}
              </li>
            ))}
          </ol>
        )}
        {notice}
      </div>
    );
  }
  if (tool === "read_webpage") {
    return (
      <div className="result-view">
        <p>
          <button className="link-button" onClick={() => window.alt.openSource(action.id, String(result.url)).catch(onError)}>
            {String(result.title || result.url)}
            <ExternalLink size={11} />
          </button>{" "}
          <span className="source-domain">{domain(String(result.url))}</span>
        </p>
        <p className="setting-note">
          Lida em {when(result.retrieved_at)}
          {result.truncated ? " · página longa: só o começo foi guardado." : ""} Conteúdo externo, não verificado.
        </p>
      </div>
    );
  }
  if ((tool === "write_text" || tool === "download_file") && result.path) {
    const full = String(result.path);
    const name = full.split(/[\\/]/).pop() || full;
    return (
      <div className="result-view file-result">
        <p>
          <strong>{name}</strong> · {size(Number(result.bytes))}
        </p>
        <p className="setting-note">{full}</p>
        {!!result.sha256 && <p className="setting-note">SHA256 {String(result.sha256).slice(0, 16)}…</p>}
        {tool === "download_file" && <p className="setting-note">Baixado e salvo sem abrir nem executar.</p>}
        <div className="button-row">
          <button className="secondary" onClick={() => window.alt.revealFile(action.id).catch(onError)}>
            <FolderOpen size={13} /> Mostrar na pasta
          </button>
          <button className="secondary" onClick={() => window.alt.exportFile(action.id).catch(onError)}>
            <Download size={13} /> Exportar cópia
          </button>
        </div>
        {notice}
      </div>
    );
  }
  if (tool === "run_command") {
    return (
      <div className="result-view">
        <p className="setting-note">
          Código de saída {String(result.exit_code ?? "—")}
          {result.truncated ? " · saída longa: mostrando o final." : ""}
        </p>
        {!!result.output && <pre>{String(result.output)}</pre>}
      </div>
    );
  }
  return notice;
}

function domain(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}
function when(value: unknown) {
  const date = new Date(String(value || ""));
  return Number.isNaN(date.getTime()) ? "agora" : date.toLocaleString("pt-BR");
}
function size(bytes: number) {
  if (!Number.isFinite(bytes)) return "tamanho desconhecido";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
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
