import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Check,
  Download,
  FileText,
  FolderPlus,
  Pause,
  Play,
  Search,
  Trash2,
  X,
} from "lucide-react";
import type { Model, Verification } from "../../../../packages/shared-types";
import type { ReleaseCheck } from "../bridge";
import { ChatActionCard, type ChatAction } from "./ChatActionCard";
const api = <T,>(method: string, path: string, body?: unknown) =>
  window.alt.request<T>(method, path, body);
type Feedback = {
  notify: (text: string) => void;
  onError: (e: unknown) => void;
};

type Step = {
  title: string;
  action: Record<string, unknown> & { tool: string };
  expected?: string;
};
type TaskRun = {
  id: string;
  conversation_id: string;
  goal: string;
  model: string;
  scope_id: string;
  plan: { steps: Step[] } | null;
  state:
    | "planning"
    | "draft"
    | "running"
    | "awaiting_approval"
    | "paused"
    | "completed"
    | "needs_review"
    | "error";
  cursor: number;
  history: {
    step: string;
    tool: string;
    verified: boolean;
    reason: string;
    result_excerpt: string;
  }[];
  current_proposal: { id: string; preview: Record<string, unknown> } | null;
  notice: string;
  created: string;
};
const stateLabel: Record<TaskRun["state"], string> = {
  planning: "PLANEJANDO",
  draft: "AGUARDA REVISÃO",
  running: "EXECUTANDO",
  awaiting_approval: "AGUARDA SUA APROVAÇÃO",
  paused: "PAUSADA",
  completed: "CONCLUÍDA",
  needs_review: "PRECISA DE REVISÃO",
  error: "ERRO",
};
const active = (run: TaskRun) =>
  ["planning", "running", "awaiting_approval"].includes(run.state);

