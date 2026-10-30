import { useEffect, useState } from "react";
import { ContinuityPanel } from "./WorkspacePanels";
import { ProjectsPanel, WindowsPanel } from "./AgentPanels";
import {
  Plus,
  Save,
  Trash2,
  Download,
  Shield,
  FolderOpen,
  Check,
  X,
  Lock,
  RefreshCw,
  ExternalLink,
  Eye,
  Hand,
  Zap,
  Search,
  AppWindow,
} from "lucide-react";
import type {
  Memory,
  Personality,
  Preferences,
  ProviderStatus,
} from "../../../../packages/shared-types";
const api = <T,>(method: string, path: string, body?: unknown) =>
  window.alt.request<T>(method, path, body);
type Feedback = {
  notify: (message: string) => void;
  onError: (error: unknown) => void;
};
export const defaultPersonality: Personality = {
  name: "ALT-AI",
  tone: "Inspirada na Alt Cunningham e no JARVIS: direta, calma e precisa; obedece primeiro e comenta depois; humor seco e raro; leal ao usuário.",
  irony: 20,
  challenge: 15,
  warmth: 45,
  formality: 50,
  instructions: "",
};

export function PersonalityPanel({
  value,
  onChange,
}: {
  value: Personality;
  onChange: (p: Personality) => void;
}) {
  const p = value || defaultPersonality;
  function set<K extends keyof Personality>(key: K, v: Personality[K]) {
    onChange({ ...p, [key]: v });
  }
  return (
    <div className="setting-group feature-form">
      <div className="setting-heading">
        Identidade{" "}
        <button onClick={() => onChange(defaultPersonality)}>
          Restaurar padrão
        </button>
      </div>
      <p className="setting-note">
        Faz primeiro, comenta depois. Ironia e debate só aparecem com os
        controles acima de 40 e 60. O mesmo jeito em qualquer modelo.
      </p>
      <label>
        Nome
        <input
          value={p.name}
          maxLength={40}
          onChange={(e) => set("name", e.target.value)}
        />
      </label>
      <label>
        Direção de personalidade
        <textarea
          rows={4}
          value={p.tone}
          maxLength={600}
          onChange={(e) => set("tone", e.target.value)}
        />
      </label>
      {(
        [
          { key: "irony", name: "Ironia" },
          { key: "challenge", name: "Questionar ideias" },
          { key: "warmth", name: "Proximidade" },
          { key: "formality", name: "Formalidade" },
        ] as const
      ).map((item) => (
        <label key={item.key} className="feature-range">
          {item.name}
          <span>{p[item.key]}%</span>
          <input
            type="range"
            min={0}
            max={100}
            value={p[item.key]}
            onChange={(e) => set(item.key, Number(e.target.value))}
          />
        </label>
      ))}
      <label>
        Preferências de conversa
        <textarea
          rows={4}
          maxLength={3000}
          placeholder="Ex.: explique com exemplos; faça uma pergunta por vez."
          value={p.instructions}
          onChange={(e) => set("instructions", e.target.value)}
        />
      </label>
      <p className="setting-note">
        Esses ajustes mudam o estilo real das respostas. Permissões continuam
        controladas pelo aplicativo.
      </p>
    </div>
  );
}

