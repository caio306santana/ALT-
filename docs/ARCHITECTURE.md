# Arquitetura — ALT-AI 0.3

## Identidade e motores

ALT-AI é a camada própria de identidade, memória, interface, permissões e ferramentas. Qwen é o modelo de terceiros servido por Ollama; Codex é um adaptador oficial opcional de assinatura; Anthropic API é opcional e paga. Nenhum peso exclusivo foi treinado. `backend/personality.py` constrói a personalidade comum e separa estilo de regras de execução.

## Processos e dados

Electron principal inicia FastAPI em porta efêmera 127.0.0.1 com token aleatório por sessão. React usa preload limitado, sem Node/arquivos/credenciais. IPC confere frame/documento e métodos/rotas. Escopos, cofre, modos 3/4 e confirmações críticas são mediados por canais nativos, não pelo proxy genérico.

SQLite WAL guarda conversas, mensagens/estado/métricas, configurações, memórias, auditoria, propostas/resultados de ferramentas, associação de ações à conversa, escopos, temas e custos estimados. Credencial API fica fora do banco, cifrada por DPAPI. Chave de assinatura de release fica fora do Git. Recuperação marca respostas inacabadas e propostas antigas como interrompidas.

Contexto inclui personalidade, trecho da conversa corrente e memórias escolhidas/recuperadas conforme política. Limites conservadores usam bytes UTF-8, overhead e esquema de ferramentas. Entradas excessivas são recusadas, sem cortar instruções pessoais ou memórias explícitas silenciosamente. `backend/context.py` ajusta resultados ao espaço restante: JSON válido, fontes com URLs inteiras, trechos de páginas/arquivos e aviso de abreviação. O resultado completo permanece no cartão/banco. A prévia de nuvem mostra o trecho exato que será enviado; recibo vincula esse conteúdo. Não há busca semântica ou extração silenciosa; resumos locais são rascunhos revisados. Dados pessoais não são lidos para compor contexto por padrão.

## Ferramentas no chat

Policy guarda regras do dono e decisões por capacidade em settings.owner_policy. Rotas de escrita não estão no IPC genérico. Continuity usa biblioteca de memórias, geração local revisada, procedência e busca por termos; Evaluations executa casos sintéticos sequenciais e persiste respostas/métricas/notas humanas. Ambos usam cancelamento de PermissionEngine.

DesktopBridge é uma fila autenticada: execução de ferramenta aguarda, Electron main busca o job, confirma que ainda está ativo, realiza operação limitada em ResearchBrowser e devolve resultado. Job expira e só aceita uma resposta; STOP invalida espera. Páginas não recebem acesso ao backend. A sessão de pesquisa usa proxy CONNECT com validação DNS/IP público e túnel TLS, mundo isolado para scripts fixos e snapshots de DOM para interações. Não há execução de JavaScript fornecido pelo modelo.

Programas cadastrados têm caminho/hash na tabela programs; só abrir sem argumentos e fechar normalmente processos rastreados. O banco também recebe evaluations e memory_sources. Não há alteração destrutiva do esquema anterior.

`tools/chat_tools.py` declara uma função Ollama validada por Pydantic para intenções relevantes, evitando enviar todas as ferramentas em uma conversa comum. Capacidades bloqueadas não são declaradas. Tool calls criam propostas, jamais autorização. O backend emite cartões com ID, prévia e estado. Modo 3/4 permite leitura/cálculo no escopo concedido por padrão; outras capacidades seguem Policy e podem pedir revisão ou ter permissão automática explícita. Gravação no perfil amplo exige confirmação nativa adicional; fechamento de apps mantém revisão. Resultado pode ser analisado pelo modelo por ID ligado à conversa; ir para nuvem ainda exige prévia e consentimento.

Ferramentas: calcular AST restrita; listar/ler/gravar texto; abrir pasta; iniciar Notepad/Calculadora; abrir HTTPS; buscar Bing RSS e ler páginas HTTPS públicas. Não existe shell arbitrário, automação ampla de mouse/teclado, execução de downloads ou alteração administrativa.

Pesquisa resolve DNS, rejeita IPs não públicos e conecta ao IP validado com SNI/TLS do hostname. Cada redirecionamento é validado; há limites de bytes, tempo e tipo. Não usa cookies, sessão do navegador, proxy de ambiente ou JavaScript. Fontes e texto são dados não confiáveis.

## Nuvem e custos

Prévia exata gera recibo de uso único, expira em cinco minutos e vincula provedor/contexto/configuração. Mudanças invalidam a autorização. STOP invalida recibos e revoga sessões. Não há fallback pago automático.

Codex executa CLI oficial, exige ChatGPT por forced_login_method, remove chaves de ambiente e desliga configurações pessoais/rules/hooks/plugins/memórias/apps/shell/browser/computer. Perfil de permissões nega por padrão, libera somente scratch/minimal read e não libera rede a ferramentas. Falhas não ativam acesso irrestrito. Stream mostra mensagens confirmadas; este CLI entrega texto por mensagem, não necessariamente token a token. [SDK](https://learn.chatgpt.com/docs/codex-sdk), [configuração](https://learn.chatgpt.com/docs/config-file/config-reference), [permissões](https://learn.chatgpt.com/docs/permissions).

Claude por assinatura permanece bloqueado na integração sem aprovação Anthropic. API usa cofre, verificação de chave/modelos, preços e orçamento. Reserva estimada ocorre antes de pedido; falha/cancelamento sem uso final preserva reserva como estimativa. Não inventar saldo/renovação. [Regra oficial](https://code.claude.com/docs/en/agent-sdk/overview).

## Desempenho e distribuição

Perfil Notebook: 4K contexto, saída até 768, até quatro threads, keep-alive 2m. Desktop: 8K/até4096/5m. Saída pode ser reduzida para caber no contexto. Automático usa bateria, RAM e núcleos físicos; usuário pode escolher. Hardware/driver do PC principal ainda precisa de teste real, sem presumir VRAM pelo tamanho do modelo.

GAME MODE suspende ações, revoga permissões, tenta descarregar o modelo selecionado e oculta a janela; o app informa se a descarga foi confirmada. Não promete liberação total de RAM/VRAM. Requisição de descarga pode afetar outros apps usando o mesmo modelo, por isso há diálogo explícito.

Vite + PyInstaller + NSIS geram aplicativo sem exigir Python/Node no PC de uso. Fuses restringem Electron de produção e validam ASAR. Manifesto Ed25519 e SHA256 permitem atualização local verificada, rejeitando adulteração e rollback antes de executar instalador. Não há feed automático. Pipeline Authenticode existe, mas depende de certificado externo não configurado.

Cliente iOS, voz, automação GUI ampla, mais apps, resumos/memória semântica e atualização automática autenticada continuam no roadmap. Contratos e tokens visuais são separados para evolução posterior.
