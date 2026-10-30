// Test-only bridge for the isolated, hidden renderer. Never packaged with ALT.
const { contextBridge } = require('electron');
let failure='stream',level=4,streamCalls=0,routeCalls=0,offline=false,cards=false;const opened=[];
const cid='00000000-0000-0000-0000-000000000001';
const preferences={accent:'#ff0057',theme:'Night City Pink',opacity:94,font_size:15,glow:35,compact:false,animations:false,model:'auto',performance:'notebook',personality:{name:'ALT-AI',tone:'Direta, calma e precisa; obedece primeiro.',irony:20,challenge:15,warmth:45,formality:50,instructions:''},secondary:'#00c9f5',appearance:'dark',scale:1,chat_opacity:100,effects:true,radius:13,shortcut:'Control+Shift+Space',always_on_top:false,user_name:''};
const conversation={id:cid,title:'Teste visual sintético',created:new Date().toISOString(),updated:new Date().toISOString()};
const messages=[{id:'user-1',role:'user',content:'Quero organizar meus projetos com calma. Por onde começamos?',status:'complete',created:conversation.created,metrics:null,model:null},{id:'assistant-1',role:'assistant',content:'Vamos separar o que precisa acontecer hoje do que só está fazendo barulho.\n\nQual projeto merece sua primeira hora de atenção? Podemos começar com uma lista curta de prioridades e definir um próximo passo concreto para cada uma.',status:'complete',created:conversation.created,metrics:null,model:'qwen3.5:4b'}];
// Result cards (stage 2): one of each outcome the card must tell apart.
const actionId=n=>'00000000-0000-0000-0000-00000000c0'+String(n).padStart(2,'0');
const resultCards=[
  {id:actionId(1),state:'complete',preview:{tool:'web_search',query:'previsão do tempo Curitiba'},result:{ok:true,found:true,query:'previsão do tempo Curitiba',status:'done',results:[{title:'Previsão Curitiba — fonte sintética A',url:'https://example.com/tempo/curitiba',snippet:'Trecho sintético da primeira fonte, longo o bastante para quebrar em duas linhas numa janela estreita.'},{title:'Fonte sintética B',url:'https://www.example.org/b',snippet:'Outro trecho.'}],notice:'Resultados recuperados da internet; não representam verificação independente dos fatos.'}},
  {id:actionId(2),state:'complete',preview:{tool:'web_search',query:'termo sem resultado sintético'},result:{ok:true,found:false,query:'termo sem resultado sintético',results:[],notice:'Pesquisa concluída, mas nenhuma fonte HTTPS utilizável foi retornada para esta consulta. Isso não prova que a informação não exista.'}},
  {id:actionId(3),state:'complete',preview:{tool:'write_text',path:'C:\Projetos\Aurora\resumo.txt'},result:{path:'C:\Projetos\Aurora\resumo.txt',bytes:2048,undo_available:true}},
  {id:actionId(4),state:'complete',preview:{tool:'windows_type',target:'Campo de busca'},result:{status:'unverified',notice:'Texto enviado, mas o campo não mostrou o valor esperado.'}},
  {id:actionId(5),state:'complete',preview:{tool:'run_command',command:'Get-Item inexistente'},result:{status:'failed',command:'Get-Item inexistente',exit_code:1,output:'Get-Item : Não é possível localizar o caminho sintético.',truncated:false}},
  {id:actionId(6),state:'interrupted',preview:{tool:'read_webpage',url:'https://example.com/longa'}},
];
contextBridge.exposeInMainWorld('alt',{
  request:async(method,route,body)=>{
    if(route==='/settings')return method==='PUT'?body:preferences;
    if(route==='/health')return {stopped:false,game_mode:false};
    if(route==='/models'||route==='/models?refresh=true')return offline?{connected:false,models:[]}:{connected:true,models:[{name:'qwen3.5:4b',size:3e9,info:{source:'ollama',capabilities:{text:true,vision:true,tools:true,thinking:true},active_context:4096,max_context:262144,thinking_values:[false,true],thinking_default:true}},{name:'qwen3.5:9b',size:6e9}]};
    if(route==='/providers')return {providers:[]};
    if(route==='/evaluations')return {runs:[]};
    if(route==='/conversations')return method==='POST'?conversation:[conversation];
    if(route.endsWith('/messages'))return messages;
    if(route.endsWith('/actions'))return cards?resultCards:[];
    if(route==='/permissions'){if(method==='PUT')level=body.level;return {level,scopes:[{id:'fixture-scope',path:'C:\\Projetos\\Aurora'}],auto_scopes:['fixture-scope']};}
    if(route==='/chat/estimate')return failure==='direct'?{fits:true,input_tokens:0,input_limit:0,history_included:0,history_total:0,tokenizer:'sem geração',model:'local:actions',requested_model:body.model,execution:'direct',components:{}}:{fits:failure!=='context',input_tokens:failure==='context'?3500:1550,input_limit:3200,history_included:2,history_total:2,tokenizer:'Qwen 3.5',model:'qwen3.5:4b',requested_model:body.model,components:{message:100,instructions:700,tools:450,app_context:300},app_context_omitted:1,reason:failure==='context'?'Mensagem sintética acima do contexto.':undefined};
    if(route==='/chat/route'){routeCalls++;return {model:'qwen3.5:4b',band:'simples',reason:'Escolha sintética'};}
    if(route==='/voice/status'){const off={installed:false,downloading:false,progress:0,error:'',size_mb:0};return {...off,whisper:off,dora:off,wake:off,state:'off',engine:'dora',speaking:false};}
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
  stream:async(id,kind,body,callback)=>{
    if(kind==='voice')return new Promise(()=>{});streamCalls++;
    if(failure==='direct'){
      callback({type:'start',model:'local:actions',execution:'direct'});
      callback({type:'delta',text:'Proposta sintética, ainda não executada.'});
      callback({type:'done',status:'complete',metrics:{execution:'direct'}});
      return;
    }
    throw new Error('Falha sintética de transporte antes da aceitação.');
  },
  window:async()=>true,
  chooseWorkspace:async()=>null,
  grantWindows:async()=>{throw new Error('No real permission grants in a fixture.');},
  onUpdate:()=>()=>{},
  importDocument:async()=>null,
  openSource:async(id,url)=>{opened.push(['source',id,url]);},
  revealFile:async id=>{opened.push(['reveal',id]);return {shown:true};},
  exportFile:async id=>{opened.push(['export',id]);return {saved:false};},
});
contextBridge.exposeInMainWorld('chatFixture',{setFailure:value=>{failure=value;},calls:()=>streamCalls,routes:()=>routeCalls,withoutModel:()=>{offline=true;preferences.model='';},showCards:()=>{cards=true;},opened:()=>opened});
