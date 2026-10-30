# Estado atual e próximos passos — ALT-AI 0.5.1

**Correção atual:** o código 0.5.1 resolve a falsa contagem do Automático, limita dados auxiliares de janelas, reserva ferramentas formatadas e adiciona ação direta para Bloco de Notas/Calculadora, sem carregar LLM. Inclui catálogo [Hermes 3 3B/8B](HERMES.md), sem baixar pesos por escolha do dono, e encerramento seguro dos trabalhadores/banco. Suíte: 233 testes Python/5 Node passaram, 1 ignorado; renderer e build passaram. O pacote final ainda está em validação: ver [CHAT_CONTEXT_0.5.1.md](CHAT_CONTEXT_0.5.1.md). As informações de instalador/hash na tabela abaixo são da base 0.5.0, preservada sem alterações.

Atualizado em **30/10/2026**, após conferir o Git e a release neste notebook. As evidências funcionais do PC principal estão em [CHECKPOINT-0.5.md](CHECKPOINT-0.5.md); não foram repetidas nesta rodada de assinatura/documentação.

## Versão atual e distribuição

| Item | Estado confirmado |
| --- | --- |
| Código base publicado | Versão **0.5.0**, tag no commit `e84df62`. A correção 0.5.1 posterior não está nesse instalador. |
| Trabalhos anteriores | 0.4.0/0.4.1, 0.4.2 e `work/0.5` já integrados em `main`. As branches anteriores são referências históricas. |
| Release | [v0.5.0 publicada como prévia](https://github.com/caio306santana/ALT-/releases/tag/v0.5.0), não é rascunho. |
| Instalador | `ALT-AI-Setup-0.5.0-x64.exe`, **216.270.399 bytes**, baixado da release existente; nenhum rebuild/substituição nesta rodada. |
| SHA256 do instalador | `45fb094673c3e23d8d786f4de98fc410a88469993ebda08b4e74172b08ab6061`, conferido com o digest do asset no GitHub. |
| Manifesto de atualização | `ALT-AI-0.5.0-update.json` assinado neste notebook com a chave original, verificado pelo validador da ALT e anexado à release, junto com `SHA256SUMS.txt`. A chave privada permanece fora do Git e dos assets. |
| Feed da 0.5 | Repositório atualmente público, por estado encontrado nesta retomada. A API de releases respondeu sem autenticação. O código da 0.5 lista releases publicadas, incluindo prévias, e verifica o manifesto/instalador antes de instalar. Nenhuma visibilidade foi alterada nesta rodada. |
| Assinatura Windows | Authenticode continua pendente. O manifesto Ed25519 é a identidade da atualização do projeto; não substitui confiança/assinatura exigida pelo Windows. |
| Instalação neste notebook | Não foi executada nesta rodada. A versão do código não determina qual versão do aplicativo está aberta/instalada. |

## O que foi implementado e registrado no PC principal

**Alteração posterior à release, neste notebook:** estudo do [Drael como referência](DRAEL_REVIEW.md), com análise pública estática e limites registrados. A busca da ALT foi ajustada para distinguir uma consulta válida sem resultados de uma falha técnica. Esse ajuste está no código posterior à tag 0.5.0 e **não faz parte do instalador já publicado/assinado**; precisa entrar numa próxima distribuição.

- **Tarefas e ferramentas:** execução em várias ações, verificações de resultado, reparo de escolha de ferramenta, aplicativos/janelas, tela, volume/brilho/música, lembretes e desfazer operações suportadas.
- **Permissões:** decisões persistentes para programas/sites/pastas; conversas protegidas e revisão de ações críticas. Cartões críticos têm prazo de 90 s; isso é específico da revisão crítica da 0.5, diferente das propostas comuns sem prazo introduzidas na 0.3.1.
- **Chat e memória:** anexos de imagem/PDF com OCR/Word/texto, busca semântica/documentos/projetos, sugestões revisadas de memória e resultados de ferramentas retornando ao modelo na mesma resposta, até quatro rodadas.
- **Voz:** Whisper, voz Dora pt-BR local, Ctrl+Espaço, detecção "Hey Jarvis" e "Ei ALT" experimental; pausa do microfone durante a fala.
- **Proatividade:** resumo da manhã, rotinas, tópicos, alertas e início de conversa conforme configuração.
- **Modelo automático/desempenho:** escolha 4B/9B/Claude conforme complexidade e consentimento, Game Mode, monitoramento de GPU, reaproveitamento do prompt, pré-carga e envio de texto à interface em lotes.
- **iPhone:** gateway, pareamento por QR de uso único e PWA; precisa concluir configuração do Tailscale e teste real entre os aparelhos.

O checkpoint registra testes automatizados, testes reais de ferramentas no PC principal e **16/16 casos do smoke Qwen 3.5 4B** em [full-access-smoke-stable.json](full-access-smoke-stable.json). Esse relatório é `dry_run`: avalia a escolha/proposta de ferramentas, sem executar as ações do lote. As execuções reais separadas estão descritas no checkpoint. Testes anteriores do notebook e limites de qualidade estão preservados no [histórico da 0.4](history/STATUS-0.4.md).

## Pendências reais

| Pendência | Próxima ação / condição para concluir |
| --- | --- |
| GPU do PC principal | Depois de reiniciar o PC em momento apropriado, repetir `scripts/benchmark_latency.py --cases long` e comparar com [LATENCY-0.5.md](LATENCY-0.5.md). O checkpoint relata queda de ~57 para ~4,5 tok/s após eventos do driver; não há nova medição desse PC neste notebook. |
| Microfone | Conectar/ativar uma entrada funcional no PC principal: microfone físico ou WO Mic com o app conectado. Testar escuta e interrupção de ponta a ponta. |
| iPhone | Instalar/configurar Tailscale no PC principal e no iPhone, parear e testar chat, áudio, foto e cartões. Seguir [IPHONE.md](IPHONE.md). Não executado nesta rodada. |
| Authenticode | Configurar certificado/serviço de assinatura confiável para os executáveis Windows, se necessário pela política de destino. Nenhum certificado foi comprado/configurado e nenhuma proteção foi alterada. |
| Interface real | Abrir a 0.5 e percorrer os fluxos na janela: chat, cartões, configurações, memória/documentos, tarefas, voz, rotinas e pareamento. Testes automatizados/API não substituem essa revisão manual. |
| Janelas e tarefas | Testar com mais aplicativos reais e repetir tarefa planejada pelo Qwen em uma janela, com texto/alvo corretos, pausa/retomada e verificação de resultado. |
| Documentos | Validar PDFs longos, PDFs digitalizados e DOCX reais. OCR foi implementado na 0.5; qualidade e limites nesses documentos ainda precisam de validação. |
| Personalidade e exatidão | Avaliar o tom em uso real e manter verificação de fontes e contas, especialmente contas expressas em prosa. O smoke não garante ausência de erros ou recusas do modelo. |
| Instalação/atualização no destino | Confirmar versão em Sobre e testar atualização preservando dados/backup. Não afirmar que o aplicativo aberto neste notebook mudou apenas porque houve `git pull` ou assinatura do manifesto. |

## Retomada em qualquer PC

Continuar em **`main`**, fazendo `git status` antes de `git pull --ff-only`, sem descartar alterações locais. Preparação do ambiente no [README](../README.md#desenvolver-no-outro-pc). Não usar pastas antigas de instaladores como fonte; os assets atuais ficam na release e downloads locais podem ficar em `release/` (ignorada pelo Git).

Para versões antigas cujo aviso ainda consulta `/releases/latest`, uma prévia pode não aparecer. A 0.5 já usa a lista de releases; se a versão instalada não detectar a atualização, baixar a 0.5 pela página da release e seguir o fluxo de atualização validado. Nesta rodada o instalador foi apenas baixado para assinatura/conferência, não executado.

Conversas, bancos, documentos pessoais, áudio, modelos, credenciais e `.local/update-private-key.pem` ficam fora do Git. A chave original precisa de backup privado para assinar futuras releases em outro PC; não trocar a identidade pública para contornar sua ausência. Não há medição confiável dos créditos do agente: registrar checkpoints sem inventar percentuais.
