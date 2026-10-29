const http = require("node:http");
const net = require("node:net");
const dns = require("node:dns/promises");
const { randomUUID } = require("node:crypto");

const denied = new net.BlockList();
for (const [ip, bits] of [
  ["0.0.0.0", 8],
  ["10.0.0.0", 8],
  ["100.64.0.0", 10],
  ["127.0.0.0", 8],
  ["169.254.0.0", 16],
  ["172.16.0.0", 12],
  ["192.0.0.0", 24],
  ["192.0.2.0", 24],
  ["192.88.99.0", 24],
  ["192.168.0.0", 16],
  ["198.18.0.0", 15],
  ["198.51.100.0", 24],
  ["203.0.113.0", 24],
  ["224.0.0.0", 3],
])
  denied.addSubnet(ip, bits, "ipv4");
for (const [ip, bits] of [
  ["2001::", 23],
  ["2001:db8::", 32],
  ["2002::", 16],
])
  denied.addSubnet(ip, bits, "ipv6");
function publicIP(ip) {
  const family = net.isIP(ip);
  if (family === 4) return !denied.check(ip, "ipv4");
  if (family !== 6 || !/^[23][0-9a-f]{3}:/i.test(ip)) return false;
  return !denied.check(ip, "ipv6");
}
function publicURL(value) {
  const url = new URL(value);
  if (
    !["https:", "wss:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    (url.port && url.port !== "443") ||
    value.length > 2000
  )
    throw Error("Use HTTPS público, sem credenciais ou portas alternativas.");
  const host = url.hostname.replace(/^\[|\]$/g, "");
  if (
    host === "localhost" ||
    /\.(localhost|local|internal|home\.arpa)$/i.test(host) ||
    (net.isIP(host) && !publicIP(host))
  )
    throw Error("Endereço local/privado não permitido neste navegador.");
  return url;
}

// CONNECT proxy: resolve, validate every answer, then connect to the chosen IP.
// Chromium still validates the origin's TLS certificate inside this tunnel.
async function startPublicProxy(lookup = dns.lookup) {
  const sockets = new Set();
  let paused = false;
  const server = http.createServer((_, res) => {
    res.writeHead(405);
    res.end();
  });
  server.on("connect", async (req, client, head) => {
    let upstream;
    client.on("error", () => {});
    try {
      if (paused || sockets.size >= 32) throw Error("Navegação suspensa.");
      sockets.add(client);
      client.on("close", () => sockets.delete(client));
      const url = publicURL("https://" + req.url);
      const host = url.hostname.replace(/^\[|\]$/g, "");
      const answers = await lookup(host, { all: true, verbatim: true });
      if (
        !answers.length ||
        answers.some((a) => !publicIP(a.address)) ||
        paused ||
        client.destroyed
      )
        throw Error("DNS não público.");
      upstream = net.connect({ host: answers[0].address, port: 443 });
      sockets.add(upstream);
      sockets.add(client);
      const close = () => {
        upstream.destroy();
        client.destroy();
        sockets.delete(upstream);
        sockets.delete(client);
      };
      upstream.on("error", close);
      client.on("error", close);
      upstream.on("close", close);
      client.on("close", close);
      upstream.setTimeout(60000, close);
      client.setTimeout(60000, close);
      upstream.once("connect", () => {
        if (paused) return close();
        client.write("HTTP/1.1 200 Connection Established\r\n\r\n");
        if (head.length) upstream.write(head);
        client.pipe(upstream);
        upstream.pipe(client);
      });
    } catch {
      sockets.delete(client);
      client.end("HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n");
      upstream?.destroy();
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  server.unref();
  return {
    port: server.address().port,
    pause() {
      paused = true;
      for (const s of sockets) s.destroy();
    },
    resume() {
      paused = false;
    },
    close() {
      for (const s of sockets) s.destroy();
      server.close();
    },
  };
}

class ResearchBrowser {
  constructor(electron, options = {}) {
    this.electron = electron;
    this.visible = options.visible !== false;
    this.window = null;
    this.proxy = null;
    this.partition = null;
    this.lastSnapshot = null;
  }
  async ensure() {
    if (this.window && !this.window.isDestroyed()) return;
    this.proxy = await startPublicProxy();
    const { session, BrowserWindow } = this.electron;
    this.partition = session.fromPartition("alt-research-" + randomUUID(), {
      cache: false,
    });
    await this.partition.setProxy({
      proxyRules: `http=127.0.0.1:${this.proxy.port};https=127.0.0.1:${this.proxy.port}`,
      proxyBypassRules: "<-loopback>",
    });
    this.partition.setPermissionRequestHandler((_, __, callback) =>
      callback(false),
    );
    this.partition.setPermissionCheckHandler(() => false);
    this.partition.on("will-download", (event) => event.preventDefault());
    this.partition.webRequest.onBeforeRequest((details, callback) => {
      try {
        if (
          !["mainFrame", "subFrame"].includes(details.resourceType) &&
          /^(data:|blob:)/.test(details.url)
        )
          return callback({});
        publicURL(details.url);
        callback({});
      } catch {
        callback({ cancel: true });
      }
    });
    this.window = new BrowserWindow({
      show: this.visible,
      width: 1080,
      height: 780,
      title: "ALT · Navegador isolado",
      autoHideMenuBar: true,
      webPreferences: {
        session: this.partition,
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: true,
        webSecurity: true,
        webviewTag: false,
        allowRunningInsecureContent: false,
        spellcheck: false,
        enableWebSQL: false,
      },
    });
    this.window.webContents.setWebRTCIPHandlingPolicy(
      "disable_non_proxied_udp",
    );
    this.window.webContents.setWindowOpenHandler(({ url }) => {
      this.navigate(url).catch(() => {});
      return { action: "deny" };
    });
    this.window.webContents.on("will-navigate", (event, url) => {
      try {
        publicURL(url);
      } catch {
        event.preventDefault();
      }
    });
    this.window.webContents.on("did-start-navigation", () => {
      this.lastSnapshot = null;
    });
    this.window.on("closed", () => {
      this.proxy?.close();
      this.proxy = null;
      this.window = null;
      this.lastSnapshot = null;
      this.partition?.clearStorageData().catch(() => {});
    });
  }
  async navigate(url) {
    publicURL(url);
    await this.ensure();
    this.proxy.resume();
    if (this.visible) this.window.show();
    await this.window.loadURL(url);
    return this.read();
  }
  async script(code) {
    if (!this.window || this.window.isDestroyed())
      throw Error("Abra uma página no navegador da ALT primeiro.");
    publicURL(this.window.webContents.getURL());
    return this.window.webContents.executeJavaScriptInIsolatedWorld(1001, [
      { code },
    ]);
  }
  async read() {
    const id = randomUUID();
    const data = await this.script(`(()=>{
      const visible=e=>!!(e.getClientRects().length)&&getComputedStyle(e).visibility!=='hidden';
      const nodes=[...document.querySelectorAll('a[href],button,input:not([type=hidden]),textarea,select,[role=button]')].filter(visible).slice(0,60);
      globalThis.__altSnapshot={id:${JSON.stringify(id)},url:location.href,nodes:nodes.map(e=>({e,html:e.outerHTML}))};
      return {snapshot_id:${JSON.stringify(id)},url:location.href,title:document.title,text:(document.body?.innerText||'').slice(0,14000),
        elements:nodes.map((e,i)=>({id:'e'+i,tag:e.tagName.toLowerCase(),type:e.type||'',label:(e.getAttribute('aria-label')||e.innerText||e.getAttribute('placeholder')||e.name||'').slice(0,140),href:e.tagName==='A'?e.href:undefined}))};
    })()`);
    this.lastSnapshot = data;
    return data;
  }
  async act(body) {
    const { tool } = body;
    if (tool === "browser_open") return this.navigate(body.url);
    if (tool === "browser_read") return this.read();
    if (tool === "browser_back") {
      if (!this.window?.webContents.navigationHistory.canGoBack())
        throw Error("Sem página anterior.");
      this.window.webContents.navigationHistory.goBack();
      await new Promise((r) => setTimeout(r, 600));
      return this.read();
    }
    if (!["browser_click", "browser_type"].includes(tool))
      throw Error("Comando de navegador inválido.");
    if (
      !this.lastSnapshot ||
      this.lastSnapshot.snapshot_id !== body.snapshot_id ||
      !/^e\d+$/.test(body.target)
    )
      throw Error("A página mudou. Leia novamente antes de interagir.");
    const index = Number(body.target.slice(1));
    const text = JSON.stringify(body.content || "");
    const outcome = await this.script(`(()=>{try{
      const s=globalThis.__altSnapshot,item=s?.nodes[${index}];
      if(!s||s.id!==${JSON.stringify(body.snapshot_id)}||s.url!==location.href||!item?.e.isConnected||item.e.outerHTML!==item.html)throw Error('Elemento alterado; leia novamente.');
      const e=item.e;
      if(${JSON.stringify(tool)}==='browser_type'){
        if(!['INPUT','TEXTAREA'].includes(e.tagName)||e.disabled||e.readOnly||/password|senha|one-time|cc-|credit|token|secret|cvv|captcha/i.test([e.type,e.name,e.id,e.autocomplete].join(' ')))throw Error('Campo protegido ou não editável. Preencha manualmente.');
        const setter=Object.getOwnPropertyDescriptor(e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value')?.set;
        setter.call(e,${text});e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));
      }else{if(e.disabled)throw Error('Elemento desabilitado.');e.click();}
      globalThis.__altSnapshot=null;return {ok:true};
    }catch(error){return {ok:false,error:String(error.message||error).slice(0,500)};}})()`);
    if (!outcome.ok) throw Error(outcome.error);
    this.lastSnapshot = null;
    await new Promise((r) => setTimeout(r, 600));
    try {
      return await this.read();
    } catch {
      return {
        interaction_requested: true,
        notice:
          "A página está mudando. Leia novamente para verificar o resultado.",
      };
    }
  }
  stop() {
    this.window?.webContents.stop();
    this.lastSnapshot = null;
    this.proxy?.pause();
  }
  close() {
    this.window?.destroy();
    this.proxy?.close();
  }
}
module.exports = { ResearchBrowser, startPublicProxy, publicIP, publicURL };
