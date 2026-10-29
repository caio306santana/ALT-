# Correção do chat 0.3.1 — 29/10/2026

## Feito no código

- Qwen 3.5/Huihui passam a usar o tokenizer oficial local, com proveniência/revisão/hash fixos e licença Apache 2.0. Bytes UTF-8 não são tratados como tokens. Outros modelos mantêm o limite conservador anterior.
- Conferência de contexto antes do envio; indicador inclui personalidade, memórias, esquema de ferramentas e histórico efetivamente enviado. O histórico antigo fica salvo quando só a janela recente cabe. Seleções manuais não são descartadas silenciosamente.
- Erros antes da aceitação do envio preservam o rascunho. Também é preservado o texto editado enquanto a conferência está acontecendo.
- Propostas novas não vencem por tempo. Pesquisa/cálculo/ações independentes de snapshots podem continuar pendentes após reabrir a ALT. Uso único, STOP, recusa, regras, escopos e conferência de arquivo alterado continuam valendo.
- Propostas da versão antiga sem dados suficientes podem ser preparadas novamente para revisão. Isso não executa a ação. Snapshots de navegador/janelas e processos rastreados não são reaproveitados após reiniciar.
- Seletor dentro do chat: Somente conversar / Pedir aprovação / Usar minhas regras / Acesso amplo. Indica o modo real e mantém as confirmações nativas existentes para ampliar escopos.
- Chat com mensagens mais limpas, largura de leitura, caixa que cresce, configurações fechadas ao iniciar e rolagem que respeita quem está lendo mensagens anteriores.
- Personalidade atende primeiro ao pedido concreto; cumprimentos/tarefas simples não devem virar debate sobre o usuário.

## Validação

- 82 testes Python passaram; 1 teste de symlink ignorado por falta de privilégio Windows.
- 3 testes Node passaram; TypeScript/Vite compilou.
- Teste real Qwen 3.5 4B/Notebook em banco temporário: mensagem de 4.757 caracteres + memória selecionada; estimativa 1.517 tokens, Ollama informou 1.470; resposta “Entendido.” completa, em 74,39 s neste notebook/CPU. Ver `chat-context-smoke.json`. Nenhum envio à nuvem.
- Teste de interface em Electron oculto, com dados/ponte sintéticos: rascunho recuperado após erro de transporte, contexto excedido mostrado antes do envio, modo real/alteração para pedir aprovação e configurações fechadas. Capturas revisadas; não foi automação do desktop do usuário. O serviço Computer Use estava indisponível.
- NSIS gerado: `ALT-AI-Setup-0.3.1-x64.exe`, 134.257.757 bytes; SHA256 `831f1d72d7f07792f27250442cfc0a4bde1f8d52ee769a38b93fd0a3d4aa9e85`. Manifesto Ed25519 do projeto gerado; não equivale a Authenticode.

## Impedimento real do pacote

O smoke do runtime empacotado foi **bloqueado antes de iniciar**: Windows `WinError 4551`, Controle de Aplicativos. O log `Microsoft-Windows-CodeIntegrity/Operational` registrou eventos 3033 e 3077 para `alt-backend.exe`, informando exigência de assinatura/política de integridade.

Assim, o instalador não é considerado validado nem foi instalado sobre a ALT aberta. Manter a entrega como rascunho até resolver a confiança/assinatura com o responsável pela política e executar o smoke empacotado. Nenhuma proteção do Windows foi desabilitada ou contornada. O usuário não possui certificado e havia autorizado deixar essa dependência explícita.

## Continuidade

`main` recebe a correção isolada da base 0.3; a implementação ainda incompleta das etapas 2–6 fica preservada em `work/advanced-0.4`, com lista em `docs/PROGRESS-0.4.md` nessa branch. Não incluir migrações/driver UIA experimentais neste pacote de correção.

Próximos passos: resolver o impedimento de assinatura do runtime, rodar `scripts/smoke_packaged.py` e teste de instalação/atualização; depois integrar e validar tarefas de várias ações, memória semântica/documentos/projetos, UIA Windows, cálculos/fontes e backup/feed. EmbeddingGemma já foi baixado com autorização. PC principal/Windows limpo continuam sem teste.
