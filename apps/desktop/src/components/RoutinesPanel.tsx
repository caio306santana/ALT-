import { useEffect, useState } from "react";
import type { Preferences } from "../../../../packages/shared-types";

type Routine = { id: string; name: string; prompt: string; enabled: boolean; next_run: string | null; last_run: string | null; schedule: Record<string, unknown> };
type Reminder = { id: string; due: string; text: string };
type Update = <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
const api = <T,>(method: string, path: string, body?: unknown) => window.alt.request<T>(method, path, body);
const when = (iso: string | null) => iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "—";

// Everything the ALT does on its own schedule: briefing, check-ins, topics, PC alerts, routines, reminders.
export function RoutinesPanel({ prefs, update, notify, onError }: { prefs: Preferences; update: Update; notify: (t: string) => void; onError: (e: unknown) => void }) {
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [form, setForm] = useState({ name: "", schedule: "diário 18:00", prompt: "" });
  const [topic, setTopic] = useState("");
  const [running, setRunning] = useState(false);
  const load = () => {
    api<Routine[]>("GET", "/routines").then(setRoutines).catch(onError);
    api<Reminder[]>("GET", "/reminders").then(setReminders).catch(onError);
  };
  useEffect(load, []);
  const topics = prefs.topics || [];
  return (
    <div className="page-scroll routines-page">
      <section>
        <div className="setting-heading">Resumo da manhã</div>
        <label className="toggle-line"><input type="checkbox" checked={!!prefs.briefing_enabled} onChange={() => update("briefing_enabled", !prefs.briefing_enabled)} /><span>Fazer o resumo da manhã</span></label>
        <label>Horário<input type="time" value={prefs.briefing_time || "08:00"} onChange={(e) => update("briefing_time", e.target.value)} /></label>
        <label>Cidade para o clima (consulta o Open-Meteo, sem conta)
          <input value={prefs.weather_city || ""} placeholder="Ex.: Curitiba" maxLength={80} onChange={(e) => update("weather_city", e.target.value)} />
        </label>
        <label className="toggle-line"><input type="checkbox" checked={prefs.briefing_voice !== false} onChange={() => update("briefing_voice", prefs.briefing_voice === false)} /><span>Ler em voz alta</span></label>
        <p className="setting-note">Bom dia, hora, clima, lembretes de hoje, o que ficou da última conversa e novidades dos seus tópicos. Só fatos: um número que não veio dos dados faz a ALT refazer o texto. Se o PC estiver desligado no horário, sai na primeira vez que ele ligar depois.</p>
        <div className="button-row">
          <button type="button" className="secondary" disabled={running} onClick={async () => {
            setRunning(true);
            try { const r = await api<{ text: string }>("POST", "/briefing/run"); notify(r.text); } catch (e) { onError(e); }
            finally { setRunning(false); }
          }}>{running ? "Preparando…" : "Ouvir o resumo agora"}</button>
        </div>
      </section>
      <section>
        <div className="setting-heading">Puxar conversa</div>
        <label className="toggle-line"><input type="checkbox" checked={!!prefs.proactive_enabled} onChange={() => update("proactive_enabled", !prefs.proactive_enabled)} /><span>A ALT pode falar primeiro</span></label>
        <p className="setting-note">Só depois de 15 minutos sem conversa, no mínimo 20 minutos entre uma e outra, nunca durante uma resposta, e ela pode decidir ficar quieta.</p>
        <label>No máximo por dia<input type="number" min={1} max={12} value={prefs.proactive_daily_cap || 4} onChange={(e) => update("proactive_daily_cap", Number(e.target.value))} /></label>
        <div className="inline-fields">
          <label>Silêncio das<input type="time" value={prefs.quiet_start || "22:00"} onChange={(e) => update("quiet_start", e.target.value)} /></label>
          <label>até<input type="time" value={prefs.quiet_end || "08:00"} onChange={(e) => update("quiet_end", e.target.value)} /></label>
        </div>
      </section>
      <section>
        <div className="setting-heading">Tópicos acompanhados</div>
        <p className="setting-note">Uma busca por dia em cada tópico; ela avisa só quando a manchete principal muda.</p>
        <div className="program-chips">
          {topics.map((t) => <span key={t} className="attachment-chip"><span>{t}</span><button type="button" aria-label={"Remover " + t} onClick={() => update("topics", topics.filter((x) => x !== t))}>×</button></span>)}
        </div>
        <form className="inline-fields" onSubmit={(e) => { e.preventDefault(); if (topic.trim() && topics.length < 10) update("topics", [...topics, topic.trim().slice(0, 60)]); setTopic(""); }}>
          <input value={topic} placeholder="Ex.: RTX 5070, Cyberpunk 2077" onChange={(e) => setTopic(e.target.value)} />
          <button type="submit" className="secondary">Adicionar</button>
        </form>
      </section>
      <section>
        <div className="setting-heading">Alertas do PC</div>
        <label className="toggle-line"><input type="checkbox" checked={!!prefs.pc_alerts} onChange={() => update("pc_alerts", !prefs.pc_alerts)} /><span>Avisar quando processador ou memória passarem de 90% por 30 s</span></label>
      </section>
      <section>
        <div className="setting-heading">Rotinas: {routines.length}</div>
        <p className="setting-note">Rodam sozinhas no horário e respondem com texto numa notificação; para ações, use lembretes ou Tarefas. Você também pode pedir no chat: “todo dia às 18h me lembra de alongar”.</p>
        {routines.map((r) => (
          <div key={r.id} className="suggestion-row">
            <span><b>{r.name}</b> · próxima {when(r.next_run)}<br /><small>{r.prompt}</small></span>
            <label className="toggle-line"><input type="checkbox" checked={r.enabled} onChange={() => api("PUT", `/routines/${r.id}`, { enabled: !r.enabled }).then(load).catch(onError)} />ativa</label>
            <button type="button" className="secondary" onClick={() => api<{ text: string }>("POST", `/routines/${r.id}/run`).then((x) => { notify(x.text); load(); }).catch(onError)}>Rodar agora</button>
            <button type="button" className="secondary" onClick={() => api("DELETE", `/routines/${r.id}`).then(load).catch(onError)}>Apagar</button>
          </div>
        ))}
        <form className="routine-form" onSubmit={(e) => { e.preventDefault(); api("POST", "/routines", form).then(() => { setForm({ name: "", schedule: "diário 18:00", prompt: "" }); load(); }).catch(onError); }}>
          <input value={form.name} placeholder="Nome" maxLength={80} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input value={form.schedule} placeholder="diário 08:00 · seg,qua 18:00 · a cada 60 min" maxLength={80} onChange={(e) => setForm({ ...form, schedule: e.target.value })} />
          <input value={form.prompt} placeholder="O que a ALT deve dizer ou lembrar" maxLength={1000} onChange={(e) => setForm({ ...form, prompt: e.target.value })} />
          <button type="submit" className="secondary">Criar rotina</button>
        </form>
      </section>
      <section>
        <div className="setting-heading">Lembretes: {reminders.length}</div>
        <p className="setting-note">Tocam pelo Agendador do Windows, mesmo com a ALT fechada.</p>
        {reminders.map((r) => (
          <div key={r.id} className="suggestion-row">
            <span>{when(r.due)} · {r.text}</span>
            <button type="button" className="secondary" onClick={() => api("DELETE", `/reminders/${r.id}`).then(load).catch(onError)}>Cancelar</button>
          </div>
        ))}
      </section>
    </div>
  );
}
