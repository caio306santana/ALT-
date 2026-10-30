const {app,BrowserWindow}=require('electron');
const path=require('node:path');
const fs=require('node:fs');
const assert=require('node:assert/strict');
// Synthetic hidden renderer: do not compete with the owner's local inference
// for the GPU or depend on this notebook's hardware compositor state.
app.disableHardwareAcceleration();
const root=path.resolve(__dirname,'..');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
app.whenReady().then(async()=>{
 const win=new BrowserWindow({show:false,width:1080,height:860,webPreferences:{offscreen:true,backgroundThrottling:false,sandbox:true,contextIsolation:true,nodeIntegration:false,preload:path.join(__dirname,'smoke_chat_ui_preload.cjs')}});
 const js=async code=>{try{return await win.webContents.executeJavaScript(code);}catch(error){throw new Error('Renderer evaluation failed: '+code,{cause:error});}};
 win.webContents.on('console-message',(_event,...args)=>{if(args.some(value=>String(value).includes('TypeError')))console.error('Renderer:',...args);});
 async function until(code){for(let i=0;i<100;i++){if(await js(code))return;await delay(50);}throw new Error('UI condition timed out: '+code);}
 async function draft(value){await js(`(()=>{const el=document.querySelector('textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event('input',{bubbles:true}));})()`);}
 try {
  await win.loadFile(path.join(root,'apps/desktop/dist/index.html'));
  await until(`!!document.querySelector('.approval-trigger') && document.querySelector('.approval-trigger').textContent.includes('Acesso total')`);
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
  assert.ok(await js(`document.querySelector('.context-indicator').textContent.includes('qwen3.5:4b (Automático)')`));
  await js(`document.querySelector('.context-parts summary').click()`);
  assert.ok(await js(`document.querySelector('.context-parts').open && document.querySelector('.context-parts').textContent.includes('Personalidade e memórias escolhidas')`));
  await js(`document.querySelector('button[aria-label="Enviar mensagem"]').click()`);
  await until(`document.body.textContent.includes('Falha sintética de transporte')`);
  assert.equal(await js(`document.querySelector('textarea').value`),value);
  assert.equal(await js(`window.chatFixture.calls()`),1);
  await js(`window.chatFixture.setFailure('context')`);
  await draft(value+' Maior.');
  await until(`!!document.querySelector('.context-indicator.over-limit')`);
  assert.equal(await js(`document.querySelector('button[aria-label="Enviar mensagem"]').disabled`),true);
  assert.equal(await js(`window.chatFixture.calls()`),1);
  // A permission change must refresh a previously blocked estimate without editing the draft.
  await js(`window.chatFixture.setFailure('stream');document.querySelector('.approval-trigger').click()`);
  await until(`!!document.querySelector('.approval-popover')`);
  await js(`Array.from(document.querySelectorAll('.approval-popover button')).find(b=>b.textContent.includes('Somente conversar')).click()`);
  await until(`!!document.querySelector('.context-indicator') && !document.querySelector('.context-indicator.over-limit')`);
  assert.equal(await js(`document.querySelector('button[aria-label="Enviar mensagem"]').disabled`),false);
  assert.equal(await js(`document.querySelector('textarea').value`),value+' Maior.');
  const routed=await js(`window.chatFixture.routes()`);
  await js(`window.chatFixture.setFailure('direct')`);
  await draft('abre o bloco de notas');
  await until(`!!document.querySelector('.context-indicator') && document.querySelector('.context-indicator').textContent.includes('Ação local direta')`);
  assert.equal(await js(`!!document.querySelector('.context-parts')`),false);
  await js(`document.querySelector('button[aria-label="Enviar mensagem"]').click()`);
  await until(`window.chatFixture.calls()===2`);
  assert.equal(await js(`window.chatFixture.routes()`),routed,'Direct launch must not route to an LLM');
  await js(`document.querySelector('.side-nav button[aria-label="Inteligências"]').click()`);
  await until(`document.body.textContent.includes('Hermes 3 · NousResearch · 3B') && document.body.textContent.includes('Hermes 3 · NousResearch · 8B')`);
  assert.ok(await js(`document.querySelector('.model-card:has(.supported)').textContent.includes('262.144') && document.querySelector('.model-card:has(.supported)').textContent.includes('4.096')`));
  assert.ok(await js(`document.body.textContent.includes('cerca de 2 GB') && document.body.textContent.includes('cerca de 4,7 GB')`));
  await js(`Array.from(document.querySelectorAll('.download-row')).find(row=>row.textContent.includes('Hermes 3')).scrollIntoView({block:'center'})`);
  win.webContents.invalidate();await delay(300);
  fs.writeFileSync(path.join(root,'.local/ui-hermes.png'),(await win.webContents.capturePage()).toPNG());
  await js(`document.querySelector('.side-nav button[aria-label="Chat"]').click()`);
  // Visual pass of the 0.4 layout: labeled sidebar, main panels, collapsed and light.
  // Hidden windows only repaint on request; invalidate so each capture shows the current view.
  const shot=async name=>{win.webContents.invalidate();await delay(300);fs.writeFileSync(path.join(root,'.local',name),(await win.webContents.capturePage()).toPNG());};
  assert.ok(await js(`document.querySelectorAll('.sidebar .side-item.recent').length===1`),'Recent conversations should be listed in the sidebar');
  await shot('ui-chat.png');
  for(const [label,file,ready] of [['Tarefas','ui-tasks.png','.task-run'],['Memória','ui-memory.png','.projects-panel'],['Ferramentas','ui-tools.png','.permission-card']]){
    await js(`document.querySelector('.side-nav button[aria-label="${label}"]').click()`);
    await until(`!!document.querySelector('${ready}')`);await delay(150);await shot(file);
  }
  await js(`document.querySelector('.side-nav button[aria-label="Chat"]').click()`);
  await js(`document.querySelector('.side-toggle').click()`);
  await until(`!!document.querySelector('.sidebar.collapsed')`);await delay(250);await shot('ui-collapsed.png');
  await js(`document.querySelector('.side-toggle').click()`);
  await js(`document.querySelector('.app').classList.add('light')`);await delay(150);await shot('ui-light.png');
  await js(`window.chatFixture.withoutModel();document.querySelector('.side-nav button[aria-label="Inteligências"]').click()`);
  await until(`!!document.querySelector('.subheading button')`);
  await js(`document.querySelector('.subheading button').click()`);
  await until(`document.querySelectorAll('.model-card').length===0`);
  await js(`document.querySelector('.side-nav button[aria-label="Chat"]').click()`);
  await draft('abra o bloco de notas');
  await until(`!!document.querySelector('.context-indicator') && document.querySelector('.context-indicator').textContent.includes('Ação local direta')`);
  assert.equal(await js(`document.querySelector('button[aria-label="Enviar mensagem"]').disabled`),false);
  await js(`document.querySelector('button[aria-label="Enviar mensagem"]').click()`);
  await until(`window.chatFixture.calls()===3`);
  console.log(JSON.stringify({chat_ui:'ok',sidebar_views:true,permission_label_matches_mode:true,approval_mode_change:true,draft_restored_on_transport_rejection:true,oversize_shown_before_send:true,settings_closed_on_start:true,direct_launch_skips_model_routing:true,hermes_3b_8b_catalog:true,screenshots:'synthetic hidden renderer only'}));
 }finally{win.destroy();app.quit();}
}).catch(error=>{console.error(error);app.exit(1);});
