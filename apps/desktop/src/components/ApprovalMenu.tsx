import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Shield } from "lucide-react";

type Permissions = { level: number; auto_scopes: string[]; scopes: { id: string; path: string }[] };
export function ApprovalMenu({ disabled, onError }: { disabled: boolean; onError: (e: unknown) => void }) {
  const [open, setOpen] = useState(false);
  const [permissions, setPermissions] = useState<Permissions | null>(null);
  const [working, setWorking] = useState(false);
  const [scope, setScope] = useState("");
  const root = useRef<HTMLDivElement>(null);
  async function refresh() {
    const value = await window.alt.request<Permissions>("GET", "/permissions");
    setPermissions(value);
    setScope(old => value.scopes.some(s => s.id === old && s.id !== "windows-profile") ? old : value.scopes.find(s => s.id !== "windows-profile")?.id || "");
  }
  useEffect(() => { refresh().catch(onError); }, []);
  useEffect(() => {
    if (!open) return;
    refresh().catch(onError);
    const close = (e: PointerEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("pointerdown", close); document.removeEventListener("keydown", key); };
  }, [open]);
  useEffect(() => { refresh().catch(onError); if (disabled) setOpen(false); }, [disabled]);
  const modes = [
    { level: 1, name: "Somente conversar", text: "Conversa e propostas, sem executar ações." },
    { level: 2, name: "Pedir aprovação", text: "Você revisa e aprova cada ação." },
    { level: 3, name: "Usar minhas regras", text: "Pasta escolhida, leitura e cálculo autorizados; demais ações seguem suas regras." },
    { level: 4, name: "Acesso amplo", text: "Perfil pessoal e pastas autorizadas. Suas regras valem; ações sensíveis continuam supervisionadas." },
  ];
  async function change(level: number) {
    setWorking(true);
    try {
      if (level <= 2) await window.alt.request("PUT", "/permissions", { level });
      else await window.alt.grantWindows(level as 3 | 4, scope);
      await refresh();
      setOpen(false);
    } catch (e) { onError(e); }
    finally { setWorking(false); }
  }
  return <div className="approval-control" ref={root}>
    <button type="button" className="approval-trigger" disabled={disabled || working} aria-expanded={open} aria-haspopup="dialog" onClick={() => setOpen(!open)}>
      <Shield size={13} /><span>{modes.find(m => m.level === permissions?.level)?.name || "Permissões"}</span><ChevronDown size={12} />
    </button>
    {open && <div className="approval-popover" role="dialog" aria-label="Aprovação de ações">
      <strong>Como a ALT pode agir?</strong>
      <p>Permanece assim até você alterar ou revogar.</p>
      {modes.map(mode => <button type="button" key={mode.level} className={permissions?.level === mode.level ? "chosen" : ""} disabled={working || disabled} onClick={() => change(mode.level)}>
        <span><b>{mode.name}</b><small>{mode.text}</small></span>{permissions?.level === mode.level && <Check size={16} />}
      </button>)}
      <label>Pasta para “Usar minhas regras”<select value={scope} disabled={working} onChange={e => setScope(e.target.value)}>{permissions?.scopes.filter(s => s.id !== "windows-profile").map(s => <option value={s.id} key={s.id}>{s.path}</option>)}</select></label>
      <button type="button" disabled={working} onClick={async () => { try { await window.alt.chooseWorkspace(); await refresh(); } catch (e) { onError(e); } }}>Escolher outra pasta</button>
      <small className="approval-note">O alcance é o da sua conta Windows. Sistema, credenciais e elevação administrativa ficam fora deste modo. Ajuste cada capacidade em Controle e regras.</small>
    </div>}
  </div>;
}
