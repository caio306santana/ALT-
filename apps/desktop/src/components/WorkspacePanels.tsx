import { useEffect, useState } from "react";
import type { Model, Conversation } from "../../../../packages/shared-types";
import { ChatActionCard, type ChatAction } from "./ChatActionCard";
import { RemotePanel } from "./RemotePanel";
const api = <T,>(method: string, path: string, body?: unknown) =>
  window.alt.request<T>(method, path, body);
type Feedback = {
  notify: (text: string) => void;
  onError: (e: unknown) => void;
};
type Decision = "deny" | "ask" | "allow";
export type OwnerPolicy = {
  rules: string;
  memory_recall: "manual" | "automatic" | "semantic";
  auto_project_summaries: boolean;
  conversation_summaries?: boolean;
  capabilities: Record<string, Decision>;
};
type PolicyState = {
  policy: OwnerPolicy;
  effective_prompt: string;
  boundaries: { source: string; text: string }[];
};
const labels: Record<string, string> = {
  calculate: "Cálculos",
  files_read: "Leitura e busca de arquivos",
  files_write: "Criar e editar arquivos",
  apps: "Aplicativos e pastas",
  internet: "Pesquisa e leitura na internet",
  browser_navigation: "Abrir e ler no navegador ALT",
  browser_interaction: "Clicar e digitar no navegador ALT",
  downloads: "Baixar arquivos da internet",
  images: "Gerar imagens",
  windows_read: "Ler janelas do Windows autorizadas",
  windows_control: "Clicar e digitar em janelas autorizadas",
  shell: "Comandos do PowerShell (sempre com cartão de aprovação)",
};

type Remembered = { id: string; tool: string; target: string; created: string };
const rememberedLabel: Record<string, string> = { open_app: "Programa", open_url: "Site", open_folder: "Pasta" };
// Targets the owner allowed with "Aprovar e sempre permitir"; removing one brings the card back.
function RememberedApprovals({ onError }: { onError: (e: unknown) => void }) {
  const [rows, setRows] = useState<Remembered[]>([]);
  const load = () => api<Remembered[]>("GET", "/approvals/remembered").then(setRows).catch(onError);
  useEffect(() => { load(); }, []);
  return (
    <>
      <h3>Sempre permitidos: {rows.length}</h3>
      <p className="setting-note">
        Abrem sem perguntar nos modos Pedir aprovação e Usar minhas regras. Comandos, fechar programas,
        gravar arquivos e downloads nunca entram aqui.
      </p>
      {rows.length > 0 && (
        <div className="program-chips">
          {rows.map((row) => (
            <span key={row.id} className="attachment-chip">
              <span>{rememberedLabel[row.tool] || row.tool}: {row.target.replace("catalog:", "")}</span>
              <button type="button" aria-label={"Remover " + row.target} onClick={() => api("DELETE", "/approvals/remembered/" + row.id).then(load).catch(onError)}>×</button>
            </span>
          ))}
        </div>
      )}
    </>
  );
}