export function TasksPanel({
  models,
  model,
  notify,
  onError,
  onOpenConversation,
}: Feedback & {
  models: Model[];
  model: string;
  onOpenConversation: (id: string) => void;
}) {
  const [runs, setRuns] = useState<TaskRun[]>([]),
    [selected, setSelected] = useState(""),
    [goal, setGoal] = useState(""),
    [scope, setScope] = useState(""),
    [taskModel, setTaskModel] = useState(""),
    [scopes, setScopes] = useState<{ id: string; path: string; label?: string }[]>([]),
    [replan, setReplan] = useState(false),
    [editing, setEditing] = useState(""),
    [busy, setBusy] = useState(false);
  const local = models.filter((m) => !m.name.startsWith("cloud:"));
  const chosenModel =
    taskModel || (local.some((m) => m.name === model) ? model : local[0]?.name || "");
  async function refresh() {
    const list = await api<TaskRun[]>("GET", "/tasks");
    setRuns(list);
    return list;
  }
  useEffect(() => {
    refresh().catch(onError);
    api<{ scopes: { id: string; path: string; label?: string }[] }>("GET", "/permissions")
      .then((p) => setScopes(p.scopes.filter((s) => s.id !== "windows-profile")))
      .catch(onError);
  }, []);
  const run = runs.find((r) => r.id === selected) || runs[0];
  const polling = runs.some(active);
  useEffect(() => {
    if (!polling) return;
    const id = setInterval(() => refresh().catch(() => {}), 1200);
    return () => clearInterval(id);
  }, [polling]);
  async function act(fn: () => Promise<unknown>, message?: string) {
    setBusy(true);
    try {
      await fn();
      await refresh();
      if (message) notify(message);
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page-scroll">
      <p className="setting-note">
        Cada ação segue suas regras e aprovações. Pausar não desfaz nada;
        retomar não repete ações já concluídas.
      </p>
      <div className="feature-form">
        <label>
          Objetivo
          <textarea
            rows={3}
            maxLength={1500}
            value={goal}
            placeholder="Ex.: liste os arquivos .md da pasta, leia o README e crie resumo.txt com os pontos principais."
            onChange={(e) => setGoal(e.target.value)}
          />
        </label>
        <label>
          Pasta da tarefa (ferramentas de arquivo ficam restritas a ela)
          <select value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="">Sem pasta · somente cálculo, pesquisa e apps</option>
            {scopes.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label || s.path}
              </option>
            ))}
          </select>
        </label>
        <label>
          Modelo que planeja
          <select value={chosenModel} onChange={(e) => setTaskModel(e.target.value)}>
            {local.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
        <button
          className="primary"
          disabled={busy || !goal.trim() || !chosenModel || polling}
          onClick={() =>
            act(async () => {
              const created = await api<TaskRun>("POST", "/tasks", {
                goal: goal.trim(),
                model: chosenModel,
                scope_id: scope,
              });
              setSelected(created.id);
              setGoal("");
            }, "Planejando. Nenhuma ação será executada antes da sua revisão.")
          }
        >
          Planejar tarefa
        </button>
        <p className="setting-note">
          No notebook (CPU) o planejamento pode levar alguns minutos. Escolha
          pastas em Ferramentas; o modo de execução vale como no chat.
        </p>
      </div>
      {runs.length > 0 && (
        <div className="button-row">
          {runs.slice(0, 8).map((r) => (
            <button
              key={r.id}
              className={r.id === run?.id ? "primary" : "secondary"}
              onClick={() => setSelected(r.id)}
              title={r.goal}
            >
              {r.goal.slice(0, 28)}
              {r.goal.length > 28 ? "…" : ""} · {stateLabel[r.state]}
            </button>
          ))}
        </div>
      )}
      {run && (
        <article className="info-card task-run">
          <strong>{run.goal}</strong>
          <span className="small-tag">{stateLabel[run.state]}</span>
          <p className="setting-note">{run.notice}</p>
          {run.plan && (
            <ol className="task-steps">
              {run.plan.steps.map((step, i) => {
                const done = run.history[i];
                return (
                  <li
                    key={i}
                    className={
                      done ? (done.verified ? "done" : "failed") : i === run.cursor && active(run) ? "current" : ""
                    }
                  >
                    <span>
                      {done ? (done.verified ? "✓ " : "✗ ") : ""}
                      {step.title}
                    </span>
                    <code>
                      {step.action.tool}
                      {Object.entries(step.action)
                        .filter(([k, v]) => k !== "tool" && v !== "" && !["scope_id", "window_id"].includes(k))
                        .map(([k, v]) => ` · ${k}: ${String(v).slice(0, 80)}`)
                        .join("")}
                    </code>
                    {done && (
                      <details>
                        <summary>{done.reason}</summary>
                        <pre>{done.result_excerpt}</pre>
                      </details>
                    )}
                  </li>
                );
              })}
            </ol>
          )}
          {run.state === "awaiting_approval" && run.current_proposal && (
            <ChatActionCard
              action={{ ...run.current_proposal, state: "proposed" } as ChatAction}
              onUpdate={() => refresh().catch(onError)}
              onAnalyze={() => onOpenConversation(run.conversation_id)}
              onError={onError}
            />
          )}
          <div className="button-row">
            {["draft", "paused", "needs_review", "error"].includes(run.state) && run.plan && (
              <>
                <label className="inline-check">
                  <input type="checkbox" checked={replan} onChange={(e) => setReplan(e.target.checked)} />
                  Replanejar se uma etapa falhar (até 2 vezes)
                </label>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    act(() => api("POST", `/tasks/${run.id}/start`, { allow_replan: replan }))
                  }
                >
                  <Play size={13} />
                  {run.history.length ? "Retomar" : "Iniciar plano revisado"}
                </button>
              </>
            )}
            {active(run) && (
              <button className="secondary" disabled={busy} onClick={() => act(() => api("POST", `/tasks/${run.id}/pause`), "Pausa solicitada.")}>
                <Pause size={13} />
                {run.state === "planning" ? "Cancelar planejamento" : "Pausar"}
              </button>
            )}
            <button className="text-button" onClick={() => onOpenConversation(run.conversation_id)}>
              Abrir conversa da tarefa
            </button>
          </div>
          {run.plan && !run.history.length && ["draft", "paused", "needs_review", "error"].includes(run.state) && (
            <details>
              <summary>Editar plano (JSON)</summary>
              <textarea
                className="plan-editor"
                rows={10}
                value={editing || JSON.stringify(run.plan, null, 2)}
                onChange={(e) => setEditing(e.target.value)}
              />
              <button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  act(async () => {
                    await api("PUT", `/tasks/${run.id}/plan`, JSON.parse(editing || JSON.stringify(run.plan)));
                    setEditing("");
                  }, "Plano atualizado. Nenhuma ação foi executada.")
                }
              >
                Salvar plano editado
              </button>
            </details>
          )}
        </article>
      )}
    </div>
  );
}

