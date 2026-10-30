const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const crypto=require('node:crypto');
const {checkRelease,parseRelease,stageRelease}=require('../apps/desktop/electron/update-feed.cjs');
const {verifyUpdate}=require('../apps/desktop/electron/update-security.cjs');
const base='https://github.com/caio306santana/ALT-/releases/download/v0.4.0/';
const release={tag_name:'v0.4.0',name:'ALT-AI 0.4.0',body:'## Novidades\n- Tarefas',published_at:'2026-10-30T12:00:00Z',html_url:'https://github.com/caio306santana/ALT-/releases/tag/v0.4.0',
  assets:[{name:'ALT-AI-Setup-0.4.0-x64.exe',size:10,browser_download_url:base+'ALT-AI-Setup-0.4.0-x64.exe'},{name:'ALT-AI-0.4.0-update.json',size:300,browser_download_url:base+'ALT-AI-0.4.0-update.json'}]};
const reply=(status,body)=>({status,ok:status===200,json:async()=>body,url:'',body:null});

test('only a newer published release with signed assets is offered, with its notes',async()=>{
  const info=parseRelease(release,'0.3.1');
  assert.equal(info.version,'0.4.0');assert.equal(info.notes,'## Novidades\n- Tarefas');assert.ok(info.downloadable);
  assert.equal(parseRelease(release,'0.4.0'),null);
  assert.equal(parseRelease({...release,draft:true},'0.3.1'),null);
  assert.equal(parseRelease({...release,assets:[]},'0.3.1').downloadable,false);
  assert.throws(()=>parseRelease({...release,assets:[{...release.assets[0],browser_download_url:'https://evil.example/x.exe'}]},'0.3.1'));
  assert.equal((await checkRelease('0.3.1',async()=>reply(404))).available,false);
  assert.match((await checkRelease('0.3.1',async()=>reply(404))).reason,/Nenhuma release/);
  // Prereleases count (every ALT release is one); the newest wins from a list.
  assert.equal((await checkRelease('0.3.1',async()=>reply(200,[{...release,prerelease:true,tag_name:'v0.3.5'},{...release,prerelease:true}]))).version,'0.4.0');
  assert.equal((await checkRelease('0.3.1',async()=>reply(200,release))).version,'0.4.0');
});

test('downloaded assets are staged and still need the Ed25519 signature',async()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'alt-feed-test-'));
  try{
    const installer=Buffer.from('synthetic installer');
    const {privateKey,publicKey}=crypto.generateKeyPairSync('ed25519');
    const payload={version:'0.4.0',file:'ALT-AI-Setup-0.4.0-x64.exe',size:installer.length,sha256:crypto.createHash('sha256').update(installer).digest('hex')};
    const manifest={payload,signature:crypto.sign(null,Buffer.from(JSON.stringify(payload)),privateKey).toString('base64')};
    const stream=data=>({ok:true,url:'',body:(async function*(){yield data;})()});
    const fetcher=async url=>stream(url.endsWith('.json')?Buffer.from(JSON.stringify(manifest)):installer);
    const staged=await stageRelease(parseRelease(release,'0.3.1'),dir,null,fetcher);
    assert.equal(path.basename(staged.installerPath),payload.file);
    assert.equal((await verifyUpdate({installerPath:staged.installerPath,manifest:staged.manifest,publicKey,currentVersion:'0.3.1'})).version,'0.4.0');
    const other=crypto.generateKeyPairSync('ed25519').publicKey;
    await assert.rejects(verifyUpdate({installerPath:staged.installerPath,manifest:staged.manifest,publicKey:other,currentVersion:'0.3.1'}));
    const oversized=async url=>stream(url.endsWith('.json')?Buffer.from(JSON.stringify(manifest)):Buffer.concat([installer,installer]));
    await assert.rejects(stageRelease(parseRelease(release,'0.3.1'),dir,null,oversized),/maior/);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