export function AdvancedAppearance({
  prefs,
  onChange,
  notify,
  onError,
}: { prefs: Preferences; onChange: (p: Preferences) => void } & Feedback) {
  const [name, setName] = useState(""),
    [saved, setSaved] = useState<
      {
        name: string;
        accent: string;
        secondary: string;
        appearance: "dark" | "light";
        opacity: number;
        glow: number;
      }[]
    >([]);
  const [shortcut, setShortcut] = useState(prefs.shortcut),
    [width, setWidth] = useState(1130),
    [height, setHeight] = useState(800),
    [position, setPosition] = useState("center");
  useEffect(() => {
    api<typeof saved>("GET", "/themes").then(setSaved).catch(onError);
  }, []);
  const set = <K extends keyof Preferences>(key: K, value: Preferences[K]) =>
    onChange({ ...prefs, [key]: value });
  async function save() {
    try {
      await api("POST", "/themes", {
        name,
        accent: prefs.accent,
        secondary: prefs.secondary,
        appearance: prefs.appearance,
        opacity: prefs.opacity,
        glow: prefs.glow,
      });
      setSaved(await api("GET", "/themes"));
      setName("");
      notify("Tema salvo.");
    } catch (e) {
      onError(e);
    }
  }
  return (
    <div className="setting-group feature-form">
      <div className="setting-heading">Mais aparência</div>
      <label>
        Modo
        <select
          value={prefs.appearance}
          onChange={(e) =>
            set("appearance", e.target.value as Preferences["appearance"])
          }
        >
          <option value="dark">Escuro</option>
          <option value="light">Claro</option>
        </select>
      </label>
      <label>
        Cor secundária
        <input
          type="color"
          value={prefs.secondary}
          onChange={(e) => set("secondary", e.target.value)}
        />
      </label>
      <label className="feature-range">
        Escala<span>{Math.round(prefs.scale * 100)}%</span>
        <input
          type="range"
          min={0.8}
          max={1.3}
          step={0.05}
          value={prefs.scale}
          onChange={(e) => set("scale", Number(e.target.value))}
        />
      </label>
      <label className="feature-range">
        Opacidade da conversa<span>{prefs.chat_opacity}%</span>
        <input
          type="range"
          min={65}
          max={100}
          value={prefs.chat_opacity}
          onChange={(e) => set("chat_opacity", Number(e.target.value))}
        />
      </label>
      <label className="feature-range">
        Raio das bordas<span>{prefs.radius}px</span>
        <input
          type="range"
          min={0}
          max={24}
          value={prefs.radius}
          onChange={(e) => set("radius", Number(e.target.value))}
        />
      </label>
      <label className="inline-check">
        <input
          type="checkbox"
          checked={prefs.effects}
          onChange={(e) => set("effects", e.target.checked)}
        />
        Sombras e efeitos neon
      </label>
      <label>
        Salvar este tema
        <input
          placeholder="Nome do seu tema"
          value={name}
          maxLength={60}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <button className="secondary full" disabled={!name.trim()} onClick={save}>
        <Save size={14} />
        Salvar tema
      </button>
      {saved.length > 0 && (
        <label>
          Temas pessoais
          <select
            defaultValue=""
            onChange={(e) => {
              const theme = saved.find((t) => t.name === e.target.value);
              if (theme) {
                const { name, ...visual } = theme;
                onChange({ ...prefs, ...visual, theme: name });
              }
            }}
          >
            <option value="">Escolher tema salvo</option>
            {saved.map((t) => (
              <option key={t.name}>{t.name}</option>
            ))}
          </select>
        </label>
      )}
      <div className="setting-heading">Janela</div>
      <div className="form-columns">
        <label>
          Largura
          <input
            type="number"
            min={750}
            max={2500}
            value={width}
            onChange={(e) => setWidth(Number(e.target.value))}
          />
        </label>
        <label>
          Altura
          <input
            type="number"
            min={560}
            max={1600}
            value={height}
            onChange={(e) => setHeight(Number(e.target.value))}
          />
        </label>
      </div>
      <select
        aria-label="Posição da janela"
        value={position}
        onChange={(e) => setPosition(e.target.value)}
      >
        <option value="left">Esquerda</option>
        <option value="center">Centro</option>
        <option value="right">Direita</option>
      </select>
      <button
        className="secondary full"
        onClick={() =>
          window.alt.layout({ width, height, position }).catch(onError)
        }
      >
        Aplicar posição e tamanho
      </button>
      <label>
        Atalho global
        <input
          placeholder="Control+Shift+Space"
          value={shortcut}
          onChange={(e) => setShortcut(e.target.value)}
        />
      </label>
      <button
        className="secondary full"
        onClick={() => {
          if (
            !/^(Control|Alt)(\+(Control|Alt|Shift)){0,2}\+([A-Z]|Space|F[1-9]|F1[0-2])$/.test(
              shortcut,
            )
          ) {
            onError(
              new Error("Use, por exemplo, Control+Shift+Space ou Alt+F8."),
            );
            return;
          }
          set("shortcut", shortcut);
        }}
      >
        Aplicar atalho
      </button>
    </div>
  );
}