export function OwnerControlPanel({ notify, onError }: Feedback) {
  const [state, setState] = useState<PolicyState | null>(null),
    [draft, setDraft] = useState<OwnerPolicy | null>(null),
    [busy, setBusy] = useState(false),
    [programs, setPrograms] = useState<
      { id: string; name: string; path?: string }[]
    >([]),
    [installed, setInstalled] = useState<{
      level: number;
      programs: string[];
    } | null>(null),
    [programQuery, setProgramQuery] = useState("");
  async function refresh() {
    const p = await api<PolicyState>("GET", "/policy");
    setState(p);
    setDraft(p.policy);
    setPrograms(await api("GET", "/programs"));
    setInstalled(await api("GET", "/programs/installed"));
  }
  const fullAccess = installed?.level === 4,
    query = programQuery.trim().toLocaleLowerCase(),
    matching = (installed?.programs || []).filter((name) =>
      name.toLocaleLowerCase().includes(query),
    );
  useEffect(() => {
    refresh().catch(onError);
  }, []);
  if (!state || !draft)
    return <div className="page-scroll">Carregando suas regras…</div>;
  return (
    <div className="page-scroll owner-control">
      <div className="security-hero">
        <h2>Suas regras. À vista.</h2>
        <p>
          Defina o comportamento da ALT e o que ela pode fazer. As autorizações
          ficam salvas até você alterar ou revogar.
        </p>
      </div>
      <div className="feature-form">
        <label>
          Regras de conversa definidas por você
          <textarea
            rows={4}
            maxLength={1500}
            value={draft.rules}
            placeholder="Ex.: discuta temas controversos com franqueza, explicite incertezas e questione meus argumentos."
            onChange={(e) => setDraft({ ...draft, rules: e.target.value })}
          />
        </label>
        <label>
          Recuperação de memórias
          <select
            value={draft.memory_recall}
            onChange={(e) =>
              setDraft({
                ...draft,
                memory_recall: e.target.value as OwnerPolicy["memory_recall"],
              })
            }
          >
            <option value="manual">Somente as que eu selecionar</option>
            <option value="automatic">
              Recuperar memórias relacionadas à mensagem (por termos)
            </option>
            <option value="semantic">
              Recuperação semântica de memórias e documentos (EmbeddingGemma)
            </option>
          </select>
        </label>
        <label className="inline-check">
          <input
            type="checkbox"
            checked={!!draft.auto_project_summaries}
            onChange={(e) =>
              setDraft({ ...draft, auto_project_summaries: e.target.checked })
            }
          />
          Gerar rascunhos de resumo de conversas vinculadas a projetos (a cada
          12 mensagens, sempre para revisão)
        </label>
        <label className="inline-check">
          <input
            type="checkbox"
            checked={draft.conversation_summaries !== false}
            onChange={(e) =>
              setDraft({ ...draft, conversation_summaries: e.target.checked })
            }
          />
          Em conversas longas, resumir as mensagens antigas que não cabem mais no
          contexto (as originais continuam salvas; o resumo não vira memória)
        </label>
        <p className="setting-note">
          A semântica busca por significado nos itens indexados em Memória e
          volta para a busca por termos se o EmbeddingGemma não estiver
          disponível. O chat informa o que entrou; a prévia de nuvem mostra o
          contexto exato.
        </p>
        {Object.entries(draft.capabilities).map(([key, value]) => (
          <label key={key}>
            {labels[key] || key}
            <select
              value={value}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  capabilities: {
                    ...draft.capabilities,
                    [key]: e.target.value as Decision,
                  },
                })
              }
            >
              <option value="deny">Bloquear</option>
              <option value="ask">
                Pedir aprovação · leitura já autorizada segue o escopo
              </option>
              <option value="allow">
                Permitir automaticamente nos modos 3/4
              </option>
            </select>
          </label>
        ))}
        <p className="setting-note">
          Observação não executa. No modo 4 (acesso total), tudo que não
          estiver bloqueado aqui executa sem pedir aprovação, menos comandos do
          PowerShell, que sempre mostram um cartão. STOP revoga na hora.
          Arquivos de credenciais e privilégios de administrador ficam sempre de
          fora; downloads nunca são executados.
        </p>
        <button
          className="primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              const saved = await window.alt.savePolicy(draft);
              if (saved) {
                await refresh();
                notify("Suas regras foram salvas.");
              }
            } catch (e) {
              onError(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Salvando…" : "Revisar e salvar minhas regras"}
        </button>
      </div>
      <h3>O que cada camada controla</h3>
      {state.boundaries.map((b) => (
        <article className="info-card" key={b.source}>
          <strong>{b.source}</strong>
          <p>{b.text}</p>
        </article>
      ))}
      <details className="info-card">
        <summary>Ver instrução efetiva de conversa</summary>
        <p className="setting-note">
          Sem histórico ou memórias selecionadas. Regras de operação são
          aplicadas pelo código; o modelo não pode conceder permissão por texto.
        </p>
        <pre className="prompt-preview">{state.effective_prompt}</pre>
      </details>
      <RememberedApprovals onError={onError} />
      <RemotePanel onError={onError} />
      {fullAccess ? (
        <>
          <h3>
            Programas instalados (detectados automaticamente):{" "}
            {installed?.programs.length ?? 0}
          </h3>
          <p className="setting-note">
            No acesso total a ALT abre qualquer um pelo nome, como “abre o
            Spotify”. Não é preciso registrar nada.
          </p>
          <input
            className="program-search"
            value={programQuery}
            placeholder="Procurar programa…"
            onChange={(e) => setProgramQuery(e.target.value)}
          />
          <div className="program-chips">
            {matching.slice(0, 80).map((name) => (
              <span className="small-tag" key={name}>
                {name}
              </span>
            ))}
            {matching.length > 80 && (
              <span className="setting-note">+{matching.length - 80}</span>
            )}
          </div>
        </>
      ) : (
        <>
          <h3>Aplicativos registrados</h3>
          <p className="setting-note">
            Fora do acesso total, a ALT só abre os aplicativos registrados aqui.
          </p>
          <button
            className="secondary"
            onClick={() =>
              window.alt
                .chooseProgram()
                .then(() => refresh())
                .catch(onError)
            }
          >
            Escolher aplicativo .exe
          </button>
        </>
      )}
      {!fullAccess && programs.map((p) => (
        <article className="info-card" key={p.id}>
          <strong>{p.name}</strong>
          <p>{p.path || "Aplicativo do Windows"}</p>
          <code>{p.id}</code>
          {p.path && (
            <button
              className="text-button"
              onClick={() =>
                api("DELETE", `/programs/${p.id}`)
                  .then(() => refresh())
                  .catch(onError)
              }
            >
              Remover autorização
            </button>
          )}
        </article>
      ))}
    </div>
  );
}

