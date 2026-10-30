import re
from backend.tools.service import ToolProposal

# Short descriptions so a small model knows which field carries what.
HINTS={
    'app':'Nome do programa instalado, como o usuário falou (ex.: Spotify, Google Chrome, Discord).',
    'url':'Endereço do site; pode ser só o domínio, como youtube.com.',
    'query':'Termos de pesquisa.',
    'command':'Comando completo do PowerShell.',
    'keys':'Atalho de teclado, ex.: ctrl+t, ctrl+w, alt+left, f5, pagedown*3, space.',
    'value':'Valor: volume/brilho (50, +10, -10, mudo), mídia (playpause, next, previous) ou horário do lembrete (2026-10-30T15:00, em 10 minutos).',
}

# Shortcut-style requests: tabs, scrolling, reload, media keys.
KEY_WORDS=('atalho','tecla','aperte','pressione','ctrl','alt+','fecha a aba','feche a aba','fechar aba','próxima aba','proxima aba','aba anterior',
    'role ','rola ','rolar','desça','desce','suba a página','recarreg','atualize a página','f5','tela cheia')
SCREEN_WORDS=('minha tela','na tela','da tela','olha isso','olhe isso','o que tem aqui','o que aparece','print da tela','lê isso aqui','leia isso aqui','o que estou vendo')
VOLUME_WORDS=('volume','som ','mudo','silencia','desmut','aumenta o som','abaixa o som','mais alto','mais baixo')
MEDIA_WORDS=('pausa','pause','despausa','próxima música','proxima musica','música anterior','musica anterior','pula a música','pula essa','volta a música','toca a música','continua a música')
ROUTINE_WORDS=('rotina','todo dia','todos os dias','toda manhã','toda noite','toda segunda','toda terça','toda quarta','toda quinta','toda sexta','todo sábado','todo domingo','a cada ')
MEMORY_WORDS=('lembra','lembrar','você sabe','voce sabe','vc sabe','sobre mim','o que eu te disse','o que eu falei','anotou','minhas preferências','meu aniversário')
REMINDER_WORDS=('lembre','lembrete','me avise','me avisa','me lembra','alarme','avisa às','avise às')

# Stable set for modes 2-4, core first and capped at 14 like Mark LVI's local budget. The same list every
# turn keeps the prompt prefix identical, so Ollama reuses its cache instead of rereading tools and history.
STABLE=['open_app','open_url','web_search','close_app','windows_keys','windows_read','windows_invoke','windows_type',
    'read_webpage','list_files','read_text','write_text','run_command','download_file']
BRIEF={
    'open_app':'abre um programa instalado pelo nome (app)','open_url':'abre um site em nova aba do navegador padrão (url ou query)',
    'web_search':'pesquisa na internet (query)','close_app':'fecha um programa (app)','read_webpage':'lê o texto de uma página (url)',
    'windows_keys':'envia um atalho de teclado a uma janela (window_id = título ou programa, keys)',
    'windows_read':'lê os elementos de uma janela aberta (window_id)','windows_invoke':'clica num elemento lido (window_id, target, snapshot_id)',
    'windows_type':'digita num campo lido (window_id, target, snapshot_id, content)','list_files':'lista uma pasta (scope_id, path)',
    'read_text':'lê um arquivo de texto (scope_id, path)','write_text':'grava um arquivo de texto (scope_id, path, content)',
    'run_command':'executa PowerShell depois da aprovação do usuário (command)','download_file':'baixa um arquivo (url, path)',
    'find_files':'procura arquivos (scope_id, path, query)','open_folder':'abre uma pasta no Explorer (scope_id, path)',
    'screen_look':'captura a tela do usuário para você ver (sem argumentos)','system_volume':'muda o volume (value: 0-100, +10, -10, mudo, desmutar)',
    'system_brightness':'muda o brilho do monitor (value: 0-100, +10, -10)','media_key':'tocar/pausar ou trocar de música (value: playpause, next, previous)',
    'reminder_create':'cria um lembrete que toca mesmo com a ALT fechada (content: texto, value: 2026-10-30T15:00 ou "em 10 minutos")',
    'reminder_list':'lista os lembretes','memory_recall':'procura nas memórias salvas do usuário (query)',
    'routine_create':'agenda uma rotina que roda sozinha (content: o que fazer, value: "diário 08:00", "seg,qua 18:00" ou "a cada 60 min", target: nome)','routine_list':'lista as rotinas','reminder_cancel':'cancela um lembrete (target: id ou parte do texto)',
    'calculate':'calcula uma expressão (expression)','undo':'desfaz a última gravação ou download da ALT (target vazio = última)','browser_open':'abre site no navegador ALT (url)','browser_read':'lê a página do navegador ALT',
    'browser_back':'volta uma página no navegador ALT','browser_click':'clica no navegador ALT (target, snapshot_id)',
    'browser_type':'digita no navegador ALT (target, snapshot_id, content)',
}
STABLE_FIELDS=('tool','app','url','query','scope_id','path','content','command','keys','window_id','target','snapshot_id','expression','value')