type Suggestion = { id: string; fact: string; flagged: string; created: string };
// Facts the ALT noticed in conversations: nothing becomes a memory until the owner approves it.
function MemorySuggestionsPanel({ notify, onError, onSaved }: Feedback & { onSaved: () => void }) {
  const [items, setItems] = useState<Suggestion[]>([]);
  const [enabled, setEnabled] = useState(false);
  const load = () => api<Suggestion[]>("GET", "/memories/suggestions").then(setItems).catch(onError);
  useEffect(() => {
    load();
    api<{ memory_suggestions?: boolean }>("GET", "/settings").then((s) => setEnabled(!!s.memory_suggestions)).catch(() => {});
  }, []);
  async function toggle() {
    try {
      const settings = await api<Record<string, unknown>>("GET", "/settings");
      await api("PUT", "/settings", { ...settings, memory_suggestions: !enabled });
      setEnabled(!enabled);
    } catch (e) { onError(e); }
  }
  return (
    <section className="memory-suggestions">
      <div className="setting-heading">Aprendidas nas conversas</div>
      <label className="toggle-line">
        <input type="checkbox" checked={enabled} onChange={toggle} />
        <span>Sugerir fatos sobre mim depois das conversas (eu aprovo cada um)</span>
      </label>
      {items.length === 0 ? <p className="setting-note">Nenhuma sugestão pendente.</p> : items.map((item) => (
        <div key={item.id} className="suggestion-row">
          <span>{item.fact}{item.flagged && <small className="voice-error"> · {item.flagged}</small>}</span>
          <button type="button" className="secondary" onClick={async () => {
            try { await api("POST", `/memories/suggestions/${item.id}/approve`); notify("Memória salva."); onSaved(); load(); } catch (e) { onError(e); }
          }}>Guardar</button>
          <button type="button" className="secondary" onClick={() => api("DELETE", `/memories/suggestions/${item.id}`).then(load).catch(onError)}>Descartar</button>
        </div>
      ))}
    </section>
  );
}

