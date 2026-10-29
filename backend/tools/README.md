# Ferramentas — 0.2

Implementação em service.py, intenções/esquema Ollama em chat_tools.py e pesquisa pública em research.py. Todas as entradas têm esquema Pydantic; ações criam propostas e geram resultado estruturado/auditoria.

Conversas podem propor cálculo, listagem/leitura/gravação texto, pastas, Notepad/Calculadora, URLs HTTPS, busca e leitura pública. Modos 3/4 podem executar somente cálculo/leitura dentro do escopo concedido sem novo clique. Consultas externas, aberturas e gravações continuam supervisionadas. Autorizações persistem sem prazo até alteração/revogação; STOP e Modo Jogo revogam também o estado salvo. Perfil amplo tem confirmação nativa e gravação crítica com confirmação adicional. Propostas mantêm validade de cinco minutos. Não há shell arbitrário, execução de downloads ou GUI genérica.

Leia docs/SECURITY.md e os testes de escopo/replay/consentimento/SSRF antes de adicionar ferramentas. Resultado externo não é autorização; nenhum provedor pode aumentar permissões por texto. Mais apps, fechamento com proteção de documentos, mouse/teclado, lembretes e tarefas estruturadas ainda estão no roadmap.
