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
});