export function ContinuityPanel({
  conversationId,
  model,
  notify,
  onError,
  onSaved,
}: Feedback & {
  conversationId: string | null;
  model: string;
  onSaved: () => void;
}) {
  const [conversations, setConversations] = useState<Conversation[]>([]),
    [cid, setCid] = useState(conversationId || ""),
    [draft, setDraft] = useState<{
      id: string;
      title: string;
      content: string;
      partial: boolean;
    } | null>(null),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Conversation[]>("GET", "/conversations")
      .then((items) => {
        setConversations(items);
        if (!cid && items.length) setCid(items[0].id);
      })
      .catch(onError);
  }, []);
  return (
    <details className="info-card continuity-card">
      <summary>Resumo de continuidade · retomar projetos</summary>
      <p>
        O modelo local propõe um resumo. Você pode corrigir o texto antes de
        salvá-lo como memória.
      </p>
      <select
        value={cid}
        onChange={(e) => {
          setCid(e.target.value);
          setDraft(null);
        }}
      >
        <option value="">Escolha uma conversa</option>
        {conversations.map((c) => (
          <option key={c.id} value={c.id}>
            {c.title}
          </option>
        ))}
      </select>
      <button
        className="secondary"
        disabled={busy || !cid || !model || model.startsWith("cloud:")}
        onClick={async () => {
          setBusy(true);
          try {
            setDraft(
              await api("POST", "/continuity/draft", {
                conversation_id: cid,
                model,
              }),
            );
          } catch (e) {
            onError(e);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy
          ? "Gerando resumo local…"
          : "Gerar rascunho com o modelo local selecionado"}
      </button>
      {model.startsWith("cloud:") && (
        <p className="setting-note">
          Selecione um modelo Ollama para gerar resumos sem enviar a conversa à
          nuvem.
        </p>
      )}
      {draft && (
        <div className="feature-form">
          <label>
            Título
            <input
              value={draft.title}
              maxLength={120}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            />
          </label>
          <label>
            Revise decisões, preferências e próximos passos
            <textarea
              rows={8}
              value={draft.content}
              maxLength={6000}
              onChange={(e) => setDraft({ ...draft, content: e.target.value })}
            />
          </label>
          {draft.partial && (
            <p className="setting-note">
              Rascunho feito somente com o trecho recente que coube no contexto.
              Confira o histórico completo antes de aprovar.
            </p>
          )}
          <button
            className="primary"
            disabled={busy || !draft.content.trim()}
            onClick={async () => {
              setBusy(true);
              try {
                await api("POST", `/continuity/approve/${draft.id}`, {
                  title: draft.title,
                  content: draft.content,
                  category: "contexto",
                  enabled: true,
                });
                setDraft(null);
                onSaved();
                notify("Resumo revisado salvo como memória.");
              } catch (e) {
                onError(e);
              } finally {
                setBusy(false);
              }
            }}
          >
            Salvar resumo revisado como memória
          </button>
        </div>
      )}
    </details>
  );
}

type Evaluation = {
  id: string;
  status: string;
  created: string;
  models: { name: string }[];
  cases: { id: string; label: string; prompt: string }[];
  results: {
    model: string;
    case: string;
    reply: string;
    status: string;
    seconds: number;
    tokens_per_second: number | null;
    output_limited?: boolean;
    error?: string;
  }[];
  ratings: Record<string, Record<string, string | number>>;
  notice: string;
  error?: string;
};
export function EvaluationPanel({
  models,
  notify,
  onError,
}: Feedback & { models: Model[] }) {
  const [selected, setSelected] = useState<string[]>([]),
    [runs, setRuns] = useState<Evaluation[]>([]),
    [busy, setBusy] = useState(false);
  const local = models.filter((m) => !m.name.startsWith("cloud:"));
  async function refresh() {
    const data = await api<{ runs: Evaluation[] }>("GET", "/evaluations");
    setRuns(data.runs);
  }
  useEffect(() => {
    refresh().catch(onError);
    const id = setInterval(() => refresh().catch(onError), 3000);
    return () => clearInterval(id);
  }, []);
  return (
    <details className="info-card evaluation-panel">
      <summary>Laboratório · comparar modelos locais</summary>
      <p>
        Mesmos prompts sintéticos de português, personalidade, discussão e
        precisão. Sem memórias pessoais, pesquisa ou nuvem. Uma rodada por vez;
        pode levar minutos em CPU.
      </p>
      {local.map((m) => (
        <label className="inline-check" key={m.name}>
          <input
            type="checkbox"
            checked={selected.includes(m.name)}
            onChange={(e) =>
              setSelected(
                e.target.checked
                  ? [...selected, m.name].slice(0, 3)
                  : selected.filter((n) => n !== m.name),
              )
            }
          />
          {m.name}
        </label>
      ))}
      <div className="button-row">
        <button
          className="secondary"
          disabled={
            busy || !selected.length || runs.some((r) => r.status === "running")
          }
          onClick={async () => {
            setBusy(true);
            try {
              await api("POST", "/evaluations", { models: selected });
              await refresh();
              notify(
                selected.length === 1
                  ? "Linha de base iniciada. Selecione dois modelos para comparação lado a lado."
                  : "Comparação local iniciada.",
              );
            } catch (e) {
              onError(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          Iniciar avaliação
        </button>
        <button
          className="text-button"
          onClick={() =>
            api("POST", "/evaluations/cancel")
              .then(() => notify("Cancelamento solicitado."))
              .catch(onError)
          }
        >
          Cancelar avaliação
        </button>
      </div>
      {runs.map((run) => (
        <article className="evaluation-run" key={run.id}>
          <h4>
            {new Date(run.created).toLocaleString()} · {run.status}
          </h4>
          <p className="setting-note">{run.notice}</p>
          {run.error && <p>{run.error}</p>}
          <div className="comparison-grid">
            {run.models.map((model) => (
              <div className="info-card" key={model.name}>
                <strong>{model.name}</strong>
                {run.results
                  .filter((r) => r.model === model.name)
                  .map((result) => (
                    <details key={result.case}>
                      <summary>
                        {run.cases.find((c) => c.id === result.case)?.label} ·{" "}
                        {result.seconds}s · {result.tokens_per_second ?? "—"}{" "}
                        tokens/s · {result.status}
                        {result.output_limited
                          ? " · limite de saída atingido"
                          : ""}
                      </summary>
                      <p className="setting-note">
                        {run.cases.find((c) => c.id === result.case)?.prompt}
                      </p>
                      <p className="model-answer">
                        {result.reply || result.error || "Sem texto"}
                      </p>
                    </details>
                  ))}
                {run.status !== "running" && (
                  <RatingForm
                    current={run.ratings[model.name]}
                    onSave={(values) =>
                      api("PUT", `/evaluations/${run.id}/rating`, {
                        model: model.name,
                        ...values,
                      })
                        .then(() => refresh())
                        .catch(onError)
                    }
                  />
                )}
              </div>
            ))}
          </div>
        </article>
      ))}
    </details>
  );
}
function RatingForm({
  current,
  onSave,
}: {
  current?: Record<string, string | number>;
  onSave: (values: Record<string, string | number>) => void;
}) {
  const [rating, setRating] = useState<Record<string, string | number>>(
    current || {
      portuguese: 3,
      personality: 3,
      usefulness: 3,
      freedom: 3,
      notes: "",
    },
  );
  return (
    <details>
      <summary>Sua avaliação · notas de 1 a 5</summary>
      {Object.entries({
        portuguese: "Português",
        personality: "Personalidade",
        usefulness: "Qualidade e utilidade",
        freedom: "Liberdade de discussão",
      }).map(([key, label]) => (
        <label key={key}>
          {label}
          <select
            value={rating[key]}
            onChange={(e) =>
              setRating({ ...rating, [key]: Number(e.target.value) })
            }
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
      ))}
      <textarea
        rows={2}
        maxLength={1000}
        value={rating.notes}
        placeholder="Suas observações; notas são suas, não um benchmark automático."
        onChange={(e) => setRating({ ...rating, notes: e.target.value })}
      />
      <button className="secondary" onClick={() => onSave(rating)}>
        Salvar minhas notas
      </button>
    </details>
  );
}

type BrowserSnapshot = {
  snapshot_id: string;
  url: string;
  title: string;
  text: string;
  elements: {
    id: string;
    tag: string;
    type: string;
    label: string;
    href?: string;
  }[];
};
export function BrowserPanel({
  notify,
  onError,
  onAnalyze,
}: Feedback & { onAnalyze: (id: string) => void }) {
  const [url, setUrl] = useState("https://docs.ollama.com/"),
    [snapshot, setSnapshot] = useState<BrowserSnapshot | null>(null),
    [action, setAction] = useState<ChatAction | null>(null),
    [target, setTarget] = useState(""),
    [text, setText] = useState(""),
    [busy, setBusy] = useState(false);
  async function propose(tool: string, extra: Record<string, string> = {}) {
    setBusy(true);
    try {
      const p = await api<{ id: string; preview: Record<string, unknown> }>(
        "POST",
        "/tools/propose",
        { tool, ...extra },
      );
      setAction({ ...p, state: "proposed" });
      notify("Confira o cartão e aprove a ação.");
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page-scroll browser-panel">
      <div className="security-hero">
        <h2>Navegar, observar, agir.</h2>
        <p>
          Uma janela de navegador da ALT, separada do seu navegador pessoal.
          JavaScript das páginas funciona. Sem acesso às suas sessões pessoais;
          digitação e cliques podem enviar dados ao site.
        </p>
      </div>
      <label>
        Endereço HTTPS
        <input
          value={url}
          maxLength={2000}
          onChange={(e) => setUrl(e.target.value)}
        />
      </label>
      <div className="button-row">
        <button
          disabled={busy}
          className="primary"
          onClick={() => propose("browser_open", { url })}
        >
          Preparar abertura
        </button>
        <button
          disabled={busy}
          className="secondary"
          onClick={() => propose("browser_read")}
        >
          Ler página atual
        </button>
        <button
          disabled={busy}
          className="secondary"
          onClick={() => propose("browser_back")}
        >
          Voltar
        </button>
      </div>
      <p className="setting-note">
        Ative um modo em Ferramentas. O proxy do navegador conecta somente a IPs
        públicos validados. Downloads, câmera/microfone e campos de senha ficam
        indisponíveis nesta versão.
      </p>
      {action && (
        <ChatActionCard
          action={action}
          onError={onError}
          onAnalyze={() => onAnalyze(action.id)}
          onUpdate={(next) => {
            setAction(next);
            const r = next.result as BrowserSnapshot | undefined;
            if (r?.snapshot_id) {
              setSnapshot(r);
              setTarget("");
              setUrl(r.url);
            }
          }}
        />
      )}
      {snapshot && (
        <>
          <h3>{snapshot.title}</h3>
          <p>{snapshot.url}</p>
          <details>
            <summary>Texto observado</summary>
            <pre className="prompt-preview">{snapshot.text}</pre>
          </details>
          <label>
            Elemento observado
            <select value={target} onChange={(e) => setTarget(e.target.value)}>
              <option value="">Escolha um elemento</option>
              {snapshot.elements.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.id} · {e.tag} · {e.label || e.href || e.type}
                </option>
              ))}
            </select>
          </label>
          <button
            className="secondary"
            disabled={!target || busy}
            onClick={() =>
              propose("browser_click", {
                target,
                snapshot_id: snapshot.snapshot_id,
              })
            }
          >
            Preparar clique neste elemento
          </button>
          <label>
            Texto para o campo escolhido
            <input
              value={text}
              maxLength={2000}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
          <button
            className="secondary"
            disabled={!target || busy}
            onClick={() =>
              propose("browser_type", {
                target,
                snapshot_id: snapshot.snapshot_id,
                content: text,
              })
            }
          >
            Revisar digitação
          </button>
        </>
      )}
    </div>
  );
}
