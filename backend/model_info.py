"""Reported model capabilities, separated from the application's active budget."""
import copy

def unknown_info():
    return {'source':'unknown','capabilities':{key:None for key in ('text','vision','tools','thinking')},
        'max_context':None,'thinking_values':None,'thinking_default':None}

def normalize_info(data):
    info=unknown_info()
    if not isinstance(data,dict):return info
    info['source']='ollama'
    caps=data.get('capabilities')
    if isinstance(caps,list) and all(isinstance(value,str) for value in caps):
        for key,name in (('text','completion'),('vision','vision'),('tools','tools'),('thinking','thinking')):
            info['capabilities'][key]=name in caps
    model=data.get('model_info') or {}
    if isinstance(model,dict):
        architecture=model.get('general.architecture')
        maximum=model.get(str(architecture)+'.context_length') if architecture else None
        if maximum is None:
            candidates=[value for key,value in model.items() if key.endswith('.context_length')]
            if len(candidates)==1:maximum=candidates[0]
        if isinstance(maximum,int) and not isinstance(maximum,bool) and 256<=maximum<=100_000_000:info['max_context']=maximum
    thinking=data.get('thinking')
    if isinstance(thinking,dict):
        values=thinking.get('values')
        if isinstance(values,list) and values and all(isinstance(v,bool) or isinstance(v,str) and 0<len(v)<=40 for v in values):
            info['thinking_values']=values
            default=thinking.get('default')
            info['thinking_default']=default if isinstance(default,(bool,str)) and default in values else None
            info['capabilities']['thinking']=any(v is not False for v in values)
    return info

def effective_profile(profile,info):
    result=copy.deepcopy(profile);requested=result['options']['num_ctx'];maximum=info.get('max_context')
    result['requested_context']=requested;result['model_context_limit']=maximum
    if maximum is not None:result['options']['num_ctx']=min(requested,maximum)
    result['options']['num_predict']=min(result['options']['num_predict'],max(1,result['options']['num_ctx']//2))
    result['context_limited_by_model']=result['options']['num_ctx']<requested
    return result

async def describe(provider,model,**kwargs):
    if hasattr(provider,'describe'):return await provider.describe(model,**kwargs)
    # Older adapters may report capabilities without model details.
    caps=await provider.capabilities(model) if hasattr(provider,'capabilities') else None
    return normalize_info({'capabilities':caps}) if caps is not None else unknown_info()
