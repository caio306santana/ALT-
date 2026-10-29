import re
from backend.tools.service import ToolProposal

# Short descriptions so a small model knows which field carries what.
HINTS={
    'app':'Nome do programa instalado, como o usuário falou (ex.: Spotify, Google Chrome, Discord).',
    'url':'Endereço do site; pode ser só o domínio, como youtube.com.',
    'query':'Termos de pesquisa.',
    'command':'Comando completo do PowerShell.',
}

def tool_spec(content,status):
    text=content.lower()
    names=[]
    level=status['level']
    # "navegador" alone means the user's own browser unless a page is open in the ALT browser.
    browser=any(word in text for word in ('navegador alt','navegador isolado','página aberta','pagina aberta','volte à página')) or bool(status.get('browser_page')) and any(word in text for word in ('navegador','página','pagina','clique','digite'))
    if browser:
        names+=['browser_open','browser_read','browser_back']
        if any(word in text for word in ('clique','clicar')):names+=['browser_click']
        if any(word in text for word in ('digite','preencha')):names+=['browser_type']
    # Opening sites and programs is offered on every message in modes 3/4: keyword routing missed
    # ordinary requests ("abre o google", "nova aba") and left the model with the wrong tool.
    # Only opening is always on: with calculate always offered, the 9B "calculated" a daily schedule.
    if level>=3:names+=['open_url','open_app']
    if not browser and any(word in text for word in ('pesquis','busque','buscar','procure','naveg','acesse','página','pagina','site','https://','http://','.com','aba','google','youtube','link','abr','entra')):names+=['web_search','read_webpage','open_url']
    if level>=2 and any(word in text for word in ('arquivo','pasta','documento','salve','grave','leia','listar','escreva no','crie um')):names+=['list_files','find_files','read_text','write_text','open_folder']
    if any(word in text for word in ('abra','abre','abrir','abri','inici','calculadora','bloco de notas','notepad','programa','aplicativo','app ')):names+=['open_app']
    if any(word in text for word in ('feche','fecha','fechar','encerr')):names+=['close_app']
    if any(word in text for word in ('calcule','quanto é','quanto e','calcular')):names+=['calculate']
    if any(word in text for word in ('baixe','baixar','download')):names+=['download_file']
    if level>=2 and any(word in text for word in ('comando','powershell','terminal','execute','executar','rode ','rodar','instale','instalar','winget','ipconfig')):names+=['run_command']
    windows=(status.get('windows') or level==4) and any(word in text for word in ('janela','aplicativo aberto','programa aberto','no app','botão','botao','campo','clique','clicar','digite','escreva'))
    if windows:
        names+=['windows_read']
        if any(word in text for word in ('clique','clicar','aperte','pressione','marque','selecione')):names+=['windows_invoke']
        if any(word in text for word in ('digite','escreva','preencha')):names+=['windows_type']
    if not names:return None
    names=list(dict.fromkeys(names))
    schema=ToolProposal.model_json_schema();properties={key:value for key,value in schema['properties'].items() if key in {'tool','query','url','scope_id','path','content','app','expression','target','snapshot_id','window_id','command'}}
    relevant={'tool'}
    if any(name in names for name in ('web_search','read_webpage','open_url')):relevant.update(('query','url'))
    if any(name in names for name in ('list_files','find_files','read_text','write_text','open_folder')):relevant.update(('scope_id','path','content','query'))
    if any(name in names for name in ('open_app','close_app')):relevant.add('app')
    if browser:relevant.add('url')
    if any(name in names for name in ('browser_click','browser_type')):relevant.update(('target','snapshot_id','content'))
    if 'calculate' in names:relevant.add('expression')
    if 'download_file' in names:relevant.update(('url','path','scope_id'))
    if 'run_command' in names:relevant.add('command')
    if windows:relevant.update(('window_id','target','snapshot_id','content'))
    properties={key:{**{k:v for k,v in value.items() if k in ('type','enum')},**({'description':HINTS[key]} if key in HINTS else {})} for key,value in properties.items() if key in relevant}
    properties['tool']={'type':'string','enum':names}
    description='Executa uma ação no computador; o aplicativo aplica permissões. Só afirme execução com resultado.'
    if 'open_url' in names:description+=' open_url abre um site em nova aba do navegador padrão do usuário.'
    if 'open_app' in names:description+=' open_app abre um programa instalado pelo nome.'
    if 'run_command' in names:description+=' run_command executa PowerShell depois da aprovação do usuário.'
    if browser:description+=' Clique/digitação no navegador ALT exigem target e snapshot_id observados em browser_read.'
    if windows:description+=' Em janelas, leia com windows_read (window_id pode ser o título ou o programa) e use window_id, target e snapshot_id observados.'
    return [{'type':'function','function':{'name':'alt_propose_action','description':description,'parameters':{'type':'object','properties':properties,'required':['tool'],'additionalProperties':False}}}]
