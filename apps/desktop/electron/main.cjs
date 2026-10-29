const { app, BrowserWindow, ipcMain, dialog, globalShortcut, Tray, Menu, nativeImage, shell } = require('electron');
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
let win, backend, tray, base, quitting = false;
const token = randomBytes(32).toString('hex');
const root = path.resolve(__dirname,'../../..');
const dev = process.env.ALT_DEV === '1' && !app.isPackaged;
const ui = dev ? 'http://127.0.0.1:5173/' : pathToFileURL(path.join(__dirname,'../dist/index.html')).href;
const operations = new Map();
const allowed = [
  ['GET',/^\/(health|models|settings|system|conversations)$/],
  ['POST',/^\/(conversations|actions\/stop|actions\/resume)$/],
  ['GET',/^\/conversations\/[a-f0-9-]+\/messages$/],
  ['DELETE',/^\/conversations\/[a-f0-9-]+$/],
  ['POST',/^\/chat\/cancel\/[a-f0-9-]+$/],
  ['PUT',/^\/settings$/]
];
function validate(event) {
  if (!win || event.sender !== win.webContents || event.senderFrame !== win.webContents.mainFrame || event.senderFrame.url !== ui) throw new Error('Origem IPC inválida');
}
function payloadSize(body) { if (JSON.stringify(body ?? {}).length > 90000) throw new Error('Solicitação muito grande'); }
async function request(method, route, body, signal) {
  const response = await fetch(base+route,{method,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal});
  if (!response.ok) {
    let message = 'Falha na comunicação local';
    try { const data = await response.json(); message = typeof data.detail==='string'?data.detail:message; } catch {}
    throw new Error(message);
  }
  return response;
}
function startBackend() {
  return new Promise((resolve,reject) => {
    const executable = app.isPackaged ? path.join(process.resourcesPath,'backend','alt-backend.exe') : path.join(root,'.venv','Scripts','python.exe');
    const args = app.isPackaged ? [] : ['-m','backend.run'];
    const dataDir = path.join(app.getPath('userData'),'data');
    fs.mkdirSync(dataDir,{recursive:true});
    backend = spawn(executable,args,{cwd:app.isPackaged?process.resourcesPath:root,windowsHide:true,env:{...process.env,ALT_SESSION_TOKEN:token,ALT_DATA_DIR:dataDir,PYTHONIOENCODING:'utf-8'}});
    let output = ''; let settled = false;
    const timeout = setTimeout(()=>{if(!settled) { settled=true; reject(new Error('O backend não iniciou em 30 segundos')); }},30000);
    backend.stdout.on('data',data=>{
      output+=data.toString();
      const match = output.match(/ALT_READY:(\{[^\r\n]+\})/);
      if (match && !settled) { settled=true; clearTimeout(timeout); base='http://127.0.0.1:'+JSON.parse(match[1]).port; resolve(); }
    });
    backend.stderr.on('data',data=>fs.appendFileSync(path.join(app.getPath('userData'),'backend.log'),data));
    backend.on('error',error=>{clearTimeout(timeout);if(!settled){settled=true;reject(error);}});
    backend.on('exit',()=>{clearTimeout(timeout);if(!settled){settled=true;reject(new Error('O backend encerrou antes de iniciar'));}else if(!quitting){dialog.showErrorBox('ALT-AI','O backend local foi encerrado. Reinicie o aplicativo.');app.quit();}});
  });
}
function createWindow() {
  const boundsFile = path.join(app.getPath('userData'),'window.json');
  let saved={}; try {saved=JSON.parse(fs.readFileSync(boundsFile,'utf8'));} catch {}
  const { screen } = require('electron');
  if (saved.x!==undefined && !screen.getAllDisplays().some(d=>saved.x<d.workArea.x+d.workArea.width && saved.x+saved.width>d.workArea.x && saved.y<d.workArea.y+d.workArea.height && saved.y+saved.height>d.workArea.y)) saved={};
  win = new BrowserWindow({...saved,width:saved.width||1130,height:saved.height||800,minWidth:750,minHeight:560,frame:false,transparent:true,backgroundColor:'#00000000',show:false,title:'ALT-AI',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,webSecurity:true,webviewTag:false}});
  win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  win.webContents.on('will-navigate',(event,url)=>{if(url!==ui)event.preventDefault();});
  win.webContents.session.setPermissionRequestHandler((contents,permission,callback)=>callback(false));
  win.webContents.session.setPermissionCheckHandler(()=>false);
  win.on('close',event=>{if(!quitting){event.preventDefault();win.hide();}});
  let saveTimer;
  const save=()=>{clearTimeout(saveTimer);saveTimer=setTimeout(()=>{if(!win.isDestroyed())fs.writeFileSync(boundsFile,JSON.stringify(win.getNormalBounds()));},500);};
  win.on('resize',save);win.on('move',save);
  win.once('ready-to-show',()=>win.show());
  win.loadURL(ui);
  const icon=nativeImage.createFromDataURL('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAIElEQVR42mP8z8Dwn4ECwESJ5lEDRg0YNWDUgFEDBg0AAJiJAx1kZ2YfAAAAAElFTkSuQmCC');
  tray=new Tray(icon);tray.setToolTip('ALT-AI');
  tray.setContextMenu(Menu.buildFromTemplate([{label:'Abrir ALT-AI',click:()=>win.show()},{label:'Sair',click:()=>{quitting=true;app.quit();}}]));
  tray.on('double-click',()=>win.show());
  globalShortcut.register('CommandOrControl+Shift+Space',()=>win.isVisible()?win.hide():win.show());
}
ipcMain.handle('api:request',async(event,method,route,body)=>{
  validate(event);payloadSize(body);
  if(!allowed.some(([m,re])=>method===m&&re.test(route)))throw new Error('Operação não permitida');
  return (await request(method,route,body)).json();
});
ipcMain.handle('api:stream',async(event,id,kind,body)=>{
  validate(event);payloadSize(body);
  if(!/^[a-zA-Z0-9-]{1,80}$/.test(id)||operations.has(id)||!['chat','pull'].includes(kind)||operations.size>=4)throw new Error('Operação inválida');
  const controller=new AbortController();operations.set(id,controller);
  try {
    const response=await request('POST',kind==='chat'?'/chat':'/setup/pull',body,controller.signal);
    const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';
    while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines)if(line)event.sender.send('api:event',id,JSON.parse(line));}
    if(buffer.trim())event.sender.send('api:event',id,JSON.parse(buffer));
  } finally {operations.delete(id);}
});
ipcMain.handle('window:action',(event,action)=>{
  validate(event);
  if(action==='minimize')win.minimize();
  else if(action==='hide')win.hide();
  else if(action==='maximize')win.isMaximized()?win.unmaximize():win.maximize();
  else if(action==='pin'){win.setAlwaysOnTop(!win.isAlwaysOnTop());return win.isAlwaysOnTop();}
  else if(action==='quit'){quitting=true;app.quit();}
});
ipcMain.handle('setup:ollama',async event=>{
  validate(event);
  const result=await dialog.showMessageBox(win,{type:'question',buttons:['Cancelar','Instalar Ollama'],defaultId:0,cancelId:0,title:'Instalar dependência local',message:'Instalar o Ollama oficial neste usuário?',detail:'Será usado o winget para baixar e executar o instalador oficial. O download pode ocupar vários GB. Nenhum modelo será baixado nesta etapa.'});
  if(result.response!==1)return {ok:false,message:'Instalação cancelada'};
  return new Promise(resolve=>{
    const child=spawn('winget.exe',['install','--exact','--id','Ollama.Ollama','--scope','user','--silent','--accept-package-agreements','--accept-source-agreements','--disable-interactivity'],{windowsHide:true});
    child.stdout.resume();child.stderr.resume();
    child.on('error',()=>resolve({ok:false,message:'Winget indisponível. Instale pelo site oficial: ollama.com/download/windows'}));
    child.on('exit',code=>resolve({ok:code===0,message:code===0?'Ollama instalado. Abra o Ollama e atualize a conexão.':'Não foi possível concluir. Verifique o Ollama ou instale pelo site oficial.'}));
  });
});
ipcMain.handle('setup:website',event=>{validate(event);return shell.openExternal('https://ollama.com/download/windows');});
if(!app.requestSingleInstanceLock())app.quit();
else {
  app.on('second-instance',()=>{if(win){win.show();win.focus();}});
  app.whenReady().then(async()=>{try{await startBackend();createWindow();}catch(error){dialog.showErrorBox('ALT-AI — erro de inicialização',error.message);app.quit();}});
  app.on('before-quit',()=>{quitting=true;for(const controller of operations.values())controller.abort();globalShortcut.unregisterAll();if(backend)backend.kill();});
  app.on('window-all-closed',()=>{if(quitting)app.quit();});
}