type Project = { id: string; name: string; created: string };
type Doc = { id: string; name: string; created: string; chunks: number };
type IndexStatus = {
  status: "idle" | "running" | "complete" | "cancelled" | "error";
  completed: number;
  total: number;
  indexed: number;
  items: number;
  error?: string;
};
type Hit = { kind: string; id: string; title: string; content: string; score: number };
type SummaryDraft = { id: string; payload: { title: string; content: string; partial: boolean } };

export function ProjectsPanel({
  conversationId,
  model,
  notify,
  onError,
  onSaved,
}: Feedback & { conversationId: string | null; model: string; onSaved: () => void }) {
  const [projects, setProjects] = useState<Project[]>([]),
    [current, setCurrent] = useState(""),
    [linked, setLinked] = useState(""),
    [docs, setDocs] = useState<Doc[]>([]),
    [drafts, setDrafts] = useState<SummaryDraft[]>([]),
    [status, setStatus] = useState<IndexStatus | null>(null),
    [name, setName] = useState(""),
    [query, setQuery] = useState(""),
    [hits, setHits] = useState<Hit[] | null>(null),
    [edits, setEdits] = useState<Record<string, string>>({}),
    [busy, setBusy] = useState(false);
  async function refresh(pid = current) {
    const list = await api<Project[]>("GET", "/projects");
    setProjects(list);
    const chosen = pid && list.some((p) => p.id === pid) ? pid : list[0]?.id || "";
    setCurrent(chosen);
    setDocs(chosen ? await api<Doc[]>("GET", `/projects/${chosen}/documents`) : []);
    setDrafts(chosen ? await api<SummaryDraft[]>("GET", `/projects/${chosen}/summaries`) : []);
    setStatus(await api<IndexStatus>("GET", "/knowledge/status"));
    if (conversationId)
      setLinked((await api<{ project_id: string }>("GET", `/conversations/${conversationId}/project`)).project_id);
  }
  useEffect(() => {
    refresh().catch(onError);
  }, [conversationId]);
  useEffect(() => {
    if (status?.status !== "running") return;
    const id = setInterval(
      () => api<IndexStatus>("GET", "/knowledge/status").then(setStatus).catch(() => {}),
      1000,
    );
    return () => clearInterval(id);
  }, [status?.status]);
  async function act(fn: () => Promise<unknown>, message?: string) {
    setBusy(true);
    try {
      await fn();
      await refresh();
      if (message) notify(message);
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  const project = projects.find((p) => p.id === current);
  return (
    <details className="info-card projects-panel" open>
      <summary>Projetos, documentos e busca semântica</summary>
      <p className="setting-note">
        Documentos PDF, DOCX, TXT e Markdown ficam locais. A busca semântica usa
        o EmbeddingGemma no Ollama; ative “Recuperação semântica” em Controle e
        regras para usá-la no chat. Conversas vinculadas a um projeto buscam só
        nele.
      </p>
      <div className="button-row">
        <input
          value={name}
          maxLength={100}
          placeholder="Nome do novo projeto"
          onChange={(e) => setName(e.target.value)}
        />
        <button
          className="secondary"
          disabled={busy || !name.trim()}
          onClick={() =>
            act(async () => {
              const created = await api<Project>("POST", "/projects", { name: name.trim() });
              setName("");
              setCurrent(created.id);
              await refresh(created.id);
            }, "Projeto criado.")
          }
        >
          <FolderPlus size={14} />
          Criar projeto
        </button>
      </div>
      {projects.length > 0 && (
        <div className="feature-form">
          <label>
            Projeto
            <select value={current} onChange={(e) => refresh(e.target.value).catch(onError)}>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {project && (
        <>
          <div className="button-row">
            <button
              className="secondary"
              disabled={busy}
              onClick={() =>
                act(async () => {
                  const result = await window.alt.importDocument(project.id);
                  if (result)
                    notify(
                      result.duplicate
                        ? "Este documento já estava no projeto."
                        : `Documento importado em ${result.chunks} trechos. Indexe para a busca semântica.`,
                    );
                })
              }
            >
              <FileText size={14} />
              Importar documento
            </button>
            {conversationId && (
              <button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  act(
                    () =>
                      api("PUT", `/conversations/${conversationId}/project`, {
                        project_id: linked === project.id ? "" : project.id,
                      }),
                    linked === project.id ? "Conversa desvinculada." : `Conversa atual vinculada a ${project.name}.`,
                  )
                }
              >
                {linked === project.id ? "Desvincular conversa atual" : "Vincular conversa atual"}
              </button>
            )}
            {conversationId && linked === project.id && (
              <button
                className="secondary"
                disabled={busy || !model || model.startsWith("cloud:")}
                onClick={() =>
                  act(
                    () => api("POST", "/projects/summaries/draft", { conversation_id: conversationId, model }),
                    "Rascunho de resumo gerado. Revise antes de salvar.",
                  )
                }
              >
                Gerar resumo da conversa para o projeto
              </button>
            )}
            <button
              className="text-button"
              disabled={busy}
              onClick={() => act(() => api("DELETE", `/projects/${project.id}`), "Projeto e documentos removidos; memórias aprovadas foram mantidas.")}
            >
              <Trash2 size={13} />
              Excluir projeto
            </button>
          </div>
          {docs.map((d) => (
            <p className="setting-note" key={d.id}>
              <FileText size={12} /> {d.name} · {d.chunks} trechos ·{" "}
              {new Date(d.created).toLocaleDateString()}{" "}
              <button className="text-button" onClick={() => act(() => api("DELETE", `/documents/${d.id}`))}>
                remover
              </button>
            </p>
          ))}
          {drafts.map((d) => (
            <article className="info-card" key={d.id}>
              <strong>Resumo para revisar{d.payload.partial ? " · parcial" : ""}</strong>
              <textarea
                rows={6}
                maxLength={6000}
                value={edits[d.id] ?? d.payload.content}
                onChange={(e) => setEdits({ ...edits, [d.id]: e.target.value })}
              />
              <div className="button-row">
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    act(async () => {
                      await api("POST", `/projects/summaries/${d.id}/approve`, {
                        title: (project.name + " · " + d.payload.title).slice(0, 120),
                        content: edits[d.id] ?? d.payload.content,
                        category: "projeto",
                      });
                      onSaved();
                    }, "Resumo salvo como memória do projeto.")
                  }
                >
                  <Check size={13} />
                  Salvar como memória
                </button>
                <button className="secondary" onClick={() => act(() => api("POST", `/projects/summaries/${d.id}/discard`))}>
                  <X size={13} />
                  Descartar
                </button>
              </div>
            </article>
          ))}
        </>
      )}
      <div className="button-row">
        <button
          className="secondary"
          disabled={busy || status?.status === "running"}
          onClick={() => act(() => api("POST", "/knowledge/index"), "Indexação iniciada.")}
        >
          Indexar memórias e documentos
        </button>
        {status?.status === "running" && (
          <button className="text-button" onClick={() => api("POST", "/knowledge/index/cancel").catch(onError)}>
            Cancelar
          </button>
        )}
        {status && (
          <span className="setting-note">
            {status.status === "running"
              ? `Indexando ${status.completed}/${status.total}…`
              : `${status.indexed} vetores · ${status.items} itens${status.status === "error" ? " · erro: " + status.error : ""}`}
          </span>
        )}
      </div>
      <div className="button-row">
        <input
          value={query}
          maxLength={1500}
          placeholder="Buscar por significado nas memórias e documentos"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && query.trim())
              api<Hit[]>("POST", "/knowledge/search", { query, project_id: current }).then(setHits).catch(onError);
          }}
        />
        <button
          className="secondary"
          disabled={!query.trim()}
          onClick={() => api<Hit[]>("POST", "/knowledge/search", { query, project_id: current }).then(setHits).catch(onError)}
        >
          <Search size={14} />
          Buscar
        </button>
      </div>
      {hits && !hits.length && <p className="setting-note">Nada relevante. Itens novos ou editados precisam ser indexados.</p>}
      {hits?.map((h) => (
        <article className="info-card" key={h.kind + h.id}>
          <strong>
            {h.title} <span className="small-tag">{h.kind === "chunk" ? "DOCUMENTO" : "MEMÓRIA"} · {h.score.toFixed(2)}</span>
          </strong>
          <p className="model-answer">{h.content.slice(0, 600)}</p>
        </article>
      ))}
    </details>
  );
}

