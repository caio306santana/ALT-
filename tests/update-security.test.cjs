const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const crypto=require('node:crypto');
const {verifyUpdate,hashFile}=require('../apps/desktop/electron/update-security.cjs');
test('signed update verifies content and refuses tampering, wrong key and rollback',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'alt-update-test-'));
 try{
  const file=path.join(dir,'ALT-AI-Setup-0.3.0-x64.exe');fs.writeFileSync(file,'synthetic installer fixture');
  const {privateKey,publicKey}=crypto.generateKeyPairSync('ed25519');
  const payload={version:'0.3.0',file:path.basename(file),size:fs.statSync(file).size,sha256:await hashFile(file)};
  const sign=p=>({payload:p,signature:crypto.sign(null,Buffer.from(JSON.stringify(p)),privateKey).toString('base64')});
  const args={installerPath:file,manifest:sign(payload),publicKey,currentVersion:'0.2.0'};
  assert.equal((await verifyUpdate(args)).version,'0.3.0');
  await assert.rejects(verifyUpdate({...args,currentVersion:'0.3.0'}),/igual ou anterior/);
  await assert.rejects(verifyUpdate({...args,currentVersion:'0.4.0'}),/igual ou anterior/);
  await assert.rejects(verifyUpdate({...args,manifest:{...args.manifest,payload:{...payload,version:'0.5.0'}}}),/Assinatura/);
  await assert.rejects(verifyUpdate({...args,publicKey:crypto.generateKeyPairSync('ed25519').publicKey}),/Assinatura/);
  await assert.rejects(verifyUpdate({...args,manifest:sign({...payload,file:'other.exe'})}),/Metadados/);
  fs.writeFileSync(file,'altered installer fixture!!');
  await assert.rejects(verifyUpdate(args),/tamanho|alterado/);
 }finally{assert(path.resolve(dir).startsWith(path.resolve(os.tmpdir())+path.sep));assert(path.basename(dir).startsWith('alt-update-test-'));fs.rmSync(dir,{recursive:true,force:true});}
});
