// ALT on the iPhone: talks only to the PC's gateway (same origin). Actions arrive as cards; nothing runs
// by itself, and PowerShell commands are approved only on the PC.
const $ = (id) => document.getElementById(id);
const state = { cid: localStorage.getItem("alt-cid") || "", speak: localStorage.getItem("alt-speak") === "1", pending: [] };

async function api(method, path, body, raw) {
  const options = { method, credentials: "same-origin", headers: {} };
  if (raw) { options.body = raw.data; options.headers = raw.headers; }
  else if (body !== undefined) { options.body = JSON.stringify(body); options.headers["Content-Type"] = "application/json"; }
  const response = await fetch(path, options);
  if (response.status === 401) { showPair(); throw new Error("Pareie este aparelho no PC."); }
  if (!response.ok) {
    let detail = "Falha ao falar com o PC.";
    try { detail = (await response.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  return response;
}

function showPair(message) {
  $("pair").hidden = false; $("messages").hidden = true; $("composer").hidden = true;
  $("status").textContent = "não pareado";
  if (message) $("pairMessage").textContent = message;
}

function showChat() { $("pair").hidden = true; $("messages").hidden = false; $("composer").hidden = false; }

function bubble(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + role; div.textContent = text;
  $("messages").appendChild(div); div.scrollIntoView({ block: "end" });
  return div;
}

function notice(text) {
  const div = document.createElement("div"); div.className = "notice"; div.textContent = text;
  $("messages").appendChild(div); div.scrollIntoView({ block: "end" });
}

function card(proposal) {
  const preview = proposal.preview || {};
  const div = document.createElement("div"); div.className = "card";
  const title = document.createElement("b"); title.textContent = String(preview.tool || "ação").replaceAll("_", " ");
  const detail = document.createElement("p");
  detail.textContent = String(preview.command || preview.app || preview.url || preview.query || preview.path || preview.text || "Ação proposta pela ALT");
  div.append(title, detail);
  if (preview.tool === "run_command" || preview.critical) {
    const p = document.createElement("p"); p.textContent = "Aprove esta ação no PC."; div.appendChild(p);
  } else {
    const row = document.createElement("div"); row.className = "row";
    const ok = document.createElement("button"); ok.className = "primary"; ok.textContent = "Aprovar";
    const no = document.createElement("button"); no.textContent = "Recusar";
    ok.onclick = async () => {
      ok.disabled = no.disabled = true;
      try { const r = await (await api("POST", `/api/actions/${proposal.id}/approve`)).json(); detail.textContent = "Feito: " + JSON.stringify(r.result || r).slice(0, 160); }
      catch (e) { detail.textContent = e.message; ok.disabled = no.disabled = false; }
    };
    no.onclick = async () => { await api("POST", `/api/actions/${proposal.id}/reject`).catch(() => {}); div.remove(); };
    row.append(ok, no); div.appendChild(row);
  }
  $("messages").appendChild(div); div.scrollIntoView({ block: "end" });
}

async function ensureConversation() {
  if (state.cid) return state.cid;
  const c = await (await api("POST", "/api/conversations")).json();
  state.cid = c.id; localStorage.setItem("alt-cid", c.id); return c.id;
}

async function loadHistory() {
  $("messages").textContent = "";
  if (!state.cid) { notice("Conversa nova. Fale ou escreva."); return; }
  try {
    const rows = await (await api("GET", `/api/conversations/${state.cid}/messages`)).json();
    rows.slice(-30).forEach((m) => bubble(m.role, m.content));
  } catch (e) { state.cid = ""; localStorage.removeItem("alt-cid"); notice("Conversa nova."); }
}

async function play(text) {
  if (!state.speak || !text.trim()) return;
  try {
    const wav = await (await api("POST", "/api/speak", { text })).blob();
    const audio = new Audio(URL.createObjectURL(wav)); await audio.play();
  } catch (e) {}
}

async function send(text) {
  text = (text || "").trim();
  if (!text && !state.pending.length) return;
  $("send").disabled = true;
  bubble("user", text || "📷");
  const waiting = bubble("assistant", "…");
  try {
    const cid = await ensureConversation();
    const r = await (await api("POST", "/api/chat", { conversation_id: cid, content: text || "Veja a foto.", attachment_ids: state.pending })).json();
    state.pending = [];
    waiting.textContent = r.text || (r.status === "complete" ? "Pronto." : "Não consegui responder.");
    (r.notices || []).forEach(notice);
    (r.proposals || []).forEach(card);
    play(r.text || "");
  } catch (e) { waiting.textContent = e.message; }
  finally { $("send").disabled = false; }
}

// Microphone: 16 kHz mono PCM for the PC's Whisper (needs HTTPS, which Tailscale serve provides).
let recorder = null;
async function startMic() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  const context = new AudioContext({ sampleRate: 16000 });
  const source = context.createMediaStreamSource(stream);
  const node = context.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  node.onaudioprocess = (e) => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  source.connect(node); node.connect(context.destination);
  recorder = { stream, context, node, source, chunks };
  $("mic").classList.add("on");
}
async function stopMic() {
  if (!recorder) return;
  const { stream, context, node, source, chunks } = recorder; recorder = null;
  $("mic").classList.remove("on");
  node.disconnect(); source.disconnect(); stream.getTracks().forEach((t) => t.stop());
  const rate = context.sampleRate; await context.close();
  let samples = chunks.reduce((n, c) => n + c.length, 0);
  const data = new Float32Array(samples); let offset = 0;
  chunks.forEach((c) => { data.set(c, offset); offset += c.length; });
  // Safari may ignore the requested rate: resample to 16 kHz.
  const ratio = rate / 16000; samples = Math.floor(data.length / ratio);
  const pcm = new Int16Array(samples);
  for (let i = 0; i < samples; i++) pcm[i] = Math.max(-1, Math.min(1, data[Math.floor(i * ratio)])) * 0x7fff;
  if (samples < 4000) return;
  try {
    const r = await (await api("POST", "/api/transcribe", undefined, { data: pcm.buffer, headers: { "Content-Type": "application/octet-stream" } })).json();
    if (r.text) send(r.text);
  } catch (e) { notice(e.message); }
}

async function attachPhoto(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, 1344 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale); canvas.height = Math.round(bitmap.height * scale);
  const g = canvas.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, canvas.width, canvas.height); g.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
  const r = await (await api("POST", "/api/attachments", undefined, { data: blob, headers: { "Content-Type": "application/octet-stream", "X-Alt-Name": encodeURIComponent("foto.jpg") } })).json();
  state.pending.push(r.id); notice("Foto anexada. Escreva ou fale o que quer saber.");
}