export function VerificationNote({ verification }: { verification?: Verification }) {
  if (!verification || (!verification.calculations.length && !verification.sources.length)) return null;
  const wrong = verification.calculations.filter((c) => !c.ok);
  const unconfirmed = verification.sources.filter((s) => !s.confirmed);
  return (
    <details className={`verification-note ${verification.issues ? "warning" : ""}`}>
      <summary>
        {verification.issues
          ? `Conferência: ${wrong.length ? wrong.length + " conta(s) incorreta(s)" : ""}${wrong.length && unconfirmed.length ? " · " : ""}${unconfirmed.length ? unconfirmed.length + " link(s) sem fonte confirmada" : ""}`
          : `Conferência: ${verification.calculations.length} conta(s) e ${verification.sources.length} link(s) ok`}
      </summary>
      {verification.calculations.map((c, i) => (
        <p key={i}>
          {c.ok ? "✓" : "✗"} {c.claim}
          {!c.ok && ` → resultado correto: ${c.actual.toLocaleString("pt-BR", { maximumFractionDigits: 6 })}`}
        </p>
      ))}
      {verification.sources.map((s) => (
        <p key={s.url}>
          {s.confirmed ? "✓ veio de resultado confirmado:" : "⚠ não veio de pesquisa/leitura confirmada:"} {s.url}
        </p>
      ))}
      <p className="setting-note">{verification.notice}</p>
    </details>
  );
}

