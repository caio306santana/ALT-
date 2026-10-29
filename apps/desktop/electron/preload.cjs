const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("alt", {
  request: (method, route, body) =>
    ipcRenderer.invoke("api:request", method, route, body),
  stream: (id, kind, body, callback) => {
    const listener = (_, eventId, data) => {
      if (eventId === id) callback(data);
    };
    ipcRenderer.on("api:event", listener);
    return ipcRenderer
      .invoke("api:stream", id, kind, body)
      .finally(() => ipcRenderer.removeListener("api:event", listener));
  },
  window: (action) => ipcRenderer.invoke("window:action", action),
  installOllama: () => ipcRenderer.invoke("setup:ollama"),
  ollamaWebsite: () => ipcRenderer.invoke("setup:website"),
  chooseWorkspace: () => ipcRenderer.invoke("workspace:choose"),
  grantWindows: (level, scopeId) =>
    ipcRenderer.invoke("windows:grant", level, scopeId),
  exportMemories: () => ipcRenderer.invoke("memory:export"),
  importMemories: () => ipcRenderer.invoke('memory:import'),
  savePolicy: (body) => ipcRenderer.invoke('policy:save',body),
  chooseProgram: () => ipcRenderer.invoke('program:choose'),
  setAnthropicKey: (key) => ipcRenderer.invoke("credentials:anthropic", key),
  layout: (options) => ipcRenderer.invoke("window:layout", options),
  gameMode: (enabled) => ipcRenderer.invoke("game:mode", enabled),
  openReleases: () => ipcRenderer.invoke("help:open"),
  verifyUpdate: () => ipcRenderer.invoke("updates:verify"),
  applyUpdate: () => ipcRenderer.invoke("updates:apply"),
  checkUpdate: () => ipcRenderer.invoke("updates:check"),
  downloadUpdate: () => ipcRenderer.invoke("updates:download"),
  onUpdate: (callback) => {
    const available = (_, info) => callback("available", info);
    const progress = (_, info) => callback("progress", info);
    ipcRenderer.on("updates:available", available);
    ipcRenderer.on("updates:progress", progress);
    return () => {
      ipcRenderer.removeListener("updates:available", available);
      ipcRenderer.removeListener("updates:progress", progress);
    };
  },
  importDocument: (projectId) => ipcRenderer.invoke("document:import", projectId),
  authorizeWindow: (candidateId, title) => ipcRenderer.invoke("windows:authorize", candidateId, title),
  exportBackup: () => ipcRenderer.invoke("backup:export"),
  restoreBackup: () => ipcRenderer.invoke("backup:restore"),
});
