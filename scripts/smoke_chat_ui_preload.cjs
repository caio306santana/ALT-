// Test-only bridge for the isolated, hidden renderer. Never packaged with ALT.
const { contextBridge } = require('electron');
let failure='stream',level=4,streamCalls=0;
const cid='00000000-0000-0000-0000-000000000001';
const preferences={accent:'#ff0057',theme:'Night City Pink',opacity:94,font_size:15,glow:35,compact:false,animations:false,model:'qwen3.5:4b',performance:'notebook',personality:{name:'ALT-AI',tone:'Calma e provocadora nas ideias.',irony:55,challenge:75,warmth:50,formality:35,instructions:''},secondary:'#00c9f5',appearance:'dark',scale:1,chat_opacity:100,effects:true,radius:13,shortcut:'Control+Shift+Space',always_on_top:false,user_name:''};
const conversation={id:cid,title:'Teste visual sintético',created:new Date().toISOString(),updated:new Date().toISOString()};
const messages=[{id:'user-1',role:'user',content:'Quero organizar meus projetos com calma. Por onde começamos?',status:'complete',created:conversation.created,metrics:null,model:null},{id:'assistant-1',role:'assistant',content:'Vamos separar o que precisa acontecer hoje do que só está fazendo barulho.\n\nQual projeto merece sua primeira hora de atenção? Podemos começar com uma lista curta de prioridades e definir um próximo passo concreto para cada uma.',status:'complete',created:conversation.created,metrics:null,model:'qwen3.5:4b'}];
contextBridge.exposeInMainWorld('alt',{
  request:async(method,route,body)=>{
    if(route==='/settings')return method==='PUT'?body:preferences;
    if(route==='/health')return {stopped:false,game_mode:false};
    if(route==='/models')return {connected:true,models:[{name:'qwen3.5:4b',size:3e9}]};
    if(route==='/providers')return {providers:[]};
    if(route==='/conversations')return method==='POST'?conversation:[conversation];
    if(route.endsWith('/messages'))return messages;
    if(route.endsWith('/actions'))return [];
    if(route==='/permissions'){if(method==='PUT')level=body.level;return {level,scopes:[{id:'fixture-scope',path:'C:\\Projetos\\Aurora'}],auto_scopes:['fixture-scope']};}
    if(route==='/chat/estimate')return {fits:failure!=='context',input_tokens:failure==='context'?3500:1550,input_limit:3200,history_included:2,history_total:2,tokenizer:'Qwen 3.5',reason:failure==='context'?'Mensagem sintética acima do contexto.':undefined};
    if(route==='/knowledge/status')return {status:'complete',completed:3,total:3,indexed:3,items:3};
    if(route.endsWith('/project'))return {project_id:''};
    if(route==='/projects')return [{id:'00000000-0000-0000-0000-0000000000aa',name:'Aurora',created:conversation.created}];
    if(route==='/tasks')return [{id:'00000000-0000-0000-0000-0000000000bb',conversation_id:cid,goal:'Calcule 15% de 2400 e grave em resultado.txt',model:'qwen3.5:4b',scope_id:'fixture-scope',state:'awaiting_approval',cursor:1,
      plan:{steps:[{title:'Calcular 15% de 2400',action:{tool:'calculate',expression:'2400*0.15'}},{title:'Gravar resultado.txt',action:{tool:'write_text',path:'resultado.txt',content:'Resultado: 360'}}]},
      history:[{step:'Calcular 15% de 2400',tool:'calculate',verified:true,reason:'Resultado conferido com a ferramenta.',result_excerpt:'{"value": 360.0}'}],
      current_proposal:{id:'00000000-0000-0000-0000-0000000000cc',preview:{tool:'write_text',path:'C:\Projetos\Aurora\resultado.txt',diff:'+Resultado: 360',creates_file:true}},notice:'Executando o plano revisado.',created:conversation.created}];
    // Lists the visual pass does not exercise in detail.
    if(method==='GET')return [];
    throw new Error('Unexpected fixture route '+route);
  },
  stream:async()=>{streamCalls++;throw new Error('Falha sintética de transporte antes da aceitação.');},
  window:async()=>true,
  chooseWorkspace:async()=>null,
  grantWindows:async()=>{throw new Error('No real permission grants in a fixture.');},
  onUpdate:()=>()=>{},
  importDocument:async()=>null,
});
contextBridge.exposeInMainWorld('chatFixture',{setFailure:value=>{failure=value;},calls:()=>streamCalls});
