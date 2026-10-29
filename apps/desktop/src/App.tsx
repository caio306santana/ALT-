import { useEffect, useRef, useState, type CSSProperties } from "react";
import {
  MessageSquare,
  Boxes,
  Settings,
  Database,
  Activity,
  Shield,
  Plus,
  ArrowUp,
  Mic,
  Paperclip,
  Minus,
  Square,
  X,
  Pin,
  ChevronDown,
  RefreshCw,
  ArrowLeft,
  Check,
  Download,
  Pause,
  Play,
  Timer,
  Trash2,
  Search,
  Power,
  Code2,
  Monitor,
  SlidersHorizontal,
  Keyboard,
  Info,
  AlertCircle,
  StopCircle,
  Lock,
  ExternalLink,
  Brain,
  Wrench,
  Gamepad2,
  Globe,
  ListChecks,
  PanelLeft,
  History as HistoryIcon,
  UserRound,
  Cloud,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import {version as appVersion} from '../../../package.json';
import remarkGfm from "remark-gfm";
import type {
  Conversation,
  Message,
  Model,
  Preferences,
  StreamEvent,
  ProviderStatus,
  CloudPreview,
} from "../../../packages/shared-types";
import { themes } from "../../../packages/design-tokens/themes";
import { ProfilePanel } from "./components/ProfilePanel";
import {
  BackupPanel,
  TasksPanel,
  UpdateNotice,
  VerificationNote,
} from "./components/AgentPanels";
import { ApprovalMenu } from "./components/ApprovalMenu";
import { ChatActionCard, type ChatAction } from "./components/ChatActionCard";
import {
  OwnerControlPanel,
  EvaluationPanel,
  BrowserPanel,
} from "./components/WorkspacePanels";
import {
  AdvancedAppearance,
  PersonalityPanel,
  MemoryPanel,
  ToolsPanel,
  ProvidersPanel,
  defaultPersonality,
} from "./components/FeaturePanels";

const defaults: Preferences = {
  accent: "#ff0057",
  theme: "Night City Pink",
  opacity: 94,
  font_size: 14,
  glow: 35,
  compact: false,
  animations: true,
  model: "",
  performance: "auto",
  personality: defaultPersonality,
  secondary: "#00c9f5",
  appearance: "dark",
  scale: 1,
  chat_opacity: 100,
  effects: true,
  radius: 13,
  shortcut: "Control+Shift+Space",
  always_on_top: false,
  user_name: "",
};
const api = <T,>(method: string, path: string, body?: unknown) =>
  window.alt.request<T>(method, path, body);
const bytes = (value: number | undefined | null) =>
  value == null ? "Indisponível" : `${(value / 1024 ** 3).toFixed(1)} GB`;
type View =
  | "chat"
  | "models"
  | "history"
  | "monitor"
  | "security"
  | "memory"
  | "tools"
  | "profile"
  | "browser"
  | "tasks";
// One place for every screen's name, icon, title and one-line description.
const VIEWS: Record<
  View,
  { label: string; icon: typeof MessageSquare; title: string; hint?: string }
> = {
  chat: { label: "Chat", icon: MessageSquare, title: "Conversa" },
  tasks: {
    label: "Tarefas",
    icon: ListChecks,
    title: "Tarefas",
    hint: "Peça um objetivo; a ALT planeja, você revisa e ela executa passo a passo.",
  },
  memory: {
    label: "Memória",
    icon: Brain,
    title: "Memória",
    hint: "Memórias, projetos e documentos que a ALT pode usar.",
  },
  tools: {
    label: "Ferramentas",
    icon: Wrench,
    title: "Ferramentas",
    hint: "Modo de execução, pastas autorizadas e ações manuais.",
  },
  browser: {
    label: "Navegador",
    icon: Globe,
    title: "Navegador ALT",
    hint: "Janela isolada para a ALT ler e interagir com sites.",
  },
  models: {
    label: "Inteligências",
    icon: Boxes,
    title: "Inteligências",
    hint: "Modelos locais, provedores de nuvem e laboratório de comparação.",
  },
  history: {
    label: "Histórico",
    icon: HistoryIcon,
    title: "Histórico",
    hint: "Todas as suas conversas salvas neste computador.",
  },
  monitor: {
    label: "Sistema",
    icon: Activity,
    title: "Sistema",
    hint: "Uso de CPU, memória, disco e modelos carregados.",
  },
  security: {
    label: "Controle e regras",
    icon: Shield,
    title: "Controle e regras",
    hint: "O que a ALT pode fazer sozinha, o que pede aprovação e o que fica bloqueado.",
  },
  profile: { label: "Perfil", icon: UserRound, title: "Seu perfil" },
};
const NAV: View[] = [
  "chat",
  "tasks",
  "memory",
  "tools",
  "browser",
  "models",
  "history",
  "monitor",
  "security",
];
type SystemData = {
  cpu: { name: string; percent: number; logical_cores: number };
  ram: { used: number; total: number; available: number; percent: number };
  disk: { free: number; total: number };
  gpu: { Name: string; DriverVersion: string }[] | null;
  running_models:
    | {
        name: string;
        size: number;
        size_vram: number;
        context_length?: number;
      }[]
    | null;
  note: string;
  performance: {
    effective: string;
    options: { num_ctx: number; num_predict: number };
  };
};

type ContextEstimate = {
  fits: boolean;
  input_tokens: number;
  input_limit: number;
  history_included: number;
  history_total: number;
  tokenizer: string;
  reason?: string;
};

export default function App() {
  const [view, setView] = useState<View>("chat"),
    [sidebarOpen, setSidebarOpen] = useState(
      () => localStorage.getItem("alt-sidebar") !== "collapsed",
    ),
    [settingsOpen, setSettingsOpen] = useState(false),
    [tab, setTab] = useState("Aparência");
  const [prefs, setPrefs] = useState(defaults),
    [loaded, setLoaded] = useState(false),
    [models, setModels] = useState<Model[]>([]),
    [connected, setConnected] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]),
    [cid, setCid] = useState(""),
    [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [stopped, setStopped] = useState(false),
    [pinned, setPinned] = useState(false);
  const [system, setSystem] = useState<SystemData | null>(null),
    [search, setSearch] = useState(""),
    [installing, setInstalling] = useState(false),
    [pulling, setPulling] = useState(false),
    [progress, setProgress] = useState("");
  const [remaining, setRemaining] = useState(0),
    [timerRunning, setTimerRunning] = useState(false),
    [confirmModel, setConfirmModel] = useState(""),
    [deleteId, setDeleteId] = useState("");
  const end = useRef<HTMLDivElement>(null),
    current = useRef(""),
    textarea = useRef<HTMLTextAreaElement>(null);
  const timerDeadline = useRef(0);
  const followEnd = useRef(true);
  const [contextEstimate, setContextEstimate] = useState<ContextEstimate | null>(null);
  const [contextProblem, setContextProblem] = useState("");
  const [chatActions, setChatActions] = useState<ChatAction[]>([]),
    [pendingAnalysis, setPendingAnalysis] = useState<{
      id: string;
      content: string;
    } | null>(null);
  const [memoryIds, setMemoryIds] = useState<string[]>([]),
    [cloudPreview, setCloudPreview] = useState<CloudPreview | null>(null),
    [gameMode, setGameMode] = useState(false);
  const [updateVerified, setUpdateVerified] = useState<{
    version: string;
    file: string;
  } | null>(null);
  current.current = cid;
  const report = (e: unknown) =>
    setError(
      (e instanceof Error ? e.message : String(e)).replace(
        /^Error invoking remote method '[^']+': (?:Error: )?/,
        "",
      ),
    );
  async function refresh() {
    const data = await api<{
      connected: boolean;
      models: Model[];
      error: string | null;
    }>("GET", "/models");
    let cloud: Model[] = [];
    try {
      const providers = await api<{ providers: ProviderStatus[] }>(
        "GET",
        "/providers",
      );
      cloud = providers.providers
        .filter((p) => p.available)
        .map((p) => ({
          name: "cloud:" + p.id,
          size: 0,
          provider: p.name,
          location: "cloud",
        }));
    } catch {}
    setModels([...data.models, ...cloud]);
    setConnected(data.connected);
    setPrefs((p) =>
      !p.model && data.models.length
        ? {
            ...p,
            model:
              data.models.find((m) => m.name === "qwen3.5:4b")?.name ||
              data.models[0].name,
          }
        : p,
    );
    return data;
  }
  async function refreshConversations() {
    const list = await api<Conversation[]>("GET", "/conversations");
    setConversations(list);
    return list;
  }
  async function openConversation(id: string) {
    if (busy) return;
    const data = await api<Message[]>("GET", `/conversations/${id}/messages`);
    setCid(id);
    setMemoryIds([]);
    setChatActions([]);
    setMessages(data);
    setChatActions(
      await api<ChatAction[]>("GET", `/conversations/${id}/actions`),
    );
    setView("chat");
    setError("");
  }
  async function newConversation() {
    if (busy) return;
    const data = await api<Conversation>("POST", "/conversations");
    setCid(data.id);
    setMemoryIds([]);
    setChatActions([]);
    setMessages([]);
    setView("chat");
    setError("");
    await refreshConversations();
    textarea.current?.focus();
  }
  useEffect(() => {
    let alive = true;
    (async () => {
      if (!window.alt) {
        setError("Abra o aplicativo Electron para conectar ao backend local.");
        return;
      }
      try {
        const [saved, health, list] = await Promise.all([
          api<Preferences>("GET", "/settings"),
          api<{ stopped: boolean; game_mode: boolean }>("GET", "/health"),
          api<Conversation[]>("GET", "/conversations"),
        ]);
        if (!alive) return;
        setPrefs(saved);
        setStopped(health.stopped);
        setGameMode(health.game_mode);
        setPinned(saved.always_on_top);
        setConversations(list);
        await refresh();
        if (list.length) {
          setCid(list[0].id);
          setChatActions(
            await api<ChatAction[]>(
              "GET",
              `/conversations/${list[0].id}/actions`,
            ),
          );
          setMessages(
            await api<Message[]>(
              "GET",
              `/conversations/${list[0].id}/messages`,
            ),
          );
        }
        setLoaded(true);
      } catch (e) {
        if (alive) report(e);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);
  useEffect(() => {
    if (!loaded) return;
    const timeout = setTimeout(
      () => api("PUT", "/settings", prefs).catch(report),
      450,
    );
    return () => clearTimeout(timeout);
  }, [prefs, loaded]);
  useEffect(() => {
    if (!loaded) return;
    const id = setInterval(() => {
      if (document.visibilityState === "visible") refresh().catch(report);
    }, 10000);
    const onFocus = () => refresh().catch(report);
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [loaded]);
  useEffect(() => {
    if (followEnd.current) end.current?.scrollIntoView({ behavior: "instant" });
  }, [messages, prefs.animations]);
  useEffect(() => {
    if (!textarea.current) return;
    textarea.current.style.height = "auto";
    textarea.current.style.height = `${Math.min(180, textarea.current.scrollHeight)}px`;
  }, [input, view]);
  useEffect(() => {
    setContextEstimate(null);
    setContextProblem("");
    if (!loaded || !prefs.model || !input.trim() || busy) return;
    let active = true;
    const timeout = setTimeout(() => {
      api<ContextEstimate>("POST", "/chat/estimate", { conversation_id: cid, model: prefs.model, content: input.trim(), memory_ids: memoryIds })
        .then(value => { if (active) setContextEstimate(value); })
        .catch(() => { if (active) setContextProblem("Não foi possível conferir o contexto. O envio fará uma nova conferência."); });
    }, 350);
    return () => { active = false; clearTimeout(timeout); };
  }, [input, cid, memoryIds, prefs, loaded, busy]);
  useEffect(() => {
    if (!timerRunning || remaining <= 0) return;
    if (!timerDeadline.current)
      timerDeadline.current = Date.now() + remaining * 1000;
    const id = setInterval(() => {
      const next = Math.max(
        0,
        Math.ceil((timerDeadline.current - Date.now()) / 1000),
      );
      setRemaining(next);
      if (next === 0) {
        setTimerRunning(false);
        setNotice("Seu tempo de foco terminou. Faça uma pausa.");
      }
    }, 500);
    return () => clearInterval(id);
  }, [timerRunning]);
  useEffect(() => {
    if (view !== "monitor" || !window.alt) return;
    const load = () =>
      api<SystemData>("GET", "/system").then(setSystem).catch(report);
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [view]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSettingsOpen(false);
        setConfirmModel("");
        setDeleteId("");
        setCloudPreview(null);
      }
      if (e.ctrlKey && e.key === "n") {
        e.preventDefault();
        newConversation().catch(report);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [busy]);
  const selected = models.find((m) => m.name === prefs.model);
  const modelName =
    selected?.provider || selected?.name || "Selecionar inteligência";
  function update<K extends keyof Preferences>(key: K, value: Preferences[K]) {
    setPrefs((old) => ({ ...old, [key]: value }));
  }
  async function send(
    consentReceipt = "",
    analysis?: { id: string; content: string },
  ) {
    const text = analysis?.content || input.trim();
    if (!text || busy) return;
    if (stopped) {
      setError("Retome as ações antes de enviar uma mensagem.");
      return;
    }
    if (!selected) {
      setNotice(
        "Escolha um modelo local no painel Inteligências para conversar.",
      );
      setView("models");
      return;
    }
    setError("");
    setNotice("");
    setBusy(true);
    let id = cid;
    let accepted = false;
    let attempted = false;
    try {
      if (!id) {
        const c = await api<Conversation>("POST", "/conversations");
        id = c.id;
        setCid(id);
      }
      const estimate = await api<ContextEstimate>("POST", "/chat/estimate", {
        conversation_id: id, model: prefs.model, content: text,
        memory_ids: memoryIds, tool_result_id: analysis?.id || "",
      });
      setContextEstimate(estimate);
      if (!estimate.fits) throw new Error(estimate.reason || "Este envio excede o contexto disponível.");
      if (prefs.model.startsWith("cloud:") && !consentReceipt) {
        setPendingAnalysis(analysis || null);
        if (analysis) setInput(text);
        setCloudPreview(
          await api<CloudPreview>("POST", "/chat/preview", {
            conversation_id: id,
            model: prefs.model,
            content: text,
            memory_ids: memoryIds,
            tool_result_id: analysis?.id || "",
          }),
        );
        return;
      }
      setCloudPreview(null);
      const user: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        model: null,
        status: "complete",
        created: new Date().toISOString(),
        metrics: null,
      };
      const assistant: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        model: prefs.model,
        status: "streaming",
        created: new Date().toISOString(),
        metrics: null,
      };
      setMessages((old) => [...old, user, assistant]);
      followEnd.current = true;
      attempted = true;
      setInput(old => old.trim() === text ? "" : old);
      await window.alt.stream(
        crypto.randomUUID(),
        "chat",
        {
          conversation_id: id,
          model: prefs.model,
          content: text,
          memory_ids: memoryIds,
          consent_receipt: consentReceipt,
          tool_result_id: analysis?.id || "",
        },
        (event: StreamEvent) => {
          if (event.type === "start") accepted = true;
          if (event.type === "tool_proposal" && event.proposal)
            setChatActions((old) => [
              ...old,
              { ...event.proposal!, state: "proposed" },
            ]);
          if (event.type === "tool_result")
            setChatActions((old) =>
              old.map((action) =>
                action.id === event.action_id
                  ? { ...action, state: "complete", result: event.result }
                  : action,
              ),
            );
          if (event.type === "delta")
            setMessages((old) =>
              old.map((m) =>
                m.id === assistant.id
                  ? { ...m, content: m.content + (event.text || "") }
                  : m,
              ),
            );
          if (event.type === "error")
            setError(event.message || "Erro ao gerar resposta");
          if (event.type === "start")
            setNotice(
              [
                event.context_truncated
                  ? "A conversa completa está salva. Apenas o trecho recente que cabe no contexto foi enviado ao modelo."
                  : "",
                event.tool_result_truncated
                  ? "A ALT recebeu um trecho do resultado ajustado ao contexto. O conteúdo completo continua no cartão da ferramenta."
                  : "",
                event.recalled_memories?.length
                  ? `Memórias recuperadas: ${event.recalled_memories.map((m) => m.title).join(", ")}.`
                  : "",
              ]
                .filter(Boolean)
                .join(" "),
            );
          if (event.type === "done")
            setMessages((old) =>
              old.map((m) =>
                m.id === assistant.id
                  ? {
                      ...m,
                      status: event.status as Message["status"],
                      metrics: event.metrics || null,
                    }
                  : m,
              ),
            );
        },
      );
    } catch (e) {
      if (attempted && !accepted) setInput(old => old || text);
      report(e);
    } finally {
      setBusy(false);
      if (id) {
        try {
          setMessages(
            await api<Message[]>("GET", `/conversations/${id}/messages`),
          );
          await refreshConversations();
        } catch (e) {
          report(e);
        }
      }
    }
  }
  async function stopAll() {
    await api("POST", "/actions/stop");
    setStopped(true);
    setNotice("Ações suspensas. Respostas parciais serão preservadas.");
  }
  async function resume() {
    await api("POST", "/actions/resume");
    setStopped(false);
    setGameMode(false);
    setNotice("Modo de observação retomado.");
  }
  async function pull() {
    const model = confirmModel;
    setConfirmModel("");
    setPulling(true);
    setError("");
    try {
      await window.alt.stream(
        crypto.randomUUID(),
        "pull",
        { model },
        (event) => {
          if (event.type === "progress")
            setProgress(
              `${event.status || "Baixando"}${event.total ? " · " + Math.round(((event.completed || 0) / event.total) * 100) + "%" : ""}`,
            );
          if (event.type === "error")
            setError(event.message || "Download interrompido");
        },
      );
      await refresh();
    } catch (e) {
      report(e);
    } finally {
      setPulling(false);
      setProgress("");
    }
  }
  async function install() {
    setInstalling(true);
    try {
      const result = await window.alt.installOllama();
      setNotice(result.message);
      await refresh();
    } catch (e) {
      report(e);
    } finally {
      setInstalling(false);
    }
  }
  const style = {
    "--accent": prefs.accent,
    "--surface-alpha": prefs.opacity / 100,
    "--glow": `${prefs.glow / 2}px`,
    "--secondary": prefs.secondary,
    "--chat-alpha": prefs.chat_opacity / 100,
    "--radius": `${prefs.radius}px`,
    fontSize: `${prefs.font_size}px`,
  } as CSSProperties;
  const title =
    conversations.find((c) => c.id === cid)?.title ||
    "Seu espaço para pensar além.";
  const toggleSidebar = () => {
    localStorage.setItem("alt-sidebar", sidebarOpen ? "collapsed" : "open");
    setSidebarOpen(!sidebarOpen);
  };
  const screen = VIEWS[view];
  return (
    <div
      className={`app ${prefs.compact ? "compact" : ""} ${!prefs.animations || gameMode ? "no-animation" : ""} ${prefs.appearance === "light" ? "light" : ""} ${!prefs.effects || gameMode ? "no-effects" : ""}`}
      style={style}
    >
      <header className="titlebar">
        <div className="brand">
          <span className="brand-slash" />
          ALT-AI<span className="edition">PERSONAL INTELLIGENCE</span>
        </div>
        <div className="window-tools">
          <span className={`connection ${connected ? "online" : ""}`}>
            <i />
            {connected ? "Ollama conectado" : "Ollama offline"}
          </span>
          <button
            className={pinned ? "active" : ""}
            title="Sempre no topo"
            aria-label="Sempre no topo"
            onClick={() =>
              window.alt.window("pin").then((v) => {
                setPinned(!!v);
                update("always_on_top", !!v);
              })
            }
          >
            <Pin size={15} />
          </button>
          <span className="divider" />
          <button
            aria-label="Minimizar"
            onClick={() => window.alt.window("minimize")}
          >
            <Minus size={16} />
          </button>
          <button
            aria-label="Maximizar"
            onClick={() => window.alt.window("maximize")}
          >
            <Square size={13} />
          </button>
          <button
            aria-label="Ocultar na bandeja"
            onClick={() => window.alt.window("hide")}
          >
            <X size={17} />
          </button>
        </div>
      </header>
      <div className="workspace">
        <aside className={`sidebar ${sidebarOpen ? "open" : "collapsed"}`}>
          <button
            className="side-item side-toggle"
            title={sidebarOpen ? "Recolher barra lateral" : "Expandir barra lateral"}
            aria-label={sidebarOpen ? "Recolher barra lateral" : "Expandir barra lateral"}
            onClick={toggleSidebar}
          >
            <PanelLeft size={18} />
          </button>
          <button
            className="side-item new-chat"
            title="Nova conversa · Ctrl+N"
            aria-label="Nova conversa"
            onClick={() => newConversation().catch(report)}
            disabled={busy}
          >
            <Plus size={18} />
            <span>Nova conversa</span>
          </button>
          <nav className="side-nav">
            {NAV.map((id) => {
              const item = VIEWS[id];
              return (
                <button
                  key={id}
                  title={item.label}
                  aria-label={item.label}
                  className={`side-item ${view === id ? "selected" : ""}`}
                  onClick={() => setView(id)}
                >
                  <item.icon size={18} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
          {sidebarOpen && conversations.length > 0 && (
            <div className="side-recent">
              <span className="side-heading">Recentes</span>
              {conversations.slice(0, 12).map((c) => (
                <button
                  key={c.id}
                  title={c.title}
                  className={`side-item recent ${c.id === cid && view === "chat" ? "selected" : ""}`}
                  disabled={busy}
                  onClick={() => openConversation(c.id).catch(report)}
                >
                  <span>{c.title}</span>
                </button>
              ))}
            </div>
          )}
          <div className="side-bottom">
            <button
              title="Configurações"
              aria-label="Configurações"
              className={`side-item ${settingsOpen ? "selected" : ""}`}
              onClick={() => setSettingsOpen(!settingsOpen)}
            >
              <Settings size={18} />
              <span>Configurações</span>
            </button>
            <button
              className={`side-item side-profile ${view === "profile" ? "selected" : ""}`}
              title="Seu perfil"
              aria-label="Seu perfil"
              onClick={() => setView("profile")}
            >
              <i className="avatar">
                {prefs.user_name?.slice(0, 1).toUpperCase() || "A"}
              </i>
              <span>{prefs.user_name || "Seu perfil"}</span>
            </button>
          </div>
        </aside>
        <main className="main">
          <div className="sectionbar">
            <div>
              <h1>
                {screen.title}
                {view === "chat" && (
                  <span className="small-tag">
                    {prefs.model.startsWith("cloud:") ? "NUVEM" : "LOCAL"}
                  </span>
                )}
              </h1>
              {screen.hint && <p className="section-hint">{screen.hint}</p>}
            </div>
            {view === "chat" ? (
              <button className="model-pill" onClick={() => setView("models")}>
                <Boxes size={15} />
                <span>{modelName}</span>
                <ChevronDown size={13} />
              </button>
            ) : (
              <button
                className="icon-btn"
                title="Voltar ao chat"
                onClick={() => setView("chat")}
              >
                <ArrowLeft size={20} />
              </button>
            )}
          </div>
          {error && (
            <div role="alert" className="banner error">
              <AlertCircle size={16} />
              <span>{error}</span>
              <button aria-label="Fechar erro" onClick={() => setError("")}>
                <X size={14} />
              </button>
            </div>
          )}
          {notice && (
            <div role="status" className="banner">
              <Info size={16} />
              <span>{notice}</span>
              <button aria-label="Fechar aviso" onClick={() => setNotice("")}>
                <X size={14} />
              </button>
            </div>
          )}
          <UpdateNotice onError={report} />
          {pulling && (
            <div className="banner">
              <Download size={16} />
              <span>{progress || "Iniciando download…"}</span>
              <button onClick={() => stopAll().catch(report)}>
                Interromper
              </button>
            </div>
          )}
          {view === "chat" && (
            <>
              <div className="chat-scroll" onScroll={e => { const el = e.currentTarget; followEnd.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100; }}>
                {messages.length === 0 ? (
                  <div className="welcome">
                    <div className="welcome-mark">
                      <span />
                    </div>
                    <span className="eyebrow">
                      SUA INTELIGÊNCIA. SEU ESPAÇO.
                    </span>
                    <h2>
                      Olá. Sou a{" "}
                      <strong>{prefs.personality?.name || "ALT-AI"}.</strong>
                    </h2>
                    <p>
                      Um espaço para suas ideias, projetos e próximos passos.
                      <br />
                      Por onde vamos começar?
                    </p>
                    <div className="suggestions">
                      {[
                        {
                          icon: Code2,
                          title: "Vamos criar algo",
                          text: "Me ajude a planejar um projeto de programação.",
                        },
                        {
                          icon: Timer,
                          title: "Organizar meu dia",
                          text: "Me ajude a organizar meu dia. Pergunte quais são minhas prioridades.",
                        },
                        {
                          icon: MessageSquare,
                          title: "Explorar uma ideia",
                          text: "Quero explorar uma ideia. Me ajude a desenvolver meu raciocínio.",
                        },
                      ].map((s) => (
                        <button
                          key={s.title}
                          onClick={() => {
                            setInput(s.text);
                            textarea.current?.focus();
                          }}
                        >
                          <s.icon size={19} />
                          <span>{s.title}</span>
                          <ArrowUp size={14} />
                        </button>
                      ))}
                    </div>
                    <div className="local-note">
                      <Lock size={12} />
                      {prefs.model.startsWith("cloud:")
                        ? "Nuvem somente após revisão do contexto"
                        : "Histórico local · memórias sob seu controle"}
                    </div>
                    {(!connected || models.length === 0) && (
                      <div className="setup-callout">
                        <span className="status-orb" />
                        <div>
                          <strong>
                            {connected
                              ? "Falta apenas uma inteligência."
                              : "Vamos conectar sua inteligência local."}
                          </strong>
                          <p>
                            {connected
                              ? "Baixe um modelo para começar a conversar."
                              : "O Ollama executa seus modelos neste computador."}
                          </p>
                        </div>
                        <button onClick={() => setView("models")}>
                          Configurar <ArrowUp size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="messages">
                    <div className="conversation-date">{title}</div>
                    {messages.map((m) => (
                      <article key={m.id} className={`message ${m.role}`}>
                        <div className="message-label">
                          {m.role === "assistant" ? (
                            <>
                              <span className="mini-slash" />
                              ALT-AI <small>{m.model}</small>
                            </>
                          ) : (
                            <>VOCÊ</>
                          )}
                          <time>
                            {new Date(m.created).toLocaleTimeString("pt-BR", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </time>
                        </div>
                        <div className="message-content">
                          {m.content ? (
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                a: ({ children }) => (
                                  <span className="text-link">{children}</span>
                                ),
                              }}
                            >
                              {m.content}
                            </ReactMarkdown>
                          ) : m.status === "streaming" ? (
                            <span className="thinking">
                              Processando<span>…</span>
                            </span>
                          ) : (
                            <span className="muted">
                              Nenhuma resposta concluída.
                            </span>
                          )}
                        </div>
                        {m.role === "assistant" && m.status !== "streaming" && (
                          <div className="message-meta">
                            {m.status !== "complete" && (
                              <span>
                                Resposta{" "}
                                {m.status === "error"
                                  ? "com erro"
                                  : "interrompida"}{" "}
                                · fora do contexto seguinte
                              </span>
                            )}
                            {m.metrics && (
                              <span>
                                {m.metrics.tokens ?? "—"} tokens ·{" "}
                                {m.metrics.tokens_per_second ?? "—"} tok/s ·{" "}
                                {m.metrics.total_seconds ?? "—"} s
                              </span>
                            )}
                            <button
                              title="Copiar resposta"
                              onClick={() =>
                                navigator.clipboard
                                  .writeText(m.content)
                                  .then(() => setNotice("Resposta copiada."))
                                  .catch(report)
                              }
                            >
                              Copiar
                            </button>
                          </div>
                        )}
                        {m.role === "assistant" && m.status === "complete" && (
                          <VerificationNote verification={m.metrics?.verification} />
                        )}
                      </article>
                    ))}
                    {chatActions.map((action) => (
                      <ChatActionCard
                        key={action.id}
                        action={action}
                        onUpdate={(updated, previousId) =>
                          setChatActions((old) =>
                            old.map((a) => (a.id === (previousId || updated.id) ? updated : a)),
                          )
                        }
                        onAnalyze={() =>
                          send("", {
                            id: action.id,
                            content:
                              "Analise este resultado confirmado da ferramenta. Se for uma pesquisa, explique e cite as URLs recuperadas.",
                          })
                        }
                        onError={report}
                      />
                    ))}
                    <div ref={end} />
                  </div>
                )}
              </div>
              <div className="composer-area">
                {remaining > 0 && (
                  <div className="focus-card">
                    <div className="timer-ring">
                      {Math.floor(remaining / 60)
                        .toString()
                        .padStart(2, "0")}
                      :{(remaining % 60).toString().padStart(2, "0")}
                    </div>
                    <div>
                      <strong>Modo Foco</strong>
                      <p>Uma coisa de cada vez.</p>
                    </div>
                    <button
                      className="icon-btn"
                      aria-label={
                        timerRunning
                          ? "Pausar temporizador"
                          : "Retomar temporizador"
                      }
                      onClick={() => {
                        timerDeadline.current = timerRunning
                          ? 0
                          : Date.now() + remaining * 1000;
                        setTimerRunning(!timerRunning);
                      }}
                    >
                      {timerRunning ? <Pause size={17} /> : <Play size={17} />}
                    </button>
                    <button
                      className="icon-btn danger"
                      aria-label="Parar temporizador"
                      onClick={() => {
                        setRemaining(0);
                        setTimerRunning(false);
                      }}
                    >
                      <Square size={14} />
                    </button>
                  </div>
                )}
                {stopped && (
                  <div className="stopped">
                    <StopCircle size={17} />
                    <span>Ações suspensas</span>
                    <button onClick={() => resume().catch(report)}>
                      Retomar
                    </button>
                  </div>
                )}
                <div className="memory-composer">
                  <button
                    className="text-button"
                    type="button"
                    onClick={() => setView("memory")}
                  >
                    <Brain size={13} />
                    {memoryIds.length
                      ? `${memoryIds.length} memória(s) selecionada(s)`
                      : "Selecionar memórias para esta conversa"}
                  </button>
                </div>
                <form
                  className="composer"
                  onSubmit={(e) => {
                    e.preventDefault();
                    send();
                  }}
                >
                  <textarea
                    ref={textarea}
                    aria-label="Mensagem para a ALT-AI"
                    placeholder={
                      stopped
                        ? "Retome as ações para conversar…"
                        : "Mensagem para a ALT-AI…"
                    }
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.shiftKey &&
                        !e.nativeEvent.isComposing
                      ) {
                        e.preventDefault();
                        send();
                      }
                    }}
                    rows={2}
                    maxLength={16000}
                  />
                  <div className="composer-controls">
                    <div>
                      <button
                        type="button"
                        disabled
                        title="Anexos · fase futura"
                        aria-label="Anexos indisponíveis"
                      >
                        <Paperclip size={18} />
                      </button>
                      <button
                        type="button"
                        disabled
                        title="Voz local · fase futura"
                        aria-label="Voz indisponível"
                      >
                        <Mic size={18} />
                      </button>
                      <button
                        type="button"
                        title="Iniciar 25 minutos de foco"
                        aria-label="Iniciar temporizador de foco"
                        onClick={() => {
                          timerDeadline.current = Date.now() + 1500 * 1000;
                          setRemaining(1500);
                          setTimerRunning(true);
                        }}
                      >
                        <Timer size={18} />
                      </button>
                      <ApprovalMenu disabled={stopped || busy} onError={report} />
                    </div>
                    {busy ? (
                      <button
                        className="send"
                        type="button"
                        aria-label="Interromper resposta"
                        onClick={() =>
                          api("POST", `/chat/cancel/${cid}`).catch(report)
                        }
                      >
                        <Square size={16} />
                      </button>
                    ) : (
                      <button
                        className="send"
                        aria-label="Enviar mensagem"
                        disabled={
                          !input.trim() || !selected || stopped || !loaded || contextEstimate?.fits === false
                        }
                      >
                        <ArrowUp size={20} />
                      </button>
                    )}
                  </div>
                </form>
                {(contextEstimate || contextProblem) && <div className={`context-indicator ${contextEstimate?.fits === false ? "over-limit" : ""}`} role="status">
                  {contextEstimate ? <span title={`Contagem ${contextEstimate.tokenizer}; inclui personalidade, memórias e histórico enviado.`}>
                    Contexto: {contextEstimate.input_tokens.toLocaleString("pt-BR")} / {contextEstimate.input_limit.toLocaleString("pt-BR")} tokens
                    {contextEstimate.fits && contextEstimate.history_included < contextEstimate.history_total ? " · histórico recente; conversa completa salva" : ""}
                    {!contextEstimate.fits ? ` · ${contextEstimate.reason}` : ""}
                  </span> : contextProblem}
                </div>}
                <div className="composer-caption">
                  <span>
                    <i />
                    {selected
                      ? prefs.model.startsWith("cloud:")
                        ? "Nuvem · revisão antes do envio"
                        : "Processamento local pelo Ollama"
                      : "Selecione um modelo para começar"}
                  </span>
                  <span>
                    Enter para enviar <span className="key">↵</span>
                  </span>
                </div>
              </div>
            </>
          )}
          {view === "models" && (
            <div className="page-scroll">
              <p className="page-intro">
                A inteligência muda. Seu contexto continua aqui.
                <br />
                <span>
                  Somente modelos locais detectados são disponibilizados para
                  conversa.
                </span>
              </p>
              <div className="subheading">
                <span>
                  <i className={`dot ${connected ? "green" : ""}`} />
                  {connected ? "Ollama conectado" : "Ollama não conectado"}
                </span>
                <button
                  className="text-button"
                  onClick={() =>
                    refresh()
                      .then(() => setNotice("Lista atualizada."))
                      .catch(report)
                  }
                >
                  <RefreshCw size={13} /> Atualizar
                </button>
              </div>
              {!connected && (
                <div className="info-card">
                  <Monitor size={27} />
                  <h3>O poder está no seu computador.</h3>
                  <p>
                    Instale ou abra o Ollama para executar modelos locais.
                    Nenhum crédito de API é necessário.
                  </p>
                  <div className="button-row">
                    <button
                      className="primary"
                      disabled={installing}
                      onClick={install}
                    >
                      {installing ? "Instalando…" : "Instalar Ollama"}
                    </button>
                    <button
                      className="secondary"
                      onClick={() => window.alt.ollamaWebsite()}
                    >
                      Site oficial <ExternalLink size={13} />
                    </button>
                  </div>
                </div>
              )}
              {models.map((model) => (
                <button
                  key={model.name}
                  className={`model-card ${prefs.model === model.name ? "chosen" : ""}`}
                  disabled={busy}
                  onClick={() => {
                    update("model", model.name);
                    setNotice(
                      `Modelo ${model.name} selecionado. O histórico desta conversa será preservado.`,
                    );
                  }}
                >
                  <div className="model-symbol">
                    <Boxes size={23} />
                  </div>
                  <div>
                    <h3>{model.provider || model.name}</h3>
                    <p>
                      {model.location === "cloud"
                        ? "Nuvem · revisão do contexto obrigatória"
                        : `Ollama · Local · ${bytes(model.size)} em disco`}
                    </p>
                    <span>
                      {model.location === "cloud"
                        ? "Conversa e código · ferramentas Windows no Qwen/Ollama"
                        : `${model.details?.parameter_size || "Parâmetros não informados"} · ${model.details?.quantization_level || "Quantização não informada"}`}
                    </span>
                  </div>
                  <span className="check-circle">
                    {prefs.model === model.name ? <Check size={14} /> : null}
                  </span>
                </button>
              ))}
              <div className="download-section">
                <span className="eyebrow">MODELOS QWEN LOCAIS</span>
                {[
                  "qwen3.5:2b",
                  "qwen3.5:4b",
                  "qwen3.5:9b",
                  "huihui_ai/qwen3.5-abliterated:4b",
                ]
                  .filter((name) => !models.some((m) => m.name === name))
                  .map((name) => (
                    <div className="download-row" key={name}>
                      <div>
                        <strong>
                          {name.startsWith("huihui")
                            ? "Huihui Qwen 3.5 · comunitário · 4B"
                            : `Qwen 3.5 ${name.split(":")[1].toUpperCase()}`}
                        </strong>
                        <p>
                          {name.endsWith("2b")
                            ? "Mais leve para notebooks · menor capacidade"
                            : name.endsWith("4b")
                              ? "Mais leve · download de vários GB"
                              : "Mais capacidade · maior uso de RAM/VRAM"}
                        </p>
                      </div>
                      <button
                        className="secondary"
                        disabled={!connected || pulling || stopped}
                        onClick={() => setConfirmModel(name)}
                      >
                        <Download size={14} /> Baixar
                      </button>
                    </div>
                  ))}
              </div>
              <EvaluationPanel
                models={models}
                notify={setNotice}
                onError={report}
              />
              <div className="unavailable">
                <Lock size={15} />
                <div>
                  <strong>Integrações oficiais de nuvem</strong>
                  <p>
                    Configure provedores em Configurações → Provedores. Somente
                    integrações disponíveis aparecem no seletor; cada envio
                    exige revisão do contexto.
                  </p>
                </div>
                <span className="small-tag">OPCIONAL</span>
              </div>
            </div>
          )}
          {view === "history" && (
            <div className="page-scroll">
              <div className="search-field">
                <Search size={16} />
                <input
                  placeholder="Buscar pelo título…"
                  aria-label="Buscar conversas"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              {conversations
                .filter((c) =>
                  c.title.toLowerCase().includes(search.toLowerCase()),
                )
                .map((c) => (
                  <div className="history-row" key={c.id}>
                    <button
                      disabled={busy}
                      onClick={() => openConversation(c.id).catch(report)}
                    >
                      <MessageSquare size={18} />
                      <div>
                        <strong>{c.title}</strong>
                        <p>{new Date(c.updated).toLocaleString("pt-BR")}</p>
                      </div>
                    </button>
                    <button
                      className="icon-btn"
                      disabled={busy}
                      aria-label={`Excluir ${c.title}`}
                      onClick={() => setDeleteId(c.id)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              {!conversations.length && (
                <div className="empty-state">
                  <Database size={30} />
                  <h3>Um novo começo.</h3>
                  <p>
                    Suas conversas aparecerão aqui, salvas neste computador.
                  </p>
                </div>
              )}
            </div>
          )}
          {view === "monitor" && (
            <div className="page-scroll">
              <p className="page-intro">
                Telemetria do computador em tempo real.
                <br />
                <span>
                  Atualizada a cada 5 segundos enquanto este painel está aberto.
                </span>
              </p>
              {system ? (
                <>
                  <div className="metric-grid">
                    {[
                      {
                        label: "CPU",
                        value: `${system.cpu.percent}%`,
                        sub: `${system.cpu.logical_cores} processadores lógicos`,
                        percent: system.cpu.percent,
                      },
                      {
                        label: "MEMÓRIA RAM",
                        value: bytes(system.ram.used),
                        sub: `${bytes(system.ram.available)} disponíveis / ${bytes(system.ram.total)}`,
                        percent: system.ram.percent,
                      },
                      {
                        label: "ARMAZENAMENTO",
                        value: bytes(system.disk.free),
                        sub: `livres / ${bytes(system.disk.total)}`,
                        percent:
                          (1 - system.disk.free / system.disk.total) * 100,
                      },
                    ].map((m) => (
                      <div className="metric" key={m.label}>
                        <span className="eyebrow">{m.label}</span>
                        <h2>{m.value}</h2>
                        <div className="meter">
                          <span style={{ width: `${m.percent}%` }} />
                        </div>
                        <p>{m.sub}</p>
                      </div>
                    ))}
                  </div>
                  <div className="info-line">
                    <Monitor size={17} />
                    {system.cpu.name}
                  </div>
                  <div className="info-line">
                    <Activity size={17} />
                    Perfil{" "}
                    {system.performance.effective === "notebook"
                      ? "econômico para notebook"
                      : "desktop"}{" "}
                    · contexto {system.performance.options.num_ctx} · saída até{" "}
                    {system.performance.options.num_predict} tokens
                  </div>
                  <div className="info-card">
                    <h3>GPU e inferência</h3>
                    {system.gpu?.map((gpu, index) => (
                      <p key={index}>
                        {gpu.Name} · Driver {gpu.DriverVersion}
                      </p>
                    ))}
                    <p>{system.note}</p>
                    {system.running_models === null ? (
                      <p>Ollama indisponível.</p>
                    ) : system.running_models.length === 0 ? (
                      <p>Nenhum modelo carregado.</p>
                    ) : (
                      system.running_models.map((m) => (
                        <div className="running-model" key={m.name}>
                          <strong>{m.name}</strong>
                          <p>
                            Alocado: {bytes(m.size)} · VRAM do modelo:{" "}
                            {bytes(m.size_vram)} · Contexto:{" "}
                            {m.context_length ?? "indisponível"}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="unavailable">
                    <Gamepad2 size={18} />
                    <div>
                      <strong>GAME MODE</strong>
                      <p>
                        Suspende tarefas, revoga permissões e tenta descarregar
                        o modelo local selecionado. A janela será ocultada.
                      </p>
                    </div>
                    <button
                      className="secondary"
                      onClick={() =>
                        window.alt
                          .gameMode(!gameMode)
                          .then((result) => {
                            setGameMode(result.enabled);
                            setStopped(result.enabled);
                            setNotice(result.message);
                          })
                          .catch(report)
                      }
                    >
                      {gameMode ? "Retomar" : "Ativar"}
                    </button>
                  </div>
                </>
              ) : (
                <div className="empty-state">Consultando métricas…</div>
              )}
              <BackupPanel notify={setNotice} onError={report} />
            </div>
          )}
          {view === "memory" && (
            <MemoryPanel
              selected={memoryIds}
              onSelect={setMemoryIds}
              notify={setNotice}
              onError={report}
              conversationId={cid}
              model={prefs.model}
            />
          )}
          {view === "tools" && (
            <ToolsPanel
              notify={setNotice}
              onError={report}
              onCommand={(text) => {
                setInput(text);
                setView("chat");
              }}
            />
          )}
          {view === "profile" && (
            <ProfilePanel
              prefs={prefs}
              onChange={setPrefs}
              model={modelName}
              onIdentity={() => {
                setTab("Personalidade");
                setSettingsOpen(true);
              }}
              onMemory={() => setView("memory")}
              onTools={() => setView("tools")}
            />
          )}
          {view === "security" && (
            <OwnerControlPanel notify={setNotice} onError={report} />
          )}
          {view === "tasks" && (
            <TasksPanel
              models={models}
              model={prefs.model}
              notify={setNotice}
              onError={report}
              onOpenConversation={(id) => openConversation(id).catch(report)}
            />
          )}
          {view === "browser" && (
            <BrowserPanel
              notify={setNotice}
              onError={report}
              onAnalyze={(id) => {
                setView("chat");
                send("", {
                  id,
                  content: "Analise a pagina observada e cite a fonte.",
                });
              }}
            />
          )}
          <footer className="statusbar">
            <span>
              <span className="tiny-slash" /> ALT-AI <b>{appVersion}</b>
            </span>
            <button
              className={stopped ? "halted" : ""}
              onClick={() =>
                stopped ? resume().catch(report) : stopAll().catch(report)
              }
            >
              <span className="dot" />
              {stopped ? "SUSPENSO · RETOMAR" : "STOP ALL ACTIONS"}
            </button>
            <span>
              <Lock size={10} /> LOCAL FIRST
            </span>
          </footer>
        </main>
        {settingsOpen && (
          <aside className="settings-panel">
            <div className="settings-title">
              <Settings size={18} />
              <h2>Configurações</h2>
              <button
                className="icon-btn"
                aria-label="Fechar configurações"
                onClick={() => setSettingsOpen(false)}
              >
                <X size={17} />
              </button>
            </div>
            <div className="settings-tabs">
              {[
                { name: "Aparência", icon: Monitor },
                { name: "Personalidade", icon: Brain },
                { name: "Comportamento", icon: SlidersHorizontal },
                { name: "Modelos de IA", icon: Boxes },
                { name: "Provedores", icon: Cloud },
                { name: "Atalhos", icon: Keyboard },
                { name: "Sobre", icon: Info },
              ].map((t) => (
                <button
                  key={t.name}
                  className={tab === t.name ? "selected" : ""}
                  onClick={() => setTab(t.name)}
                >
                  <t.icon size={18} />
                  {t.name}
                </button>
              ))}
            </div>
            <div className="settings-scroll">
              {tab === "Aparência" ? (
                <>
                  <div className="setting-group">
                    <div className="setting-heading">
                      Tema{" "}
                      <button
                        onClick={() =>
                          setPrefs((p) => ({
                            ...p,
                            accent: defaults.accent,
                            theme: defaults.theme,
                            opacity: defaults.opacity,
                            glow: defaults.glow,
                            font_size: defaults.font_size,
                            secondary: defaults.secondary,
                            appearance: "dark",
                            effects: true,
                            radius: 13,
                            chat_opacity: 100,
                          }))
                        }
                      >
                        Resetar
                      </button>
                    </div>
                    <select
                      aria-label="Tema"
                      value={prefs.theme}
                      onChange={(e) => {
                        const theme = themes.find(
                          (t) => t.name === e.target.value,
                        );
                        setPrefs((p) => ({
                          ...p,
                          theme: e.target.value,
                          accent: theme?.color || p.accent,
                        }));
                      }}
                    >
                      {themes.map((t) => (
                        <option key={t.name}>{t.name}</option>
                      ))}
                      <option>Custom</option>
                    </select>
                    <div className="swatches">
                      {themes.map((t) => (
                        <button
                          key={t.name}
                          title={t.name}
                          aria-label={t.name}
                          className={prefs.accent === t.color ? "current" : ""}
                          style={{ background: t.color }}
                          onClick={() =>
                            setPrefs((p) => ({
                              ...p,
                              accent: t.color,
                              theme: t.name,
                            }))
                          }
                        />
                      ))}
                    </div>
                    <div className="custom-color">
                      <input
                        type="color"
                        aria-label="Cor de destaque"
                        value={prefs.accent}
                        onChange={(e) =>
                          setPrefs((p) => ({
                            ...p,
                            accent: e.target.value,
                            theme: "Custom",
                          }))
                        }
                      />
                      <span>{prefs.accent.toUpperCase()}</span>
                      <span className="muted">HEX</span>
                    </div>
                  </div>
                  <div className="setting-group">
                    <Range
                      title="Opacidade do painel"
                      value={prefs.opacity}
                      min={65}
                      max={100}
                      suffix="%"
                      onChange={(v) => update("opacity", v)}
                    />
                    <Range
                      title="Intensidade do neon"
                      value={prefs.glow}
                      min={0}
                      max={100}
                      suffix="%"
                      onChange={(v) => update("glow", v)}
                    />
                  </div>
                  <div className="setting-group">
                    <div className="setting-heading">Layout</div>
                    <Toggle
                      title="Modo compacto"
                      text="Mais espaço para o essencial."
                      checked={prefs.compact}
                      onChange={(v) => update("compact", v)}
                    />
                    <Toggle
                      title="Animações"
                      text="Transições suaves na interface."
                      checked={prefs.animations}
                      onChange={(v) => update("animations", v)}
                    />
                    <Range
                      title="Tamanho da fonte"
                      value={prefs.font_size}
                      min={12}
                      max={20}
                      suffix="px"
                      onChange={(v) => update("font_size", v)}
                    />
                  </div>
                  <div className="theme-preview">
                    <span className="preview-icon">
                      <MessageSquare size={17} />
                    </span>
                    <div>
                      <strong>Sua interface, seu estilo.</strong>
                      <p>Preferências salvas neste PC.</p>
                    </div>
                    <Check size={14} />
                  </div>
                  <AdvancedAppearance
                    prefs={prefs}
                    onChange={setPrefs}
                    notify={setNotice}
                    onError={report}
                  />
                </>
              ) : tab === "Personalidade" ? (
                <PersonalityPanel
                  value={prefs.personality}
                  onChange={(value) => update("personality", value)}
                />
              ) : tab === "Provedores" ? (
                <ProvidersPanel
                  notify={setNotice}
                  onError={report}
                  onRefresh={() => refresh().catch(report)}
                />
              ) : tab === "Comportamento" ? (
                <div className="setting-group">
                  <div className="setting-heading">Desempenho</div>
                  <select
                    aria-label="Perfil de desempenho"
                    value={prefs.performance || "auto"}
                    onChange={(e) =>
                      update(
                        "performance",
                        e.target.value as Preferences["performance"],
                      )
                    }
                  >
                    <option value="auto">Automático por hardware</option>
                    <option value="notebook">Notebook econômico</option>
                    <option value="desktop">Desktop / mais contexto</option>
                  </select>
                  <p className="setting-note">
                    O perfil econômico usa contexto de 4K, respostas de até 768
                    tokens e libera o modelo após 2 minutos sem uso. Para maior
                    leveza, baixe opcionalmente o Qwen 2B em Inteligências.
                  </p>
                  <Toggle
                    title="Sempre no topo"
                    text="Mantenha a ALT-AI visível."
                    checked={pinned}
                    onChange={() =>
                      window.alt.window("pin").then((v) => {
                        setPinned(!!v);
                        update("always_on_top", !!v);
                      })
                    }
                  />
                  <p className="setting-note">
                    Arraste pela barra superior. A posição e o tamanho da janela
                    são restaurados automaticamente.
                  </p>
                  <p className="setting-note">
                    O botão × oculta na bandeja. Para encerrar o aplicativo e
                    seu backend, use Sair.
                  </p>
                  <button
                    className="secondary full"
                    onClick={() => window.alt.window("quit")}
                  >
                    <Power size={14} /> Sair da ALT-AI
                  </button>
                </div>
              ) : tab === "Modelos de IA" ? (
                <div className="setting-group">
                  <div className="setting-heading">Inteligência ativa</div>
                  <select
                    aria-label="Modelo padrão"
                    disabled={busy}
                    value={prefs.model}
                    onChange={(e) => update("model", e.target.value)}
                  >
                    <option value="">Selecionar modelo</option>
                    {models.map((m) => (
                      <option key={m.name} value={m.name}>
                        {m.provider || m.name}
                      </option>
                    ))}
                  </select>
                  <p className="setting-note">
                    Troque sem reiniciar. Apenas esta conversa e as memórias
                    selecionadas entram no contexto. Na nuvem, uma prévia e sua
                    autorização são obrigatórias.
                  </p>
                  <button
                    className="secondary full"
                    onClick={() => setView("models")}
                  >
                    <Boxes size={15} /> Gerenciar inteligências
                  </button>
                </div>
              ) : tab === "Atalhos" ? (
                <div className="setting-group">
                  <div className="shortcut">
                    <span>Abrir / ocultar</span>
                    <kbd>{prefs.shortcut}</kbd>
                  </div>
                  <div className="shortcut">
                    <span>Nova conversa</span>
                    <kbd>Ctrl N</kbd>
                  </div>
                  <div className="shortcut">
                    <span>Enviar</span>
                    <kbd>Enter</kbd>
                  </div>
                  <div className="shortcut">
                    <span>Nova linha</span>
                    <kbd>Shift Enter</kbd>
                  </div>
                  <div className="shortcut">
                    <span>Fechar painel</span>
                    <kbd>Esc</kbd>
                  </div>
                </div>
              ) : (
                <div className="setting-group">
                  <div className="about-brand">
                    <span className="brand-slash" /> ALT-AI
                  </div>
                  <p>Inteligência pessoal. Sob seu controle.</p>
                  <p className="setting-note">
                    Versão {appVersion} · Prévia em evolução
                    <br />
                    Electron · React · FastAPI · Ollama
                  </p>
                  <p className="setting-note">
                    Memória de continuidade, regras por capacidade, navegador e
                    nuvem com consentimento. Voz, GUI Windows genérica e iOS
                    continuam no roteiro.
                  </p>
                  <button
                    className="secondary full"
                    onClick={() => window.alt.openReleases()}
                  >
                    <ExternalLink size={14} />
                    Versões e instaladores
                  </button>
                  <button
                    className="secondary full"
                    onClick={() =>
                      window.alt
                        .checkUpdate()
                        .then((r) => {
                          if (r.available) {
                            localStorage.removeItem("alt-dismissed-update");
                            setNotice(`Nova versão ${r.version} disponível; confira as notas no aviso.`);
                            window.dispatchEvent(new CustomEvent("alt-update", { detail: r }));
                          } else setNotice(r.reason || "Nenhuma versão nova.");
                        })
                        .catch(report)
                    }
                  >
                    <RefreshCw size={14} />
                    Procurar nova versão
                  </button>
                  <button
                    className="secondary full"
                    onClick={() =>
                      window.alt
                        .verifyUpdate()
                        .then((result) => {
                          setUpdateVerified(result);
                          if (result)
                            setNotice(
                              `Assinatura e hash da versão ${result.version} conferidos.`,
                            );
                        })
                        .catch(report)
                    }
                  >
                    <Shield size={14} />
                    Verificar atualização baixada
                  </button>
                  {updateVerified && (
                    <div className="info-card">
                      <strong>
                        Versão {updateVerified.version} verificada
                      </strong>
                      <p>{updateVerified.file}</p>
                      <button
                        className="primary"
                        onClick={() => window.alt.applyUpdate().catch(report)}
                      >
                        Aplicar atualização
                      </button>
                    </div>
                  )}
                  <p className="setting-note">
                    Baixe instalador e manifesto da mesma release. A verificação
                    recusa adulteração e versões antigas. Certificado Windows
                    depende de configuração de assinatura.
                  </p>
                </div>
              )}
            </div>
            <div className="settings-footer">
              <span className="dot green" />
              {loaded
                ? "Preferências persistidas localmente"
                : "Inicializando…"}
              <Lock size={11} />
            </div>
          </aside>
        )}
      </div>
      {cloudPreview && (
        <div className="modal-backdrop">
          <div
            className="modal cloud-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Revisar envio à nuvem"
          >
            <div className="modal-icon">
              <Shield size={25} />
            </div>
            <h2>Este contexto sairá do computador.</h2>
            <p>
              {cloudPreview.provider.name}. {cloudPreview.billing_notice}
            </p>
            {cloudPreview.estimated_usd !== null && (
              <p>
                Estimativa conservadora: US${" "}
                {cloudPreview.estimated_usd.toFixed(5)} pelos preços que você
                configurou.
              </p>
            )}
            <p className="setting-note">
              Inclui personalidade, trecho desta conversa e memórias
              selecionadas. Nenhum arquivo é anexado automaticamente. A
              autorização vale para este pedido e expira em cinco minutos.
            </p>
            <div className="context-preview">
              {cloudPreview.messages.map((message, index) => (
                <details
                  key={index}
                  open={
                    message.role === "user" &&
                    index === cloudPreview.messages.length - 1
                  }
                >
                  <summary>
                    {message.role === "system"
                      ? "Personalidade e memórias"
                      : message.role === "user"
                        ? "Sua mensagem"
                        : "Resposta anterior"}{" "}
                    · {message.content.length} caracteres
                  </summary>
                  <pre>{message.content}</pre>
                </details>
              ))}
            </div>
            <div className="button-row">
              <button
                className="secondary"
                onClick={() => {
                  setCloudPreview(null);
                  setPendingAnalysis(null);
                }}
              >
                Cancelar
              </button>
              <button
                className="primary"
                disabled={busy}
                onClick={() =>
                  send(
                    cloudPreview.consent_receipt,
                    pendingAnalysis || undefined,
                  )
                }
              >
                Autorizar este envio
              </button>
            </div>
          </div>
        </div>
      )}
      {(confirmModel || deleteId) && (
        <div className="modal-backdrop">
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={
              confirmModel ? "Confirmar download" : "Excluir conversa"
            }
          >
            <div className="modal-icon">
              {confirmModel ? <Download size={25} /> : <Trash2 size={25} />}
            </div>
            <h2>
              {confirmModel
                ? "Adicionar inteligência local?"
                : "Excluir esta conversa?"}
            </h2>
            <p>
              {confirmModel
                ? `O Ollama baixará ${confirmModel} do registro oficial. O download ocupa vários GB e utiliza internet e espaço em disco. Nenhuma API paga será usada.`
                : "As mensagens serão excluídas do histórico local. Esta ação não pode ser desfeita pela interface."}
            </p>
            <div className="button-row">
              <button
                className="secondary"
                onClick={() => {
                  setConfirmModel("");
                  setDeleteId("");
                }}
              >
                Cancelar
              </button>
              <button
                className="primary"
                onClick={() => {
                  if (confirmModel) pull();
                  else {
                    const id = deleteId;
                    setDeleteId("");
                    api("DELETE", `/conversations/${id}`)
                      .then(async () => {
                        if (cid === id) {
                          setCid("");
                          setMessages([]);
                        }
                        await refreshConversations();
                      })
                      .catch(report);
                  }
                }}
              >
                {confirmModel ? "Autorizar download" : "Excluir conversa"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Range({
  title,
  value,
  min,
  max,
  suffix,
  onChange,
}: {
  title: string;
  value: number;
  min: number;
  max: number;
  suffix: string;
  onChange: (v: number) => void;
}) {
  return (
    <label className="range-setting">
      <span>
        {title}
        <b>
          {value}
          {suffix}
        </b>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={
          {
            "--progress": `${((value - min) / (max - min)) * 100}%`,
          } as CSSProperties
        }
      />
    </label>
  );
}
function Toggle({
  title,
  text,
  checked,
  onChange,
}: {
  title: string;
  text: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="toggle-setting">
      <span>
        <strong>{title}</strong>
        <small>{text}</small>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="switch" />
    </label>
  );
}
