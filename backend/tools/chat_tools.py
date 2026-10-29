import re
from backend.tools.service import ToolProposal

def tool_spec(content,status):
    text=content.lower()
    names=[]
    if any(word in text for word in ('pesquis','busque','buscar na internet','procure na internet','naveg','acesse','página','pagina','site','https://')):names+=['web_search','read_webpage','open_url']
    if status['level']>=2 and any(word in text for word in ('arquivo','pasta','documento','salve','grave','leia','listar','escreva no','crie um')):names+=['list_files','read_text','write_text','open_folder']
    if any(word in text for word in ('abra','abrir','calculadora','bloco de notas','notepad')):names+=['open_app']
    if any(word in text for word in ('calcule','quanto é','quanto e','calcular')):names+=['calculate']
    if not names:return None
    schema=ToolProposal.model_json_schema();properties={key:value for key,value in schema['properties'].items() if key in {'tool','query','url','scope_id','path','content','app','expression'}}
    relevant={'tool'}
    if any(name in names for name in ('web_search','read_webpage','open_url')):relevant.update(('query','url'))
    if any(name in names for name in ('list_files','read_text','write_text','open_folder')):relevant.update(('scope_id','path','content'))
    if 'open_app' in names:relevant.add('app')
    if 'calculate' in names:relevant.add('expression')
    properties={key:{k:v for k,v in value.items() if k not in ('default','title')} for key,value in properties.items() if key in relevant}
    properties['tool']={'type':'string','enum':list(dict.fromkeys(names))}
    return [{'type':'function','function':{'name':'alt_propose_action','description':'Propor uma ferramenta real. O aplicativo aplica permissões e pede aprovação. web_search pesquisa; read_webpage lê URL pública. Não alegue execução antes do resultado.','parameters':{'type':'object','properties':properties,'required':['tool'],'additionalProperties':False}}}]
