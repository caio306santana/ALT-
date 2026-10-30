import { useEffect, useState } from "react";

type Device = { id: string; name: string; created: string; last_seen: string | null };
type Status = { installed: boolean; running: boolean; host: string; enabled: boolean; url: string; devices: Device[]; serving: boolean };
type Pairing = { code: string; url: string; qr: string; expires_in: number };
const api = <T,>(method: string, path: string) => window.alt.request<T>(method, path);

// The ALT on the iPhone through Tailscale (tailnet only, real HTTPS); pairing by a one-time QR code.
export function RemotePanel({ onError }: { onError: (e: unknown) => void }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [pairing, setPairing] = useState<Pairing | null>(null);
  const [left, setLeft] = useState(0);
  const [working, setWorking] = useState(false);
  const load = () => api<Status>("GET", "/remote/status").then(setStatus).catch(onError);
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!pairing) return;
    setLeft(pairing.expires_in);
    const timer = setInterval(() => setLeft((s) => {
      if (s <= 1) { clearInterval(timer); setPairing(null); load(); return 0; }
      return s - 1;
    }), 1000);
    return () => clearInterval(timer);
  }, [pairing]);
  async function act(path: string) {
    setWorking(true);
    try { setStatus(await api<Status>("POST", path)); } catch (e) { onError(e); }
    finally { setWorking(false); }
  }
  return (
    <section className="remote-panel">
      <h3>Celular (iPhone, sem App Store)</h3>
      {!status ? <p className="setting-note">Verificando o Tailscale…</p> : !status.installed ? (
        <p className="setting-note">
          Instale o Tailscale (grátis) no PC e no iPhone e entre com a mesma conta: tailscale.com/download. Ele cria uma rede
          privada só entre os seus aparelhos, com HTTPS de verdade. Depois volte aqui. Passo a passo em docs/IPHONE.md.
        </p>
      ) : !status.running ? (
        <p className="setting-note">Abra o Tailscale no PC e entre na sua conta.</p>
      ) : (
        <>
          <p className="setting-note">
            {status.enabled ? <>Ligado em <b>{status.url}</b>. Só aparelhos da sua tailnet chegam aqui, e nada roda sozinho a partir do celular: cada ação vira um cartão, e comandos só são aprovados no PC.</>
              : <>O PC está na sua tailnet como {status.host}. Ligar publica a ALT só para os seus aparelhos (tailscale serve, nunca funnel).</>}
          </p>
          <div className="button-row">
            {status.enabled
              ? <><button type="button" className="secondary" disabled={working} onClick={async () => {
                    try { setPairing(await window.alt.request<Pairing>("POST", "/remote/pair")); } catch (e) { onError(e); }
                  }}>Parear um iPhone</button>
                  <button type="button" className="secondary" disabled={working} onClick={() => act("/remote/disable")}>Desligar acesso pelo celular</button></>
              : <button type="button" className="primary" disabled={working} onClick={() => act("/remote/enable")}>Ligar acesso pelo celular</button>}
          </div>
          {pairing && (
            <div className="pairing">
              <img src={pairing.qr} alt="QR code de pareamento" width={220} height={220} />
              <p>Abra a câmera do iPhone no QR code, ou entre em {status.url} e digite <b>{pairing.code}</b>. Vale por {left} s e uma vez só.</p>
              <p className="setting-note">No Safari: Compartilhar → Adicionar à Tela de Início.</p>
            </div>
          )}
          {status.devices.length > 0 && <h4>Aparelhos pareados</h4>}
          {status.devices.map((d) => (
            <div key={d.id} className="suggestion-row">
              <span>{d.name} · último acesso {d.last_seen ? new Date(d.last_seen).toLocaleString("pt-BR") : "—"}</span>
              <button type="button" className="secondary" onClick={() => window.alt.request("DELETE", `/remote/devices/${d.id}`).then(load).catch(onError)}>Revogar</button>
            </div>
          ))}
        </>
      )}
    </section>
  );
}