export function MemoryPanel({
  selected,
  onSelect,
  notify,
  onError,
  conversationId,
  model,
}: {
  selected: string[];
  onSelect: (ids: string[]) => void;
  conversationId: string | null;
  model: string;
} & Feedback) {
  const [items, setItems] = useState<Memory[]>([]),
    [search, setSearch] = useState(""),
    [editing, setEditing] = useState<string | null>(null),
    [confirmDelete, setConfirmDelete] = useState("");
  const [form, setForm] = useState({
    title: "",
    content: "",
    category: "preferência" as Memory["category"],
    enabled: true,
  });
  const refresh = () => api<Memory[]>("GET", "/memories").then(setItems);
  useEffect(() => {
    refresh().catch(onError);
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => {
      (search
        ? api<Memory[]>(
            "GET",
            "/memories/search?q=" + encodeURIComponent(search),
          )
        : api<Memory[]>("GET", "/memories")
      )
        .then(setItems)
        .catch(onError);
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);
  async function save() {
    try {
      await api(
        editing ? "PUT" : "POST",
        editing ? `/memories/${editing}` : "/memories",
        form,
      );
      setEditing(null);
      setForm({
        title: "",
        content: "",
        category: "preferência",
        enabled: true,
      });
      await refresh();
      notify("Memória salva. Selecione-a quando quiser usá-la no chat.");
    } catch (e) {
      onError(e);
    }
  }
  return (
    <div className="page-scroll">
      <MemorySuggestionsPanel notify={notify} onError={onError} onSaved={() => refresh().catch(onError)} />
      <ProjectsPanel
        conversationId={conversationId}
        model={model}
        notify={notify}
        onError={onError}
        onSaved={() => refresh().catch(onError)}
      />
      <ContinuityPanel
        conversationId={conversationId}
        model={model}
        notify={notify}
        onError={onError}
        onSaved={() => refresh().catch(onError)}
      />
      <p className="page-intro">
        Continuidade sem inventar lembranças.
        <br />
        <span>
          Guarde apenas o que você quer. Selecione até dez memórias para o
          próximo envio; a seleção vale nesta sessão.
        </span>
      </p>
      <div className="button-row">
        <button
          className="secondary"
          onClick={() =>
            window.alt
              .exportMemories()
              .then((r) => {
                if (r.saved) notify("Memórias exportadas.");
              })
              .catch(onError)
          }
        >
          <Download size={14} />
          Exportar JSON
        </button>
        <button
          className="secondary"
          onClick={() =>
            window.alt
              .importMemories()
              .then(async (result) => {
                if (result) {
                  await refresh();
                  notify(
                    `${result.imported} memórias importadas; ${result.skipped} duplicatas ignoradas.`,
                  );
                }
              })
              .catch(onError)
          }
        >
          Importar JSON
        </button>
        <button className="text-button" onClick={() => onSelect([])}>
          Limpar seleção ({selected.length})
        </button>
      </div>
      <div className="feature-form memory-editor">
        <label>
          Título
          <input
            value={form.title}
            maxLength={120}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
        </label>
        <label>
          Categoria
          <select
            value={form.category}
            onChange={(e) =>
              setForm({
                ...form,
                category: e.target.value as Memory["category"],
              })
            }
          >
            {["preferência", "projeto", "decisão", "contexto"].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          O que a ALT-AI deve lembrar
          <textarea
            rows={4}
            value={form.content}
            maxLength={6000}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
          />
        </label>
        <label className="inline-check">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
          />
          Disponível para seleção
        </label>
        <div className="button-row">
          <button
            className="primary"
            disabled={!form.title.trim() || !form.content.trim()}
            onClick={save}
          >
            <Save size={14} />
            {editing ? "Salvar edição" : "Criar memória"}
          </button>
          {editing && (
            <button
              className="secondary"
              onClick={() => {
                setEditing(null);
                setForm({
                  title: "",
                  content: "",
                  category: "preferência",
                  enabled: true,
                });
              }}
            >
              Cancelar edição
            </button>
          )}
        </div>
      </div>
      <input
        className="feature-search"
        placeholder="Buscar em títulos e conteúdo…"
        aria-label="Buscar memórias"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {items.map((m) => (
        <article className="memory-card" key={m.id}>
          <div className="memory-heading">
            <label className="inline-check">
              <input
                type="checkbox"
                disabled={
                  !m.enabled ||
                  (!selected.includes(m.id) && selected.length >= 10)
                }
                checked={selected.includes(m.id)}
                onChange={(e) =>
                  onSelect(
                    e.target.checked
                      ? [...selected, m.id]
                      : selected.filter((id) => id !== m.id),
                  )
                }
              />
              <strong>{m.title}</strong>
            </label>
            <span className="small-tag">{m.category}</span>
          </div>
          <p>{m.content}</p>
          <div className="button-row">
            <button
              className="text-button"
              onClick={() => {
                setEditing(m.id);
                setForm({
                  title: m.title,
                  content: m.content,
                  category: m.category,
                  enabled: m.enabled,
                });
              }}
            >
              Editar
            </button>
            <button
              className="text-button"
              onClick={() => setConfirmDelete(m.id)}
            >
              <Trash2 size={12} />
              Excluir
            </button>
            {!m.enabled && <span className="muted">Desativada</span>}
          </div>
          {confirmDelete === m.id && (
            <div className="inline-confirm">
              <span>Excluir esta memória local?</span>
              <button
                onClick={() => {
                  api("DELETE", `/memories/${m.id}`)
                    .then(async () => {
                      onSelect(selected.filter((id) => id !== m.id));
                      setConfirmDelete("");
                      await refresh();
                    })
                    .catch(onError);
                }}
              >
                Excluir
              </button>
              <button onClick={() => setConfirmDelete("")}>Cancelar</button>
            </div>
          )}
        </article>
      ))}
      {!items.length && (
        <p className="setting-note">
          Ainda não há memórias. Nenhuma lembrança é extraída automaticamente de
          suas conversas.
        </p>
      )}
    </div>
  );
}

type Permissions = {
  level: number;
  expires_in: number | null;
  scopes: { id: string; path: string }[];
};
type Proposal = {
  id: string;
  preview: {
    tool: string;
    path?: string;
    expression?: string;
    app?: string;
    url?: string;
    diff?: string;
    creates_file?: boolean;
  };
};
export function ToolsPanel({
  notify,
  onError,
  onCommand,
}: Feedback & { onCommand: (text: string) => void }) {
  const [permissions, setPermissions] = useState<Permissions | null>(null),
    [tool, setTool] = useState("calculate"),
    [scope, setScope] = useState(""),
    [path, setPath] = useState(""),
    [content, setContent] = useState(""),
    [expression, setExpression] = useState(""),
    [application, setApplication] = useState("notepad"),
    [url, setUrl] = useState(""),
    [query, setQuery] = useState("");
  const [proposal, setProposal] = useState<Proposal | null>(null),
    [result, setResult] = useState<unknown>(null),
    [history, setHistory] = useState<
      { id: string; tool: string; status: string }[]
    >([]),
    [busy, setBusy] = useState(false);
  const [programs, setPrograms] = useState<{ id: string; name: string }[]>([]);
  async function refresh() {
    const p = await api<Permissions>("GET", "/permissions");
    setPrograms(await api("GET", "/programs"));
    setPermissions(p);
    setScope((s) =>
      p.scopes.some((r) => r.id === s) ? s : p.scopes[0]?.id || "",
    );
    setHistory(await api("GET", "/tools/history"));
  }
  useEffect(() => {
    refresh().catch(onError);
    const id = setInterval(() => refresh().catch(onError), 10000);
    return () => clearInterval(id);
  }, []);
  async function propose() {
    setBusy(true);
    setResult(null);
    try {
      setProposal(
        await api("POST", "/tools/propose", {
          tool,
          scope_id: scope,
          path,
          content,
          expression,
          app: application,
          url,
          query,
        }),
      );
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  async function approve() {
    if (!proposal) return;
    setBusy(true);
    try {
      const data = await api<{ result: unknown }>(
        "POST",
        `/tools/approve/${proposal.id}`,
      );
      setResult(data.result);
      setProposal(null);
      notify("A ferramenta confirmou a execução.");
      await refresh();
    } catch (e) {
      setProposal(null);
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page-scroll">
      <div className="security-hero">
        <Shield size={30} />
        <h2>Seu comando. Seu alcance.</h2>
        <p>
          Peça à ALT no chat. Aqui você define o alcance da sessão, acompanha
          ações e pode revogar o acesso.
        </p>
      </div>
      <div className="subheading">
        <span>
          Modo:{" "}
          {permissions && permissions.level >= 2
            ? `${["", "", "Assistido", "Leitura autorizada", "Acesso total"][permissions.level]} · sem prazo · até você alterar`
            : "Observação"}
        </span>
        <button
          className="secondary"
          onClick={() =>
            api("PUT", "/permissions", {
              level: permissions?.level === 2 ? 1 : 2,
            })
              .then(() => refresh())
              .catch(onError)
          }
        >
          {permissions?.level === 2
            ? "Voltar à observação"
            : "Ativar modo assistido"}
        </button>
      </div>
      <div className="permission-grid">
        {[
          {
            level: 1,
            title: "Observação",
            icon: Eye,
            text: "Conversar e propor. Nenhuma ação executada.",
          },
          {
            level: 2,
            title: "Assistido",
            icon: Hand,
            text: "Sem prazo. Você aprova cada ação.",
          },
          {
            level: 3,
            title: "Leitura autorizada",
            icon: FolderOpen,
            text: "Até você alterar. Cálculos e leitura na pasta escolhida podem continuar sem novos cliques.",
          },
          {
            level: 4,
            title: "Acesso total",
            icon: Zap,
            text: "Até você alterar. Internet, sites no seu navegador, downloads, arquivos, qualquer programa instalado, janelas e tarefas executam sem pedir aprovação, salvo o que você bloquear. Comandos do PowerShell pedem aprovação.",
          },
        ].map((mode) => (
          <button
            key={mode.level}
            className={`permission-card ${permissions?.level === mode.level ? "chosen" : ""}`}
            onClick={() => {
              if (mode.level <= 2)
                api("PUT", "/permissions", { level: mode.level })
                  .then(() => refresh())
                  .catch(onError);
              else
                window.alt
                  .grantWindows(mode.level as 3 | 4, scope)
                  .then(async (result) => {
                    await refresh();
                    if (mode.level === 4 && (result as Permissions).level === 4)
                      setScope("windows-profile");
                  })
                  .catch(onError);
            }}
          >
            <strong>
              <mode.icon size={16} />
              {mode.title}
            </strong>
            <p>{mode.text}</p>
            {permissions?.level === mode.level && <Check size={15} />}
          </button>
        ))}
      </div>
      <p className="setting-note">
        Acesso total nunca inclui arquivos de credenciais, AppData, privilégios
        de administrador ou executar arquivos baixados. Comandos do PowerShell
        sempre mostram um cartão para aprovar. STOP revoga tudo na hora.
      </p>
      <div className="command-shortcuts">
        <button
          onClick={() =>
            onCommand(
              "Pesquise na internet a documentação oficial do Ollama e me mostre as fontes.",
            )
          }
        >
          <Search size={14} />
          Pesquisar na internet
        </button>
        <button onClick={() => onCommand("Abra o Bloco de Notas.")}>
          <AppWindow size={14} />
          Abrir um aplicativo
        </button>
        <button
          onClick={() => onCommand("Liste os arquivos da pasta autorizada.")}
        >
          <FolderOpen size={14} />
          Explorar uma pasta
        </button>
      </div>
      <details className="manual-tools">
        <summary>Controles manuais e configuração de pastas</summary>
        <div className="feature-form">
          <label>
            Pasta autorizada
            <select
              value={scope}
              onChange={(e) => {
                setScope(e.target.value);
                setProposal(null);
              }}
            >
              {permissions?.scopes.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.path}
                </option>
              ))}
            </select>
          </label>
          <button
            className="secondary"
            onClick={() =>
              window.alt
                .chooseWorkspace()
                .then(() => refresh())
                .catch(onError)
            }
          >
            <FolderOpen size={14} />
            Escolher outra pasta
          </button>
          <button
            className="text-button"
            disabled={!scope || scope === "windows-profile"}
            onClick={() =>
              api("DELETE", `/scopes/${scope}`)
                .then(() => refresh())
                .catch(onError)
            }
          >
            Remover autorização desta pasta
          </button>
          <label>
            Ferramenta
            <select
              value={tool}
              onChange={(e) => {
                setTool(e.target.value);
                setProposal(null);
              }}
            >
              {[
                { id: "calculate", name: "Calcular expressão" },
                { id: "list_files", name: "Listar pasta" },
                { id: "find_files", name: "Buscar arquivos em subpastas" },
                { id: "read_text", name: "Ler texto" },
                { id: "write_text", name: "Criar / editar texto" },
                { id: "open_folder", name: "Abrir pasta" },
                { id: "open_app", name: "Abrir aplicativo autorizado" },
                {
                  id: "close_app",
                  name: "Solicitar fechamento de aplicativo aberto pela ALT",
                },
                { id: "open_url", name: "Abrir página HTTPS" },
                { id: "web_search", name: "Pesquisar na internet" },
                { id: "read_webpage", name: "Ler página pública" },
              ].map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          {[
            "list_files",
            "find_files",
            "read_text",
            "write_text",
            "open_folder",
          ].includes(tool) && (
            <label>
              Caminho relativo
              <input
                value={path}
                placeholder="Ex.: projeto/notas.md; vazio usa a pasta raiz"
                onChange={(e) => {
                  setPath(e.target.value);
                  setProposal(null);
                }}
              />
            </label>
          )}
          {tool === "write_text" && (
            <label>
              Conteúdo novo
              <textarea
                rows={7}
                value={content}
                maxLength={30000}
                onChange={(e) => {
                  setContent(e.target.value);
                  setProposal(null);
                }}
              />
            </label>
          )}
          {tool === "calculate" && (
            <label>
              Expressão
              <input
                value={expression}
                placeholder="Ex.: (120 + 35) * 2"
                maxLength={200}
                onChange={(e) => {
                  setExpression(e.target.value);
                  setProposal(null);
                }}
              />
            </label>
          )}
          {["open_app", "close_app"].includes(tool) && (
            <label>
              Aplicativo
              <select
                value={application}
                onChange={(e) => {
                  setApplication(e.target.value);
                  setProposal(null);
                }}
              >
                {programs.map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {(tool === "open_url" || tool === "read_webpage") && (
            <label>
              URL HTTPS
              <input
                value={url}
                placeholder="https://…"
                maxLength={2000}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setProposal(null);
                }}
              />
            </label>
          )}
          {["web_search", "find_files"].includes(tool) && (
            <label>
              Assunto da pesquisa
              <input
                value={query}
                maxLength={300}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setProposal(null);
                }}
              />
            </label>
          )}
          <button className="primary" disabled={busy} onClick={propose}>
            Revisar proposta
          </button>
        </div>
      </details>
      {proposal && (
        <div className="proposal-card">
          <h3>Uma aprovação. Uma ação.</h3>
          <pre>
            {JSON.stringify({ ...proposal.preview, diff: undefined }, null, 2)}
          </pre>
          {proposal.preview.diff !== undefined && (
            <pre className="diff-preview">
              {proposal.preview.diff || "(sem diferença de conteúdo)"}
            </pre>
          )}
          <p className="setting-note">
            Expira em cinco minutos. Se o arquivo mudar, a gravação será
            recusada.
          </p>
          <div className="button-row">
            <button
              className="primary"
              disabled={busy || !permissions || permissions.level < 2}
              onClick={approve}
            >
              <Check size={14} />
              Aprovar e executar
            </button>
            <button
              className="secondary"
              onClick={() => {
                api("POST", `/tools/reject/${proposal.id}`).catch(onError);
                setProposal(null);
              }}
            >
              Recusar
            </button>
          </div>
          {(!permissions || permissions.level < 2) && (
            <p className="setting-note">
              Ative o modo assistido para executar.
            </p>
          )}
        </div>
      )}
      {result !== null && (
        <div className="proposal-card">
          <h3>Resultado confirmado</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
      <div className="subheading">
        <span>Histórico de ações</span>
        <button
          className="text-button"
          onClick={() => refresh().catch(onError)}
        >
          <RefreshCw size={12} />
          Atualizar
        </button>
      </div>
      {history.slice(0, 20).map((h) => (
        <div className="action-row" key={h.id}>
          <span>{h.tool}</span>
          <span className="small-tag">{h.status}</span>
        </div>
      ))}
      <button
        className="stop-button"
        onClick={() =>
          api("POST", "/permissions/revoke")
            .then(() => {
              setProposal(null);
              return refresh();
            })
            .catch(onError)
        }
      >
        Revogar permissões e propostas
      </button>
      <WindowsPanel notify={notify} onError={onError} />
    </div>
  );
}

type AnthropicConfig = {
  enabled: boolean;
  model: string;
  input_usd_per_million: number;
  output_usd_per_million: number;
  request_limit_usd: number;
  session_limit_usd: number;
  daily_limit_usd: number;
  monthly_limit_usd: number;
};
type ProviderData = {
  providers: ProviderStatus[];
  anthropic: AnthropicConfig;
  key_configured: boolean;
  usage: { session: number; daily: number; monthly: number };
};
export function ProvidersPanel({
  notify,
  onError,
  onRefresh,
}: Feedback & { onRefresh: () => void }) {
  const [data, setData] = useState<ProviderData | null>(null),
    [config, setConfig] = useState<AnthropicConfig | null>(null),
    [key, setKey] = useState(""),
    [busy, setBusy] = useState(false);
  async function refresh() {
    const data = await api<ProviderData>("GET", "/providers");
    setData(data);
    setConfig(data.anthropic);
    onRefresh();
  }
  useEffect(() => {
    refresh().catch(onError);
  }, []);
  async function saveKey() {
    setBusy(true);
    try {
      const response = await window.alt.setAnthropicKey(key);
      setKey("");
      notify(
        response.message ||
          (response.configured
            ? "Chave guardada no cofre Windows."
            : "Nenhuma chave salva."),
      );
      await refresh();
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="setting-group feature-form">
      <div className="setting-heading">Provedores oficiais</div>
      {data?.providers.map((p) => (
        <div key={p.id} className="provider-state">
          <strong>{p.name}</strong>
          <span className="small-tag">
            {p.available ? "Disponível" : "Indisponível"}
          </span>
          <p>{p.reason}</p>
        </div>
      ))}
      <button
        className="secondary full"
        onClick={() => refresh().catch(onError)}
      >
        <RefreshCw size={13} />
        Verificar integrações
      </button>
      <p className="setting-note">
        Codex usa apenas login ChatGPT do CLI oficial compatível. O aplicativo
        revisa o contexto antes de cada envio à nuvem. Nenhum fallback inicia
        gastos automaticamente.
      </p>
      {config && (
        <>
          <div className="setting-heading">Claude pela API (opcional)</div>
          <label>
            Chave Anthropic
            <input
              type="password"
              autoComplete="off"
              spellCheck={false}
              placeholder={
                data?.key_configured
                  ? "Chave já protegida no Windows"
                  : "sk-ant-…"
              }
              value={key}
              onChange={(e) => setKey(e.target.value)}
              maxLength={500}
            />
          </label>
          <button
            className="secondary full"
            disabled={busy || !key}
            onClick={saveKey}
          >
            Salvar e verificar chave
          </button>
          {data?.key_configured && (
            <button
              className="text-button"
              onClick={() =>
                window.alt
                  .setAnthropicKey("")
                  .then(() => refresh())
                  .catch(onError)
              }
            >
              Remover chave do cofre
            </button>
          )}
          <label>
            Identificador do modelo
            <input
              value={config.model}
              placeholder="Informe um modelo disponível na sua API"
              onChange={(e) => setConfig({ ...config, model: e.target.value })}
            />
          </label>
          {(
            [
              {
                key: "input_usd_per_million",
                label: "USD por milhão de tokens de entrada",
              },
              {
                key: "output_usd_per_million",
                label: "USD por milhão de tokens de saída",
              },
              { key: "request_limit_usd", label: "Limite por pedido · USD" },
              { key: "session_limit_usd", label: "Limite por sessão · USD" },
              { key: "daily_limit_usd", label: "Limite diário · USD" },
              { key: "monthly_limit_usd", label: "Limite mensal · USD" },
            ] as const
          ).map((field) => (
            <label key={field.key}>
              {field.label}
              <input
                type="number"
                min={0}
                step={0.01}
                value={config[field.key]}
                onChange={(e) =>
                  setConfig({ ...config, [field.key]: Number(e.target.value) })
                }
              />
            </label>
          ))}
          <label className="inline-check">
            <input
              type="checkbox"
              checked={config.enabled}
              onChange={(e) =>
                setConfig({ ...config, enabled: e.target.checked })
              }
            />
            Habilitar API paga com esses limites
          </label>
          <p className="setting-note">
            Informe preços atuais do seu modelo. Os valores são estimativas, não
            saldo da conta. Assinatura Claude não paga esses pedidos.
          </p>
          <button
            className="primary full"
            onClick={() =>
              api("PUT", "/providers/anthropic", config)
                .then(async () => {
                  notify(
                    "Configuração da API salva. Envios ainda exigem confirmação.",
                  );
                  await refresh();
                })
                .catch(onError)
            }
          >
            Salvar configuração
          </button>
          <p className="setting-note">
            Estimado nesta sessão: US$ {data?.usage.session.toFixed(4)}
            <br />
            Hoje: US$ {data?.usage.daily.toFixed(4)} · Mês: US${" "}
            {data?.usage.monthly.toFixed(4)}
          </p>
        </>
      )}
    </div>
  );
}