export function UpdateNotice({ onError }: { onError: (e: unknown) => void }) {
  const [release, setRelease] = useState<ReleaseCheck | null>(null),
    [progress, setProgress] = useState<{ received: number; total: number } | null>(null),
    [verified, setVerified] = useState(false),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    const show = (r: ReleaseCheck) => {
      if (localStorage.getItem("alt-dismissed-update") !== r.version) setRelease(r);
    };
    const manual = (e: Event) => show((e as CustomEvent<ReleaseCheck>).detail);
    window.addEventListener("alt-update", manual);
    const stop = window.alt.onUpdate((kind, info) => {
      if (kind === "progress") setProgress(info as { received: number; total: number });
      else show(info as ReleaseCheck);
    });
    return () => {
      stop();
      window.removeEventListener("alt-update", manual);
    };
  }, []);
  if (!release?.available) return null;
  const mb = (n: number) => (n / 1024 / 1024).toFixed(0);
  return (
    <div className="update-notice" role="dialog" aria-label="Nova versão disponível">
      <div className="update-heading">
        <Download size={18} />
        <strong>Nova versão disponível · {release.version}</strong>
        <button
          aria-label="Lembrar depois"
          className="icon-btn"
          onClick={() => {
            localStorage.setItem("alt-dismissed-update", release.version || "");
            setRelease(null);
          }}
        >
          <X size={14} />
        </button>
      </div>
      <p className="setting-note">
        {release.name}
        {release.published_at && ` · publicada em ${new Date(release.published_at).toLocaleDateString()}`}
      </p>
      <div className="update-notes">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{release.notes || "Sem notas de versão."}</ReactMarkdown>
      </div>
      {release.downloadable ? (
        <div className="button-row">
          {!verified ? (
            <button
              className="primary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await window.alt.downloadUpdate();
                  setVerified(true);
                } catch (e) {
                  onError(e);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <Download size={14} />
              {busy
                ? progress
                  ? `Baixando ${mb(progress.received)}/${mb(progress.total)} MB…`
                  : "Baixando…"
                : `Baixar${release.installer ? ` (${mb(release.installer.size)} MB)` : ""}`}
            </button>
          ) : (
            <button className="primary" onClick={() => window.alt.applyUpdate().catch(onError)}>
              <Check size={14} />
              Assinatura conferida · instalar e reiniciar
            </button>
          )}
          <button className="secondary" onClick={() => window.alt.openReleases()}>
            Ver no GitHub
          </button>
        </div>
      ) : (
        <p className="setting-note">
          Esta release não traz instalador e manifesto assinados. Baixe pelo GitHub.
        </p>
      )}
      <p className="setting-note">
        Download direto do GitHub; a instalação só é liberada após conferir a
        assinatura Ed25519 e o SHA-256. Isso não substitui certificado Windows.
      </p>
    </div>
  );
}
