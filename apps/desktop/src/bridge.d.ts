import type { StreamEvent } from '../../../packages/shared-types';
declare global {interface Window {alt:{request<T=unknown>(method:string,route:string,body?:unknown):Promise<T>;stream(id:string,kind:'chat'|'pull',body:unknown,callback:(event:StreamEvent)=>void):Promise<void>;window(action:string):Promise<boolean|undefined>;installOllama():Promise<{ok:boolean;message:string}>;ollamaWebsite():Promise<void>}}}
export {};
