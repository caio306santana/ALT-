import re
from backend.tools.service import ToolProposal

def tool_spec(content,status):
    text=content.lower()
    names=[]
    browser=any(word in text for word in ('navegador','página aberta','pagina aberta','clique','digite no','volte à página'))
    if browser:
        names+=['browser_open','browser_read','browser_back']
        if any(word in text for word in ('clique','clicar')):names+=['browser_click']
        if any(word in text for word in ('digite','preencha')):names+=['browser_type']
    if not browser and any(word in text for word in ('pesquis','busque','buscar na internet','procure na internet','naveg','acesse','página','pagina','site','https://')):names+=['web_search','read_webpage','open_url']
    if status['level']>=2 and any(word in text for word in ('arquivo','pasta','documento','salve','grave','leia','listar','escreva no','crie um')):names+=['list_files','find_files','read_text','write_text','open_folder']
    if not browser and any(word in text for word in ('abra','abrir','calculadora','bloco de notas','notepad')):names+=['open_app']
    if any(word in text for word in ('feche','fechar')):names+=['close_app']
    if any(word in text for word in ('calcule','quanto é','quanto e','calcular')):names+=['calculate']
    if any(word in text for word in ('baixe','baixar','download')):names+=['download_file']
    windows=status.get('windows') and any(word in text for word in ('janela','aplicativo aberto','programa aberto','no app','botão','botao','campo'))
    if windows:
        names+=['windows_read']
        if any(word in text for word in ('clique','clicar','aperte','pressione','marque','selecione')):names+=['windows_invoke']
        if any(word in text for word in ('digite','escreva','preencha')):names+=['windows_type']
    if not names:return None
    schema=ToolProposal.model_json_schema();properties={key:value for key,value in schema['properties'].items() if key in {'tool','query','url','scope_id','path','content','app','expression','target','snapshot_id','window_id'}}
    relevant={'tool'}
    if any(name in names for name in ('web_search','read_webpage','open_url')):relevant.update(('query','url'))
    if any(name in names for name in ('list_files','find_files','read_text','write_text','open_folder')):relevant.update(('scope_id','path','content','query'))
    if any(name in names for name in ('open_app','close_app')):relevant.add('app')
    if browser:relevant.add('url')
    if any(name in names for name in ('browser_click','browser_type')):relevant.update(('target','snapshot_id','content'))
    if 'calculate' in names:relevant.add('expression')
    if 'download_file' in names:relevant.update(('url','path','scope_id'))
    if windows:relevant.update(('window_id','target','snapshot_id','content'))
    properties={key:{k:v for k,v in value.items() if k in ('type','enum')} for key,value in properties.items() if key in relevant}
    properties['tool']={'type':'string','enum':list(dict.fromkeys(names))}
    description='Propor ação; aplicativo aplica permissões. Só afirme execução com resultado.'
    if browser:description+=' Clique/digitação exigem target e snapshot_id observados em browser_read.'
    if windows:description+=' Em janelas, leia com windows_read e use window_id, target e snapshot_id observados.'
    return [{'type':'function','function':{'name':'alt_propose_action','description':description,'parameters':{'type':'object','properties':properties,'required':['tool'],'additionalProperties':False}}}]