def tool_spec(content,status):
    names,browser,windows=route(content,status)
    if not names:return None
    return build_spec(names,browser,windows)

def stable_tool_spec(content,status,allowed=lambda name:True):
    """Modes 2-4: the same tools every turn, plus any routed tool outside the core list."""
    routed,browser,_=route(content,status)
    # Window tools only where they can work: full access, or windows the owner granted (rarely changes).
    usable=lambda n:allowed(n) and (not n.startswith('windows_') or status['level']==4 or bool(status.get('windows')))
    names=[n for n in STABLE if usable(n)]+[n for n in routed if n not in STABLE and usable(n)]
    if not names:return None,[]
    schema=ToolProposal.model_json_schema()['properties']
    properties={key:{**{k:v for k,v in schema[key].items() if k in ('type','enum')},**({'description':HINTS[key]} if key in HINTS else {})} for key in STABLE_FIELDS}
    properties['tool']={'type':'string','enum':names}
    description=('Executa uma ação no computador; o aplicativo aplica permissões e aprovações. Só afirme execução com resultado confirmado. '
        'Ferramentas: '+'; '.join(f'{n}: {BRIEF[n]}' for n in names if n in BRIEF)+'. '
        'Em janelas, windows_invoke e windows_type usam target e snapshot_id lidos por windows_read.')
    spec=[{'type':'function','function':{'name':'alt_propose_action','description':description,'parameters':{'type':'object','properties':properties,'required':['tool'],'additionalProperties':False}}}]
    return spec,[n for n in routed if allowed(n)]

