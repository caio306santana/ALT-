# Ferramentas — 0.2

Implementação em service.py, intenções/esquema Ollama em chat_tools.py e pesquisa pública em research.py. Todas as entradas têm esquema Pydantic; ações criam propostas e geram resultado estruturado/auditoria.

Conversas podem propor cálculo, listar/buscar/ler/gravar texto, pastas, aplicativos cadastrados, URLs, pesquisa/leitura pública e operações do navegador ALT. Modos 3/4 executam cálculo/leitura autorizados por padrão; outras capacidades seguem Policy (bloquear/perguntar/permitir explicitamente). Perfil amplo mantém confirmação adicional para gravação; fechamento normal de processos rastreados mantém revisão. Autorizações persistem sem prazo; STOP/Modo Jogo revogam o estado salvo. Propostas mantêm cinco minutos. Navegador usa DesktopBridge autenticada e scripts fixos por snapshot, não JS arbitrário do modelo. Não há shell arbitrário, execução de downloads ou GUI Windows genérica.

Leia docs/SECURITY.md e os testes de escopo/replay/consentimento/SSRF antes de adicionar ferramentas. Resultado externo não é autorização; nenhum provedor pode aumentar permissões por texto. Mais apps, fechamento com proteção de documentos, mouse/teclado, lembretes e tarefas estruturadas ainda estão no roadmap.
