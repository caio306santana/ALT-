import { spawn } from 'node:child_process';
import { createServer } from 'vite';
import electron from 'electron';
const server=await createServer({configFile:'apps/desktop/vite.config.ts'});
await server.listen();
const env={...process.env,ALT_DEV:'1'};delete env.ELECTRON_RUN_AS_NODE;
const child=spawn(electron,['.'],{stdio:'inherit',env,windowsHide:true});
child.on('exit',async code=>{await server.close();process.exit(code??0);});
process.on('SIGINT',()=>child.kill());