def route(content,status):
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
    if not browser and (any(word in text for word in ('pesquis','busque','buscar','procure','naveg','acesse','página','pagina','site','https://','http://','.com','google','youtube','link','abr','entra')) or re.search(r'\babas?\b',text)):names+=['web_search','read_webpage','open_url']
    if level>=2 and any(word in text for word in ('arquivo','pasta','documento','salve','grave','leia','listar','escreva no','crie um')):names+=['list_files','find_files','read_text','write_text','open_folder']
    if any(word in text for word in ('abra','abre','abrir','abri','inici','calculadora','bloco de notas','notepad','programa','aplicativo','app ')):names+=['open_app']
    if any(word in text for word in ('feche','fecha','fechar','encerr')):names+=['close_app']
    if any(word in text for word in ('calcule','quanto é','quanto e','calcular')):names+=['calculate']
    if any(word in text for word in ('baixe','baixar','download')):names+=['download_file']
    if level>=2 and any(word in text for word in ('desfaz','desfazer','desfaça','reverte','reverter','volta como estava')):names+=['undo']
    if level>=2 and any(word in text for word in SCREEN_WORDS):names+=['screen_look']
    if level>=2 and any(word in text+' ' for word in VOLUME_WORDS):names+=['system_volume']
    if level>=2 and 'brilho' in text:names+=['system_brightness']
    if level>=2 and any(word in text for word in MEDIA_WORDS):names+=['media_key']
    if any(word in text for word in MEMORY_WORDS):names+=['memory_recall']
    if level>=2 and any(word in text for word in ROUTINE_WORDS):names+=['routine_create','routine_list']
    if level>=2 and any(word in text for word in REMINDER_WORDS):
        names+=['reminder_create','reminder_list']
        if any(word in text for word in ('cancel','apaga','remove','tira o lembrete')):names+=['reminder_cancel']
    if level>=2 and any(word in text for word in ('comando','powershell','terminal','execute','executar','rode ','rodar','instale','instalar','winget','ipconfig')):names+=['run_command']
    keys=any(word in text for word in KEY_WORDS)
    windows=(status.get('windows') or level==4) and (keys or any(word in text for word in ('janela','aplicativo aberto','programa aberto','no app','botão','botao','campo','clique','clicar','digite','escreva')))
    if windows:
        names+=['windows_read']
        if any(word in text for word in ('clique','clicar','aperte','pressione','marque','selecione')):names+=['windows_invoke']
        if any(word in text for word in ('digite','escreva','preencha')):names+=['windows_type']
        if keys:names+=['windows_keys']
    return list(dict.fromkeys(names)),browser,windows

def build_spec(names,browser,windows):
    schema=ToolProposal.model_json_schema();properties={key:value for key,value in schema['properties'].items() if key in {'tool','query','url','scope_id','path','content','app','expression','target','snapshot_id','window_id','command','keys'}}
    relevant={'tool'}
    if any(name in names for name in ('web_search','read_webpage','open_url')):relevant.update(('query','url'))
    if any(name in names for name in ('list_files','find_files','read_text','write_text','open_folder')):relevant.update(('scope_id','path','content','query'))
    if any(name in names for name in ('open_app','close_app')):relevant.add('app')
    if browser:relevant.add('url')
    if any(name in names for name in ('browser_click','browser_type')):relevant.update(('target','snapshot_id','content'))
    if 'calculate' in names:relevant.add('expression')
    if 'download_file' in names:relevant.update(('url','path','scope_id'))
    if 'run_command' in names:relevant.add('command')
    if 'undo' in names:relevant.add('target')
    if any(n in names for n in ('system_volume','system_brightness','media_key','reminder_create')):relevant.add('value')
    if 'reminder_create' in names or 'routine_create' in names:relevant.update(('content','value','target'))
    if 'reminder_cancel' in names:relevant.update(('target','content'))
    if windows:relevant.update(('window_id','target','snapshot_id','content'))
    if 'windows_keys' in names:relevant.add('keys')
    properties={key:{**{k:v for k,v in value.items() if k in ('type','enum')},**({'description':HINTS[key]} if key in HINTS else {})} for key,value in properties.items() if key in relevant}
    properties['tool']={'type':'string','enum':names}
    description='Executa uma ação no computador; o aplicativo aplica permissões. Só afirme execução com resultado.'
    if 'open_url' in names:description+=' open_url abre um site em nova aba do navegador padrão do usuário.'
    if 'open_app' in names:description+=' open_app abre um programa instalado pelo nome.'
    if 'run_command' in names:description+=' run_command executa PowerShell depois da aprovação do usuário.'
    if browser:description+=' Clique/digitação no navegador ALT exigem target e snapshot_id observados em browser_read.'
    if windows:description+=' Em janelas, leia com windows_read (window_id pode ser o título ou o programa) e use window_id, target e snapshot_id observados.'
    if 'windows_keys' in names:description+=' windows_keys envia um atalho à janela (window_id = título ou programa, ex.: chrome) sem precisar ler antes.'
    return [{'type':'function','function':{'name':'alt_propose_action','description':description,'parameters':{'type':'object','properties':properties,'required':['tool'],'additionalProperties':False}}}]
