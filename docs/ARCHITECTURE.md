# Arquitetura e plano de entrega

Desktop Electron executa um backend local com token aleatório de 256 bits por sessão e porta efêmera em 127.0.0.1. O token fica no processo principal/preload de transporte; o React não recebe credenciais nem acesso a Node/arquivos. A ponte IPC valida o frame principal, o documento local e uma lista fechada de métodos/rotas. Streaming usa eventos identificados por operação.

FastAPI valida entradas Pydantic, origem, host e autorização. O adaptador Ollama usa endpoint fixo em loopback, não segue proxies de ambiente, não aceita URLs fornecidas por prompts e não habilita ferramentas de sistema ou provedores de nuvem. O seletor exclui aliases remotos/cloud reportados pelo Ollama.

SQLite usa WAL, chaves estrangeiras e parâmetros SQL. Conversas e mensagens possuem IDs UUID; mensagem inclui modelo, estado e métricas. As gerações fazem checkpoints em disco aproximadamente a cada 500 ms. Um encerramento abrupto pode perder o último trecho ainda não checkpointado; a próxima inicialização marca mensagens inacabadas como interrompidas. Histórico completo permanece salvo; contexto usa apenas mensagens completas da conversa corrente, limitado conservadoramente em caracteres com aviso de truncamento.

O motor de permissões só permite observação. Níveis 2–4 são apresentados como futuros. STOP é uma trava de sessão que sinaliza cancelamento de chamadas em andamento, inclusive durante conexão/carregamento. Não há executor de shell por modelo. Downloads são restritos a duas tags Qwen e iniciados pelo usuário após confirmação.

Distribuição: React compilado pelo Vite; FastAPI empacotado por PyInstaller; ambos incluídos no instalador NSIS do electron-builder. Ollama e modelos são dependências externas detectadas e instaladas/baixadas em fluxo explícito. O repositório contém fontes, locks, testes e documentação; artefatos grandes pertencem às releases.

## Riscos e decisões

- Aceleração AMD depende do driver/backend real. A documentação do Ollama lista RX 7600 para Windows com pilha compatível, mas isso não valida o PC de destino. Confirmar com `/api/ps` e logs, sem alterar drivers automaticamente. [Hardware Ollama](https://docs.ollama.com/gpu).
- Perfil desktop: 8K de contexto, saída até 4096 e keep-alive 5 minutos. Perfil notebook: 4K, saída até 768, no máximo 4 threads e keep-alive 2 minutos. Automático considera bateria, RAM e núcleos físicos; o usuário pode escolher manualmente. Esses limites não são a capacidade máxima declarada pelo modelo.
- Só o Qwen 3.5 usa `think:false` por padrão no MVP para evitar longos silêncios de raciocínio em chat curto. Outros modelos usam seus padrões. [Contrato de chat](https://docs.ollama.com/api/chat).
- Não assumir créditos genéricos de API por existir assinatura. Codex SDK automatiza tarefas de código; App Server é a via documentada para clientes personalizados com auth/histórico/aprovações/eventos. A fase 5 precisa validar esses fluxos e o plano do usuário antes de habilitar. [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk), [autenticação oficial](https://learn.chatgpt.com/docs/auth).
- Claude Code/Agent SDK precisa de investigação oficial equivalente na fase 5. Nenhum token de outro aplicativo é extraído.
- Instalador inicial não assinado; assinatura e atualizações autenticadas permanecem pendentes. Não há alegação de proteção absoluta contra malware.
- Backend local não é serviço remoto. O cliente iOS exigirá uma camada própria de identidade/TLS/VPN, sem reusar diretamente o token efêmero do desktop.