async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
  const registration = await navigator.serviceWorker.ready;
  if (Notification.permission !== "granted" && (await Notification.requestPermission()) !== "granted") return;
  const { key } = await (await api("GET", "/api/push/key")).json();
  const padded = (key + "===".slice((key.length + 3) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  const bytes = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
  const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: bytes });
  await api("POST", "/api/push/subscribe", subscription.toJSON());
}

async function start() {
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  const fragment = new URLSearchParams(location.hash.slice(1));
  const code = fragment.get("pair");
  if (code) {
    history.replaceState(null, "", "/");
    try { await api("POST", "/pair", { code, name: "iPhone" }); } catch (e) { showPair(e.message); return; }
  }
  try {
    const me = await (await api("GET", "/api/me")).json();
    $("status").textContent = (me.user_name ? me.user_name + " · " : "") + "PC conectado";
    showChat(); await loadHistory();
  } catch (e) { return; }
}

$("pairButton").onclick = async () => {
  try { await api("POST", "/pair", { code: $("code").value, name: "iPhone" }); start(); } catch (e) { $("pairMessage").textContent = e.message; }
};
$("send").onclick = () => { const t = $("input").value; $("input").value = ""; send(t); };
$("input").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("send").click(); } });
$("mic").addEventListener("pointerdown", (e) => { e.preventDefault(); startMic().catch((err) => notice("Microfone: " + err.message)); });
["pointerup", "pointerleave", "pointercancel"].forEach((name) => $("mic").addEventListener(name, () => stopMic()));
$("photo").onclick = () => $("file").click();
$("file").onchange = () => { const f = $("file").files[0]; if (f) attachPhoto(f).catch((e) => notice(e.message)); $("file").value = ""; };
$("new").onclick = () => { state.cid = ""; localStorage.removeItem("alt-cid"); loadHistory(); };
$("speak").textContent = state.speak ? "🔊" : "🔈";
$("speak").onclick = () => {
  state.speak = !state.speak; localStorage.setItem("alt-speak", state.speak ? "1" : "0");
  $("speak").textContent = state.speak ? "🔊" : "🔈";
  if (state.speak) enablePush().catch(() => {});
};
start();
