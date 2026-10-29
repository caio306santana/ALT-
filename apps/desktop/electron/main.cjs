const {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  globalShortcut,
  Tray,
  Menu,
  nativeImage,
  shell,
} = require("electron");
const { spawn } = require("node:child_process");
const { randomBytes } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
let win,
  backend,
  tray,
  base,
  quitting = false;
const token = randomBytes(32).toString("hex");
const root = path.resolve(__dirname, "../../..");
const dev = process.env.ALT_DEV === "1" && !app.isPackaged;
const ui = dev
  ? "http://127.0.0.1:5173/"
  : pathToFileURL(path.join(__dirname, "../dist/index.html")).href;
const operations = new Map();
const { ResearchBrowser } = require("./browser.cjs");
const researchBrowser = new ResearchBrowser(require("electron"));
let desktopTimer,
  desktopBusy = false;
async function pollDesktop() {
  if (desktopBusy || quitting) return;
  desktopBusy = true;
  try {
    const { job } = await (await request("GET", "/desktop/jobs")).json();
    if (!job) return;
    const { active } = await (
      await request("GET", "/desktop/jobs/" + job.id)
    ).json();
    if (!active) return;
    let result, error;
    try {
      result = await researchBrowser.act(job.payload);
    } catch (e) {
      error = String(e.message || e).slice(0, 500);
    }
    await request("POST", "/desktop/jobs/" + job.id, {
      result: result || null,
      error: error || null,
    });
  } catch {
  } finally {
    desktopBusy = false;
  }
}
let verifiedUpdate = null;
let activeShortcut = "";
const allowed = [
  ["GET", /^\/(health|models|settings|system|conversations)$/],
  ["POST", /^\/(conversations|actions\/stop|actions\/resume)$/],
  ["GET", /^\/conversations\/[a-f0-9-]+\/messages$/],
  ["GET", /^\/conversations\/[a-f0-9-]+\/actions$/],
  ["DELETE", /^\/conversations\/[a-f0-9-]+$/],
  ["POST", /^\/chat\/cancel\/[a-f0-9-]+$/],
  ["PUT", /^\/settings$/],
  [
    "GET",
    /^\/(memories|memories\/export|themes|permissions|tools\/history|audit|providers)$/,
  ],
  [
    "POST",
    /^\/(memories|themes|permissions\/revoke|tools\/propose|chat\/(preview|estimate))$/,
  ],
  ["PUT", /^\/(permissions|providers\/anthropic)$/],
  ["PUT", /^\/memories\/[a-f0-9-]+$/],
  ["DELETE", /^\/(memories|scopes)\/[a-f0-9-]+$/],
  ["POST", /^\/tools\/(approve|reject|renew)\/[a-f0-9-]+$/],
  ["GET", /^\/(policy|programs|evaluations)$/],
  ["GET", /^\/memories\/search\?q=[^#]{0,1600}$/],
  ["POST", /^\/(evaluations|evaluations\/cancel|continuity\/draft)$/],
  ["POST", /^\/continuity\/approve\/[a-f0-9-]+$/],
  ["PUT", /^\/evaluations\/[a-f0-9-]+\/rating$/],
  ["DELETE", /^\/programs\/[a-f0-9-]+$/],
  ["GET", /^\/(tasks|projects|knowledge\/status)$/],
  ["GET", /^\/tasks\/[a-f0-9-]+$/],
  ["GET", /^\/conversations\/[a-f0-9-]+\/project$/],
  ["GET", /^\/projects\/[a-f0-9-]+\/(documents|summaries)$/],
  [
    "POST",
    /^\/(tasks|projects|knowledge\/index|knowledge\/index\/cancel|knowledge\/search|projects\/summaries\/draft)$/,
  ],
  ["POST", /^\/tasks\/[a-f0-9-]+\/(start|pause)$/],
  ["POST", /^\/projects\/summaries\/[a-f0-9-]+\/(approve|discard)$/],
  ["PUT", /^\/(tasks\/[a-f0-9-]+\/plan|conversations\/[a-f0-9-]+\/project)$/],
  ["DELETE", /^\/(projects|documents)\/[a-f0-9-]+$/],
];
function bindShortcut(shortcut) {
  if (
    !/^(Control|Alt)(\+(Control|Alt|Shift)){0,2}\+([A-Z]|Space|F[1-9]|F1[0-2])$/.test(
      shortcut,
    )
  )
    throw new Error("Atalho inválido");
  if (shortcut === activeShortcut) return;
  if (
    !globalShortcut.register(shortcut, () =>
      win.isVisible() ? win.hide() : win.show(),
    )
  )
    throw new Error("Atalho indisponível ou utilizado por outro aplicativo.");
  if (activeShortcut) globalShortcut.unregister(activeShortcut);
  activeShortcut = shortcut;
}
function applyNativePreferences(prefs) {
  win.setAlwaysOnTop(!!prefs.always_on_top);
  win.webContents.setZoomFactor(
    Math.min(1.3, Math.max(0.8, Number(prefs.scale) || 1)),
  );
}
function validate(event) {
  if (
    !win ||
    event.sender !== win.webContents ||
    event.senderFrame !== win.webContents.mainFrame ||
    event.senderFrame.url !== ui
  )
    throw new Error("Origem IPC inválida");
}
function payloadSize(body) {
  if (JSON.stringify(body ?? {}).length > 90000)
    throw new Error("Solicitação muito grande");
}
async function request(method, route, body, signal) {
  const response = await fetch(base + route, {
    method,
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    let message = "Falha na comunicação local";
    try {
      const data = await response.json();
      message = typeof data.detail === "string" ? data.detail : message;
    } catch {}
    throw new Error(message);
  }
  return response;
}
function startBackend() {
  return new Promise((resolve, reject) => {
    const executable = app.isPackaged
      ? path.join(process.resourcesPath, "backend", "alt-backend.exe")
      : path.join(root, ".venv", "Scripts", "python.exe");
    const args = app.isPackaged ? [] : ["-m", "backend.run"];
    const dataDir = path.join(app.getPath("userData"), "data");
    fs.mkdirSync(dataDir, { recursive: true });
    backend = spawn(executable, args, {
      cwd: app.isPackaged ? process.resourcesPath : root,
      windowsHide: true,
      env: {
        ...process.env,
        ALT_SESSION_TOKEN: token,
        ALT_DATA_DIR: dataDir,
        ALT_PARENT_PID: String(process.pid),
        PYTHONIOENCODING: "utf-8",
      },
    });
    let output = "";
    let settled = false;
    const timeout = setTimeout(() => {
      if (!settled) {
        settled = true;
        reject(new Error("O backend não iniciou em 30 segundos"));
      }
    }, 30000);
    backend.stdout.on("data", (data) => {
      output += data.toString();
      const match = output.match(/ALT_READY:(\{[^\r\n]+\})/);
      if (match && !settled) {
        settled = true;
        clearTimeout(timeout);
        base = "http://127.0.0.1:" + JSON.parse(match[1]).port;
        resolve();
      }
    });
    backend.stderr.on("data", (data) =>
      fs.appendFileSync(
        path.join(app.getPath("userData"), "backend.log"),
        data,
      ),
    );
    backend.on("error", (error) => {
      clearTimeout(timeout);
      if (!settled) {
        settled = true;
        reject(error);
      }
    });
    backend.on("exit", () => {
      clearTimeout(timeout);
      if (!settled) {
        settled = true;
        reject(new Error("O backend encerrou antes de iniciar"));
      } else if (!quitting) {
        dialog.showErrorBox(
          "ALT-AI",
          "O backend local foi encerrado. Reinicie o aplicativo.",
        );
        app.quit();
      }
    });
  });
}
async function createWindow() {
  const boundsFile = path.join(app.getPath("userData"), "window.json");
  let saved = {};
  try {
    saved = JSON.parse(fs.readFileSync(boundsFile, "utf8"));
  } catch {}
  const { screen } = require("electron");
  if (
    saved.x !== undefined &&
    !screen
      .getAllDisplays()
      .some(
        (d) =>
          saved.x < d.workArea.x + d.workArea.width &&
          saved.x + saved.width > d.workArea.x &&
          saved.y < d.workArea.y + d.workArea.height &&
          saved.y + saved.height > d.workArea.y,
      )
  )
    saved = {};
  win = new BrowserWindow({
    ...saved,
    width: saved.width || 1130,
    height: saved.height || 800,
    minWidth: 750,
    minHeight: 560,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    show: false,
    title: "ALT-AI",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      webviewTag: false,
    },
  });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (event, url) => {
    if (url !== ui) event.preventDefault();
  });
  win.webContents.session.setPermissionRequestHandler(
    (contents, permission, callback) => callback(false),
  );
  win.webContents.session.setPermissionCheckHandler(() => false);
  win.on("close", (event) => {
    if (!quitting) {
      event.preventDefault();
      win.hide();
    }
  });
  let saveTimer;
  const save = () => {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      if (!win.isDestroyed())
        fs.writeFileSync(boundsFile, JSON.stringify(win.getNormalBounds()));
    }, 500);
  };
  win.on("resize", save);
  win.on("move", save);
  win.once("ready-to-show", () => win.show());
  win.loadURL(ui);
  const icon = nativeImage.createFromPath(
    path.join(root, "assets", "icon.png"),
  );
  win.setIcon(icon);
  tray = new Tray(icon);
  tray.setToolTip("ALT-AI");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Abrir ALT-AI", click: () => win.show() },
      {
        label: "Sair",
        click: () => {
          quitting = true;
          app.quit();
        },
      },
    ]),
  );
  tray.on("double-click", () => win.show());
  const prefs = await (await request("GET", "/settings")).json();
  applyNativePreferences(prefs);
  try {
    bindShortcut(prefs.shortcut || "Control+Shift+Space");
  } catch {
    dialog.showErrorBox(
      "ALT-AI — atalho",
      "Não foi possível registrar o atalho global. Use o ícone da bandeja.",
    );
  }
}
ipcMain.handle("api:request", async (event, method, route, body) => {
  validate(event);
  payloadSize(body);
  if (!allowed.some(([m, re]) => method === m && re.test(route)))
    throw new Error("Operação não permitida");
  if (method === "POST" && /^\/tools\/approve\/[a-f0-9-]+$/.test(route)) {
    const id = route.split("/").pop();
    const preview = await (
      await request("GET", "/tools/proposal/" + id)
    ).json();
    if (preview.critical) {
      const consent = await dialog.showMessageBox(win, {
        type: "warning",
        buttons: ["Cancelar", "Confirmar gravação"],
        defaultId: 0,
        cancelId: 0,
        message: "Confirmar gravação no perfil pessoal do Windows?",
        detail:
          String(preview.path) +
          "\n\n" +
          String(preview.diff || "Novo arquivo").slice(0, 2500),
      });
      if (consent.response !== 1)
        throw new Error("Gravação cancelada pelo usuário.");
      await request("POST", "/tools/confirm/" + id);
    }
  }
  if (method === "PUT" && route === "/settings") {
    const oldShortcut = activeShortcut;
    if (
      typeof body.shortcut !== "string" ||
      !Number.isFinite(body.scale) ||
      body.scale < 0.8 ||
      body.scale > 1.3
    )
      throw new Error("Preferências de janela inválidas");
    bindShortcut(body.shortcut || "Control+Shift+Space");
    try {
      const result = await (await request(method, route, body)).json();
      applyNativePreferences(result);
      return result;
    } catch (error) {
      if (oldShortcut) bindShortcut(oldShortcut);
      throw error;
    }
  }
  const response = await request(method, route, body);
  if (
    method === "POST" &&
    ["/actions/stop", "/permissions/revoke"].includes(route)
  )
    researchBrowser.stop();
  return response.json();
});
ipcMain.handle("policy:save", async (event, body) => {
  validate(event);
  payloadSize(body);
  const consent = await dialog.showMessageBox(win, {
    type: "warning",
    buttons: ["Cancelar", "Salvar minhas regras"],
    defaultId: 0,
    cancelId: 0,
    message: "Aplicar estas regras persistentes da ALT?",
    detail:
      JSON.stringify(body, null, 2) +
      "\n\nPermitir automaticamente vale nos modos 3/4 e nos escopos autorizados. Observação não executa. As regras ficam salvas até você alterar; nuvem continua com prévia por envio.",
  });
  if (consent.response !== 1) return null;
  const result = await (await request("PUT", "/policy", body)).json();
  researchBrowser.stop();
  return result;
});
ipcMain.handle("program:choose", async (event) => {
  validate(event);
  const chosen = await dialog.showOpenDialog(win, {
    title: "Registrar aplicativo local autorizado",
    properties: ["openFile"],
    filters: [{ name: "Aplicativos Windows", extensions: ["exe"] }],
  });
  if (chosen.canceled) return null;
  const selected = chosen.filePaths[0];
  const consent = await dialog.showMessageBox(win, {
    type: "warning",
    buttons: ["Cancelar", "Registrar aplicativo"],
    defaultId: 0,
    cancelId: 0,
    message: "Permitir que a ALT proponha abrir este aplicativo?",
    detail:
      selected +
      "\nNão instala nem executa agora. A abertura seguirá suas regras de autorização. Sem argumentos de linha de comando; fechamento normal somente de processos rastreados pela ALT.",
  });
  if (consent.response !== 1) return null;
  return (await request("POST", "/programs", { path: selected })).json();
});
ipcMain.handle("memory:import", async (event) => {
  validate(event);
  const chosen = await dialog.showOpenDialog(win, {
    title: "Importar memórias ALT",
    properties: ["openFile"],
    filters: [{ name: "Memórias JSON", extensions: ["json"] }],
  });
  if (chosen.canceled) return null;
  const file = chosen.filePaths[0];
  if (fs.statSync(file).size > 1900000) throw Error("Arquivo excede 1,9 MB.");
  const data = JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
  if (
    data.format !== "alt-ai-memory" ||
    data.version !== 1 ||
    !Array.isArray(data.memories)
  )
    throw Error("Use um arquivo exportado pela ALT.");
  const items = data.memories.map(({ title, content, category, enabled }) => ({
    title,
    content,
    category,
    enabled,
  }));
  const consent = await dialog.showMessageBox(win, {
    type: "question",
    buttons: ["Cancelar", "Importar"],
    defaultId: 0,
    cancelId: 0,
    message: `Importar ${items.length} memórias?`,
    detail:
      "As memórias atuais serão preservadas. Duplicatas são ignoradas. Nenhum conteúdo será enviado à nuvem.",
  });
  if (consent.response !== 1) return null;
  return (await request("POST", "/memories/import", { items })).json();
});
ipcMain.handle("document:import", async (event, projectId) => {
  validate(event);
  if (!/^[a-f0-9-]{36}$/.test(String(projectId)))
    throw new Error("Projeto inválido");
  const chosen = await dialog.showOpenDialog(win, {
    title: "Importar documento para o projeto",
    properties: ["openFile"],
    filters: [
      { name: "Documentos", extensions: ["pdf", "docx", "txt", "md"] },
    ],
  });
  if (chosen.canceled) return null;
  const file = chosen.filePaths[0];
  const consent = await dialog.showMessageBox(win, {
    type: "question",
    buttons: ["Cancelar", "Importar"],
    defaultId: 0,
    cancelId: 0,
    message: "Importar este documento para a memória do projeto?",
    detail:
      file +
      "\n\nO texto é extraído e guardado localmente, sem envio à nuvem. O original não é alterado. Possíveis credenciais bloqueiam a importação.",
  });
  if (consent.response !== 1) return null;
  return (
    await request("POST", "/projects/" + projectId + "/documents", {
      path: file,
    })
  ).json();
});
ipcMain.handle("workspace:choose", async (event) => {
  validate(event);
  const chosen = await dialog.showOpenDialog(win, {
    title: "Escolha uma pasta específica para ferramentas ALT-AI",
    properties: ["openDirectory"],
  });
  if (chosen.canceled) return null;
  const selected = chosen.filePaths[0];
  const confirmation = await dialog.showMessageBox(win, {
    type: "question",
    buttons: ["Cancelar", "Autorizar esta pasta"],
    defaultId: 0,
    cancelId: 0,
    message: "Permitir ferramentas de leitura e edição de texto nesta pasta?",
    detail:
      selected +
      "\nCada ação ainda exigirá uma proposta e aprovação individual no modo assistido.",
  });
  if (confirmation.response !== 1) return null;
  return (await request("POST", "/scopes", { path: selected })).json();
});
ipcMain.handle("windows:grant", async (event, level, scopeId) => {
  validate(event);
  if (![3, 4].includes(level)) throw new Error("Modo inválido");
  const current = await (await request("GET", "/permissions")).json();
  const scope = current.scopes.find((s) => s.id === scopeId);
  if (level === 3 && (!scope || scope.id === "windows-profile"))
    throw new Error(
      "Escolha uma pasta específica nos controles manuais primeiro.",
    );
  const detail =
    level === 4
      ? "ACESSO TOTAL, sem prazo, até você alterar ou revogar, inclusive ao reabrir a ALT. A ALT executará SEM PEDIR APROVAÇÃO tudo que não estiver bloqueado em Controle e regras: pesquisar e ler sites, baixar arquivos, ler, criar e sobrescrever arquivos em qualquer pasta local do seu usuário, abrir e fechar aplicativos, usar o navegador ALT e executar tarefas com várias etapas. Versões anteriores de arquivos sobrescritos ficam guardadas em file-history. Continuam sempre excluídos: arquivos de credenciais/AppData, shell arbitrário, privilégios de administrador e executar arquivos baixados. Conteúdo de sites pode tentar enganar o modelo; STOP e Revogar encerram tudo na hora."
      : `Sem prazo; permanece autorizado até você alterar ou revogar, inclusive ao reabrir a ALT: cálculo e leitura automática apenas em ${scope.path}. Gravações e consultas externas ainda pedem aprovação.`;
  const confirmation = await dialog.showMessageBox(win, {
    type: "warning",
    buttons: [
      "Cancelar",
      level === 4 ? "Autorizar acesso total" : "Autorizar leitura limitada",
    ],
    defaultId: 0,
    cancelId: 0,
    message:
      level === 4
        ? "Dar acesso total à ALT, sem aprovação a cada ação?"
        : "Autorizar sessão de leitura limitada?",
    detail,
  });
  if (confirmation.response !== 1) return current;
  return (
    await request("POST", "/permissions/grant", {
      level,
      scope_ids: scope && scope.id !== "windows-profile" ? [scope.id] : [],
    })
  ).json();
});
ipcMain.handle("memory:export", async (event) => {
  validate(event);
  const data = await (await request("GET", "/memories/export")).json();
  const chosen = await dialog.showSaveDialog(win, {
    title: "Exportar memórias autorizadas",
    defaultPath: "ALT-AI-memorias.json",
    filters: [{ name: "JSON", extensions: ["json"] }],
  });
  if (chosen.canceled) return { saved: false };
  fs.writeFileSync(chosen.filePath, JSON.stringify(data, null, 2), "utf8");
  return { saved: true };
});
ipcMain.handle("credentials:anthropic", async (event, key) => {
  validate(event);
  if (typeof key !== "string" || key.length > 500)
    throw new Error("Chave inválida");
  if (!key) {
    await request("DELETE", "/credentials/anthropic");
    return { configured: false };
  }
  const confirmation = await dialog.showMessageBox(win, {
    type: "question",
    buttons: ["Cancelar", "Salvar no cofre"],
    defaultId: 0,
    cancelId: 0,
    message: "Salvar chave da API Anthropic no cofre deste usuário?",
    detail:
      "A chave será protegida pelo Windows DPAPI. A API tem cobrança separada da assinatura Claude. Nenhum pedido será enviado sem revisão do contexto e confirmação.",
  });
  if (confirmation.response !== 1) return { configured: false };
  return (await request("PUT", "/credentials/anthropic", { key })).json();
});
ipcMain.handle("window:layout", (event, layout) => {
  validate(event);
  const { screen } = require("electron");
  const area = screen.getDisplayMatching(win.getBounds()).workArea;
  const width = Math.min(
    area.width,
    Math.max(750, Number(layout.width) || 1130),
  );
  const height = Math.min(
    area.height,
    Math.max(560, Number(layout.height) || 800),
  );
  const position = ["left", "center", "right"].includes(layout.position)
    ? layout.position
    : "center";
  win.setBounds({
    width: Math.round(width),
    height: Math.round(height),
    x: Math.round(
      area.x +
        (position === "left"
          ? 0
          : position === "right"
            ? area.width - width
            : (area.width - width) / 2),
    ),
    y: Math.round(area.y + (area.height - height) / 2),
  });
  return win.getBounds();
});
ipcMain.handle("game:mode", async (event, enabled) => {
  validate(event);
  if (typeof enabled !== "boolean") throw new Error("Modo inválido");
  if (enabled) {
    const consent = await dialog.showMessageBox(win, {
      type: "question",
      buttons: ["Cancelar", "Ativar GAME MODE"],
      defaultId: 0,
      cancelId: 0,
      message: "Suspender tarefas e descarregar o modelo selecionado?",
      detail:
        "Isso pode afetar outros aplicativos que estejam usando o mesmo modelo Ollama. A janela será ocultada; use seu atalho ou a bandeja para restaurar.",
    });
    if (consent.response !== 1) return { enabled: false, message: "Cancelado" };
  }
  const result = await (
    await request("POST", enabled ? "/game/enable" : "/game/disable")
  ).json();
  if (enabled) {
    researchBrowser.stop();
    win.hide();
  }
  return result;
});
ipcMain.handle("help:open", (event) => {
  validate(event);
  return shell.openExternal("https://github.com/caio306santana/ALT-/releases");
});
let releaseInfo = null;
async function checkForRelease() {
  const { checkRelease } = require("./update-feed.cjs");
  const result = await checkRelease(app.getVersion());
  releaseInfo = result.available ? result : null;
  return result;
}
ipcMain.handle("updates:check", async (event) => {
  validate(event);
  return checkForRelease();
});
ipcMain.handle("updates:download", async (event) => {
  validate(event);
  if (!releaseInfo) throw new Error("Verifique se há uma nova versão primeiro.");
  verifiedUpdate = null;
  const { stageRelease } = require("./update-feed.cjs");
  const { verifyUpdate } = require("./update-security.cjs");
  const folder = path.join(app.getPath("userData"), "updates");
  let last = 0;
  const staged = await stageRelease(releaseInfo, folder, (received, total) => {
    if (received - last < 1024 * 1024 && received !== total) return;
    last = received;
    win.webContents.send("updates:progress", { received, total });
  });
  const args = {
    installerPath: staged.installerPath,
    manifest: staged.manifest,
    publicKey: fs.readFileSync(
      path.join(root, "assets", "update-public-key.pem"),
      "utf8",
    ),
    currentVersion: app.getVersion(),
  };
  const result = await verifyUpdate(args);
  verifiedUpdate = { args, expires: Date.now() + 1800000 };
  return result;
});
ipcMain.handle("updates:verify", async (event) => {
  validate(event);
  verifiedUpdate = null;
  const manifestChoice = await dialog.showOpenDialog(win, {
    title: "Escolha o manifesto de atualização ALT-AI",
    filters: [{ name: "Manifesto assinado", extensions: ["json"] }],
    properties: ["openFile"],
  });
  if (manifestChoice.canceled) return null;
  const manifestPath = manifestChoice.filePaths[0];
  if (fs.statSync(manifestPath).size > 32000)
    throw new Error("Manifesto muito grande");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const installerChoice = await dialog.showOpenDialog(win, {
    title: "Escolha o instalador correspondente ao manifesto",
    defaultPath: path.dirname(manifestPath),
    filters: [{ name: "Instalador Windows", extensions: ["exe"] }],
    properties: ["openFile"],
  });
  if (installerChoice.canceled) return null;
  const publicKey = fs.readFileSync(
    path.join(root, "assets", "update-public-key.pem"),
    "utf8",
  );
  const args = {
    installerPath: installerChoice.filePaths[0],
    manifest,
    publicKey,
    currentVersion: app.getVersion(),
  };
  const { verifyUpdate } = require("./update-security.cjs");
  const result = await verifyUpdate(args);
  verifiedUpdate = { args, expires: Date.now() + 300000 };
  return result;
});
ipcMain.handle("updates:apply", async (event) => {
  validate(event);
  if (!verifiedUpdate || Date.now() > verifiedUpdate.expires)
    throw new Error("Verifique novamente o manifesto e o instalador.");
  const pending = verifiedUpdate;
  verifiedUpdate = null;
  const { verifyUpdate } = require("./update-security.cjs");
  const checked = await verifyUpdate(pending.args);
  const consent = await dialog.showMessageBox(win, {
    type: "question",
    buttons: ["Cancelar", "Instalar atualização"],
    defaultId: 0,
    cancelId: 0,
    message: `Instalar ALT-AI ${checked.version}?`,
    detail:
      "A assinatura Ed25519 do projeto e o hash do arquivo foram conferidos. Isso não substitui um certificado Windows Authenticode. O aplicativo será encerrado para executar o instalador.",
  });
  if (consent.response !== 1) return { started: false };
  await verifyUpdate(pending.args);
  await new Promise((resolve, reject) => {
    const child = spawn(pending.args.installerPath, ["/S"], {
      detached: true,
      stdio: "ignore",
      windowsHide: true,
    });
    child.once("error", reject);
    child.once("spawn", () => {
      child.unref();
      resolve();
    });
  });
  quitting = true;
  app.quit();
  return { started: true };
});
ipcMain.handle("api:stream", async (event, id, kind, body) => {
  validate(event);
  payloadSize(body);
  if (
    !/^[a-zA-Z0-9-]{1,80}$/.test(id) ||
    operations.has(id) ||
    !["chat", "pull"].includes(kind) ||
    operations.size >= 4
  )
    throw new Error("Operação inválida");
  const controller = new AbortController();
  operations.set(id, controller);
  try {
    const response = await request(
      "POST",
      kind === "chat" ? "/chat" : "/setup/pull",
      body,
      controller.signal,
    );
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines)
        if (line) event.sender.send("api:event", id, JSON.parse(line));
    }
    if (buffer.trim()) event.sender.send("api:event", id, JSON.parse(buffer));
  } finally {
    operations.delete(id);
  }
});
ipcMain.handle("window:action", (event, action) => {
  validate(event);
  if (action === "minimize") win.minimize();
  else if (action === "hide") win.hide();
  else if (action === "maximize")
    win.isMaximized() ? win.unmaximize() : win.maximize();
  else if (action === "pin") {
    win.setAlwaysOnTop(!win.isAlwaysOnTop());
    return win.isAlwaysOnTop();
  } else if (action === "quit") {
    quitting = true;
    app.quit();
  }
});
ipcMain.handle("setup:ollama", async (event) => {
  validate(event);
  const result = await dialog.showMessageBox(win, {
    type: "question",
    buttons: ["Cancelar", "Instalar Ollama"],
    defaultId: 0,
    cancelId: 0,
    title: "Instalar dependência local",
    message: "Instalar o Ollama oficial neste usuário?",
    detail:
      "Será usado o winget para baixar e executar o instalador oficial. O download pode ocupar vários GB. Nenhum modelo será baixado nesta etapa.",
  });
  if (result.response !== 1)
    return { ok: false, message: "Instalação cancelada" };
  return new Promise((resolve) => {
    const child = spawn(
      "winget.exe",
      [
        "install",
        "--exact",
        "--id",
        "Ollama.Ollama",
        "--scope",
        "user",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--disable-interactivity",
      ],
      { windowsHide: true },
    );
    child.stdout.resume();
    child.stderr.resume();
    child.on("error", () =>
      resolve({
        ok: false,
        message:
          "Winget indisponível. Instale pelo site oficial: ollama.com/download/windows",
      }),
    );
    child.on("exit", (code) =>
      resolve({
        ok: code === 0,
        message:
          code === 0
            ? "Ollama instalado. Abra o Ollama e atualize a conexão."
            : "Não foi possível concluir. Verifique o Ollama ou instale pelo site oficial.",
      }),
    );
  });
});
ipcMain.handle("setup:website", (event) => {
  validate(event);
  return shell.openExternal("https://ollama.com/download/windows");
});
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on("second-instance", () => {
    if (win) {
      win.show();
      win.focus();
    }
  });
  app.whenReady().then(async () => {
    try {
      await startBackend();
      await createWindow();
      desktopTimer = setInterval(pollDesktop, 500);
      desktopTimer.unref();
      // Quietly look for a newer release; the renderer shows notes and asks.
      const announce = () =>
        checkForRelease()
          .then((r) => r.available && win.webContents.send("updates:available", r))
          .catch(() => {});
      setTimeout(announce, 15000).unref();
      setInterval(announce, 6 * 3600 * 1000).unref();
    } catch (error) {
      dialog.showErrorBox("ALT-AI — erro de inicialização", error.message);
      app.quit();
    }
  });
  app.on("before-quit", () => {
    quitting = true;
    clearInterval(desktopTimer);
    researchBrowser.close();
    for (const controller of operations.values()) controller.abort();
    globalShortcut.unregisterAll();
    if (backend) backend.kill();
  });
  app.on("window-all-closed", () => {
    if (quitting) app.quit();
  });
}
