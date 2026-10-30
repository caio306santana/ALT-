import type { ModelInfo } from '../../../../packages/shared-types';

const labels = {text:'Texto',vision:'Imagens',tools:'Ferramentas',thinking:'Raciocínio'};
export function ModelCapabilities({info,activeContext,compact=false}:{info?:ModelInfo;activeContext?:number;compact?:boolean}) {
  return <div className={'model-capabilities'+(compact?' compact':'')} aria-label="Capacidades informadas pelo modelo">
    <div className="capability-badges">{Object.entries(labels).map(([key,label])=>{
      const value=info?.capabilities[key as keyof ModelInfo['capabilities']];
      return <span key={key} title={key==='thinking'?'Recurso de raciocínio separado declarado pelo motor; não mede a qualidade das respostas.':undefined} className={value===true?'supported':value===false?'unsupported':'unknown'}>{label}: {value===true?'sim':value===false?'não':'não informado'}</span>;
    })}</div>
    <div className="capability-context">Contexto ativo: {(activeContext??info?.active_context)?.toLocaleString('pt-BR')??'não informado'} tokens
      {' · '}Máximo declarado: {info?.max_context?.toLocaleString('pt-BR')??'não informado'}{info?.max_context?' tokens':''}
      {info?.context_limited_by_model?' · limitado pelo modelo':''}
    </div>
    {!compact&&<small>{info?.thinking_values?`Controles de raciocínio informados: ${info.thinking_values.map(String).join(', ')}.`:'Controles de raciocínio não informados.'} O contexto ativo é o perfil em uso; não aumenta automaticamente até o máximo do modelo. Ações locais diretas dispensam suporte do motor a ferramentas.</small>}
  </div>;
}
