const {app,BrowserWindow}=require('electron');
const path=require('node:path');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
app.whenReady().then(async()=>{
 const win=new BrowserWindow({show:false,width:1080,height:860,webPreferences:{sandbox:true,contextIsolation:true,nodeIntegration:false,preload:path.join(__dirname,'smoke_chat_ui_preload.cjs')}});
 const js=code=>win.webContents.executeJavaScript(code);
 async function until(code){for(let i=0;i<100;i++){if(await js(code))return;await delay(50);}throw new Error('UI condition timed out: '+code);}
 async function draft(value){await js(`(()=>{const el=document.querySelector('textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event('input',{bubbles:true}));})()`);}
 try {
  await win.loadFile(path.join(root,'apps/desktop/dist/index.html'));
  await until(`!!document.querySelector('.approval-trigger') && document.querySelector('.approval-trigger').textContent.includes('Acesso amplo')`);
  assert.ok(await js(`document.querySelector('.approval-trigger').getBoundingClientRect().width > 100`),'Approval label should be visible, not squeezed into an icon button');
  assert.equal(await js(`!!document.querySelector('.settings-panel')`),false);
  fs.mkdirSync(path.join(root,'.local'),{recursive:true});
  fs.writeFileSync(path.join(root,'.local/chat-ui.png'),(await win.webContents.capturePage()).toPNG());
  await js(`document.querySelector('.approval-trigger').click()`);
  await until(`!!document.querySelector('.approval-popover')`);
  fs.writeFileSync(path.join(root,'.local/chat-menu.png'),(await win.webContents.capturePage()).toPNG());
  await js(`Array.from(document.querySelectorAll('.approval-popover button')).find(b=>b.textContent.includes('Pedir aprovação')).click()`);
  await until(`document.querySelector('.approval-trigger').textContent.includes('Pedir aprovação') && !document.querySelector('.approval-popover')`);
  const value='Mensagem sintética que precisa permanecer no rascunho se o backend recusar.';
  await draft(value);
  await until(`!!document.querySelector('.context-indicator')`);
  await js(`document.querySelector('button[aria-label="Enviar mensagem"]').click()`);
  await until(`document.body.textContent.includes('Falha sintética de transporte')`);
  assert.equal(await js(`document.querySelector('textarea').value`),value);
  assert.equal(await js(`window.chatFixture.calls()`),1);
  await js(`window.chatFixture.setFailure('context')`);
  await draft(value+' Maior.');
  await until(`!!document.querySelector('.context-indicator.over-limit')`);
  assert.equal(await js(`document.querySelector('button[aria-label="Enviar mensagem"]').disabled`),true);
  assert.equal(await js(`window.chatFixture.calls()`),1);
  console.log(JSON.stringify({chat_ui:'ok',permission_label_matches_mode:true,approval_mode_change:true,draft_restored_on_transport_rejection:true,oversize_shown_before_send:true,settings_closed_on_start:true,screenshots:'synthetic hidden renderer only'}));
 }finally{win.destroy();app.quit();}
}).catch(error=>{console.error(error);app.exit(1);});
