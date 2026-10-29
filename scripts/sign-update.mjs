import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {hashFile}=require('../apps/desktop/electron/update-security.cjs');
const root=path.resolve(import.meta.dirname,'..');
const publicPath=path.join(root,'assets','update-public-key.pem');
const privatePath=path.join(root,'.local','update-private-key.pem');
if(process.argv.includes('--init')){
 if(fs.existsSync(publicPath)){if(!fs.existsSync(privatePath)&&!process.env.ALT_UPDATE_PRIVATE_KEY)throw new Error('A chave pública já existe. Restaure a chave privada original para assinar; não substitua a identidade automaticamente.');process.exit(0);}
 const pair=crypto.generateKeyPairSync('ed25519');fs.mkdirSync(path.dirname(privatePath),{recursive:true});
 fs.writeFileSync(privatePath,pair.privateKey.export({type:'pkcs8',format:'pem'}),{mode:0o600,flag:'wx'});
 fs.writeFileSync(publicPath,pair.publicKey.export({type:'spki',format:'pem'}),{flag:'wx'});
 console.log('Chave pública criada em assets; chave privada local fora do Git. Guarde backup privado para assinar versões futuras.');process.exit(0);
}
const pkg=JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8'));
const file=`ALT-AI-Setup-${pkg.version}-x64.exe`;const installer=path.join(root,'release',file);
const privatePem=process.env.ALT_UPDATE_PRIVATE_KEY||fs.readFileSync(privatePath,'utf8');
const derived=crypto.createPublicKey(privatePem).export({type:'spki',format:'pem'});
if(derived!==fs.readFileSync(publicPath,'utf8'))throw new Error('Chave privada não corresponde à identidade pública versionada.');
const payload={version:pkg.version,file,size:fs.statSync(installer).size,sha256:await hashFile(installer)};
const signature=crypto.sign(null,Buffer.from(JSON.stringify(payload)),privatePem).toString('base64');
fs.writeFileSync(path.join(root,'release',`ALT-AI-${pkg.version}-update.json`),JSON.stringify({payload,signature},null,2));
fs.writeFileSync(path.join(root,'release','SHA256SUMS.txt'),`${payload.sha256}  ${file}\n`);
console.log('Manifesto Ed25519 e SHA256 gerados. Isso verifica a origem do projeto; não substitui certificado Windows Authenticode.');
