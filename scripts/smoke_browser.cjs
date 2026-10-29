// Integration test of ALT's browser implementation, in its own hidden Electron
// process. No control of the user's desktop, accounts or browser is performed.
const electron=require('electron');const assert=require('node:assert/strict');
const {ResearchBrowser}=require('../apps/desktop/electron/browser.cjs');
const browser=new ResearchBrowser(electron,{visible:false});
electron.app.commandLine.appendSwitch('disable-gpu');
electron.app.whenReady().then(async()=>{
  try{
    const page=await browser.navigate('https://docs.ollama.com/');
    assert.ok(page.text.length>50);assert.equal(new URL(page.url).hostname,'docs.ollama.com');
    // Synthetic DOM fixtures: no submission or external data transmission.
    await browser.script(`document.body.innerHTML='<label>Pesquisa<input id="search" type="search"></label><button id="mark">Marcar localmente</button><input id="secret" type="password">';document.getElementById('mark').onclick=()=>{document.body.dataset.clicked='yes';};true;`);
    let snapshot=await browser.read();let target=snapshot.elements.find(e=>e.type==='search');
    await browser.act({tool:'browser_type',target:target.id,snapshot_id:snapshot.snapshot_id,content:'ALT browser synthetic test'});
    assert.equal(await browser.script(`document.getElementById('search').value`),'ALT browser synthetic test');
    await assert.rejects(()=>browser.act({tool:'browser_click',target:target.id,snapshot_id:snapshot.snapshot_id}),/mudou|novamente/);
    snapshot=await browser.read();target=snapshot.elements.find(e=>e.label==='Marcar localmente');
    await browser.act({tool:'browser_click',target:target.id,snapshot_id:snapshot.snapshot_id});
    assert.equal(await browser.script(`document.body.dataset.clicked`),'yes');
    snapshot=await browser.read();target=snapshot.elements.find(e=>e.type==='password');
    await assert.rejects(()=>browser.act({tool:'browser_type',target:target.id,snapshot_id:snapshot.snapshot_id,content:'synthetic'}),/protegido/);
    browser.stop();assert.equal(browser.lastSnapshot,null);
    console.log(JSON.stringify({browser:'ok',public_https:'docs.ollama.com via CONNECT proxy',dom_read_click_type:'synthetic fixture passed',stale_snapshot:'refused',password_field:'refused',user_accounts:'not accessed'}));
  }catch(error){console.error(error);process.exitCode=1;}
  finally{browser.close();electron.app.quit();}
});
