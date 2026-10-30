"""Owner-controlled application policy, enforced independently of model text."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from backend.memory.library import reject_secrets

Decision = Literal['deny', 'ask', 'allow']

class Capabilities(BaseModel):
    model_config = ConfigDict(extra='forbid')
    calculate: Decision = 'ask'
    files_read: Decision = 'ask'
    files_write: Decision = 'ask'
    apps: Decision = 'ask'
    internet: Decision = 'ask'
    browser_navigation: Decision = 'ask'
    browser_interaction: Decision = 'ask'
    windows_read:Decision='ask'
    windows_control:Decision='ask'
    downloads:Decision='ask'
    # Commands always show an approval card; 'deny' removes the tool entirely.
    shell:Decision='ask'
    screen:Decision='ask'
    reminders:Decision='ask'
    memory:Decision='allow'

class OwnerPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rules: str = Field(default='', max_length=1500)
    memory_recall: Literal['manual', 'automatic','semantic'] = 'manual'
    auto_project_summaries:bool=False
    # Summary of the oldest messages when a conversation outgrows the context (derived, never a memory).
    conversation_summaries:bool=True
    capabilities: Capabilities = Field(default_factory=Capabilities)

CAPABILITY = {
    'calculate':'calculate', 'list_files':'files_read', 'find_files':'files_read',
    'read_text':'files_read', 'write_text':'files_write', 'open_folder':'apps',
    'open_app':'apps', 'close_app':'apps', 'web_search':'internet', 'read_webpage':'internet',
    'open_url':'internet', 'browser_open':'browser_navigation', 'browser_read':'browser_navigation',
    'browser_click':'browser_interaction', 'browser_type':'browser_interaction',
    'browser_back':'browser_navigation',
    'windows_read':'windows_read','windows_invoke':'windows_control','windows_type':'windows_control','windows_keys':'windows_control',
    'download_file':'downloads','find_download':'downloads','run_command':'shell','undo':'files_write',
    'screen_look':'screen','system_volume':'apps','system_brightness':'apps','media_key':'apps',
    'reminder_create':'reminders','reminder_list':'reminders','reminder_cancel':'reminders','memory_recall':'memory','routine_create':'reminders','routine_list':'reminders',
}

class Policy:
    def __init__(self, store): self.store = store

    def current(self):
        return OwnerPolicy(**self.store.settings().get('owner_policy', {}))

    def save(self, body):
        reject_secrets(body.rules)
        self.store.set_settings({'owner_policy': body.model_dump()})
        self.store.audit('owner_policy_changed')
        return self.describe()

    def decision(self, tool): return getattr(self.current().capabilities, CAPABILITY[tool])

    def check(self, tool):
        if self.decision(tool) == 'deny':
            raise PermissionError('Esta capacidade está bloqueada nas suas regras. Altere em Controle e regras para usá-la.')

    def describe(self):
        return {'policy': self.current().model_dump(), 'capability_tools': CAPABILITY,
            'boundaries': [
                {'source':'Aplicativo', 'text':'Nenhum filtro adicional por assunto. Suas regras de conversa entram no prompt; instruções de operação e a personalidade efetiva ficam visíveis aqui.'},
                {'source':'Modelo', 'text':'O modelo instalado tem comportamentos aprendidos. Regras do aplicativo não reescrevem seus pesos nem garantem respostas sem recusas.'},
                {'source':'Autorização', 'text':'Observação não executa. No modo 3, permitir automaticamente atua nos escopos autorizados. No modo 4 (acesso total) tudo que não estiver bloqueado executa sem aprovação, exceto comandos do PowerShell, que sempre pedem aprovação no cartão. Nenhum modo amplia os direitos do usuário Windows.'},
                {'source':'Implementação atual', 'text':'Comandos do PowerShell rodam como seu usuário, sem administrador, e só depois de aprovados no cartão. Credenciais/AppData/sistema ficam fora das ferramentas de arquivos; fora do acesso total, gravação no perfil exige confirmação nativa adicional. Heurística de credenciais evita salvar/expor segredos conhecidos.'},
                {'source':'Navegador', 'text':'Navegador ALT: janela isolada, HTTPS público, sem câmera/microfone nem downloads. No acesso total, sites também abrem no seu navegador padrão e as janelas dele podem ser lidas e controladas. Conteúdo de sites pode estar incorreto ou tentar enganar o modelo; STOP corta tudo.'},
                {'source':'Serviços externos', 'text':'Codex/Claude e sites mantêm regras próprias. Envio à nuvem continua exigindo prévia e consentimento; API paga não é ativada automaticamente.'},
            ]}
