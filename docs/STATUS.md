# Estado atual e próximos passos — ALT-AI

**Checkpoint mais recente — 30/10/2026:** **0.5.2 publicada como prévia** (tag `v0.5.2` no commit `2b7d3dd`), com instalador, manifesto assinado e feed conferidos; ver [RELEASE-0.5.2.md](RELEASE-0.5.2.md). Em `main` seguem as etapas 2 (cartões legíveis) e 3 (contexto em todas as rodadas) do plano Drael, ainda sem release. O dono decidiu **manter local no PC por enquanto**; ordem de trabalho em [PENDENCIAS-LOCAL.md](PENDENCIAS-LOCAL.md). A seção abaixo descreve a 0.5.1, preservada.

**Entrega atual:** a 0.5.1 foi publicada como prévia, com instalador, manifesto e hashes conferidos. Resolve a falsa contagem do Automático, limita dados auxiliares, reserva ferramentas formatadas e adiciona ação direta para Bloco de Notas/Calculadora, sem carregar LLM. Inclui [Hermes 3 3B/8B](HERMES.md), sem baixar pesos por escolha do dono, e encerramento seguro dos trabalhadores/banco. Suíte: 233 testes Python/5 Node passaram, 1 ignorado; renderer, build e backend empacotado passaram. Ver [validação da release](RELEASE-0.5.1.md) e [detalhes da correção](CHAT_CONTEXT_0.5.1.md). Não foi instalada sobre o aplicativo aberto.

Atualizado em **30/10/2026**, após conferir o Git e a release neste notebook. As evidências funcionais do PC principal estão em [CHECKPOINT-0.5.md](CHECKPOINT-0.5.md); não foram repetidas nesta rodada de assinatura/documentação.

## Versão atual e distribuição

| Item | Estado confirmado |
| --- | --- |
| Código publicado | Última release instalável: **[0.5.2](RELEASE-0.5.2.md)**, commit `2b7d3dd`, instalador 219.533.280 bytes, SHA256 `8dbb2611…0ca6`. A 0.5.1 (`750e2a0`) continua publicada. |
| Trabalhos anteriores | 0.4.0/0.4.1, 0.4.2 e `work/0.5` já integrados em `main`. As branches anteriores são referências históricas. |
| Release | [v0.5.1 publicada como prévia](https://github.com/caio306santana/ALT-/releases/tag/v0.5.1), não é rascunho. |
| Instalador | `ALT-AI-Setup-0.5.1-x64.exe`, **219.521.408 bytes**, rebuild final após Hermes/ações diretas; backend empacotado validado em banco temporário. |
| SHA256 do instalador | `3aaf630aacd05d722ca008fc045d2ec006488ad6248fe0c154f604d927434092`, igual ao digest do asset no GitHub. |
| Manifesto de atualização | `ALT-AI-0.5.1-update.json` assinado com a chave original, verificado após baixar o manifesto público, junto com `SHA256SUMS.txt`. A chave privada permanece fora do Git e dos assets. |
| Feed da 0.5 | Repositório atualmente público, por estado encontrado nesta retomada. A API de releases respondeu sem autenticação. O código da 0.5 lista releases publicadas, incluindo prévias, e verifica o manifesto/instalador antes de instalar. Nenhuma visibilidade foi alterada nesta rodada. |
| Assinatura Windows | Authenticode continua pendente. O manifesto Ed25519 é a identidade da atualização do projeto; não substitui confiança/assinatura exigida pelo Windows. |
| Instalação neste notebook | Não foi executada nesta rodada. A versão do código não determina qual versão do aplicativo está aberta/instalada. |
| Base anterior | A release 0.5.0, tag `e84df62`, instalador de 216.270.399 bytes e manifesto permanecem inalterados. |

## O que foi implementado e registrado no PC principal

**Incluído na 0.5.1, neste notebook:** estudo do [Drael como referência](DRAEL_REVIEW.md), com análise pública estática e limites registrados. A busca distingue uma consulta válida sem resultados de uma falha técnica. As demais sugestões do estudo continuam propostas, não recursos entregues.

- **Tarefas e ferramentas:** execução em várias ações, verificações de resultado, reparo de escolha de ferramenta, aplicativos/janelas, tela, volume/brilho/música, lembretes e desfazer operações suportadas.
- **Permissões:** decisões persistentes para programas/sites/pastas; conversas protegidas e revisão de ações críticas. Cartões críticos têm prazo de 90 s; isso é específico da revisão crítica da 0.5, diferente das propostas comuns sem prazo introduzidas na 0.3.1.
- **Chat e memória:** anexos de imagem/PDF com OCR/Word/texto, busca semântica/documentos/projetos, sugestões revisadas de memória e resultados de ferramentas retornando ao modelo na mesma resposta, até quatro rodadas.
- **Voz:** Whisper, voz Dora pt-BR local, Ctrl+Espaço, detecção "Hey Jarvis" e "Ei ALT" experimental; pausa do microfone durante a fala.
- **Proatividade:** resumo da manhã, rotinas, tópicos, alertas e início de conversa conforme configuração.
- **Modelo automático/desempenho:** escolha 4B/9B/Claude conforme complexidade e consentimento, Game Mode, monitoramento de GPU, reaproveitamento do prompt, pré-carga e envio de texto à interface em lotes.
- **iPhone:** gateway, pareamento por QR de uso único e PWA; precisa concluir configuração do Tailscale e teste real entre os aparelhos.

O checkpoint registra testes automatizados, testes reais de ferramentas no PC principal e **16/16 casos do smoke Qwen 3.5 4B** em [full-access-smoke-stable.json](full-access-smoke-stable.json). Esse relatório é `dry_run`: avalia a escolha/proposta de ferramentas, sem executar as ações do lote. As execuções reais separadas estão descritas no checkpoint. Testes anteriores do notebook e limites de qualidade estão preservados no [histórico da 0.4](history/STATUS-0.4.md).

## Pendências reais

As melhorias inspiradas no Drael têm um [plano de ação próprio](PLANO-ACAO-DRAEL.md), preparado em 30/10/2026: capacidades, cartões, continuidade/contexto, modos rápido/aprofundado, catálogo de ferramentas, execução isolada e cofre opcional. São etapas planejadas; este registro não representa implementação dessas entregas.

| Pendência | Próxima ação / condição para concluir |
| --- | --- |
| GPU do PC principal | Depois de reiniciar o PC em momento apropriado, repetir `scripts/benchmark_latency.py --cases long` e comparar com [LATENCY-0.5.md](LATENCY-0.5.md). O checkpoint relata queda de ~57 para ~4,5 tok/s após eventos do driver; não há nova medição desse PC neste notebook. |
| Microfone | Conectar/ativar uma entrada funcional no PC principal: microfone físico ou WO Mic com o app conectado. Testar escuta e interrupção de ponta a ponta. |
| iPhone | Instalar/configurar Tailscale no PC principal e no iPhone, parear e testar chat, áudio, foto e cartões. Seguir [IPHONE.md](IPHONE.md). Não executado nesta rodada. |
| Authenticode | Configurar certificado/serviço de assinatura confiável para os executáveis Windows, se necessário pela política de destino. Nenhum certificado foi comprado/configurado e nenhuma proteção foi alterada. |
| Hermes real | O dono escolheu baixar depois. Instalar a variante escolhida em Inteligências, então avaliar português, personalidade, chamadas de ferramenta e latência. Nesta entrega houve validação de integração/tokenização, sem inferência Hermes real. |
| Bloco de Notas real | O caminho direto passou por testes de autorização/contrato com execução simulada; falta confirmar uma janela real após instalar. O helper Computer Use estava indisponível nesta sessão, erro 2; nenhum documento do dono foi tocado. |
| Interface real | Abrir a 0.5.1 e percorrer os fluxos na janela: chat, cartões, configurações, memória/documentos, tarefas, voz, rotinas e pareamento. Testes automatizados/API não substituem essa revisão manual. |
| Janelas e tarefas | Testar com mais aplicativos reais e repetir tarefa planejada pelo Qwen em uma janela, com texto/alvo corretos, pausa/retomada e verificação de resultado. |
| Documentos | Validar PDFs longos, PDFs digitalizados e DOCX reais. OCR foi implementado na 0.5; qualidade e limites nesses documentos ainda precisam de validação. |
| Personalidade e exatidão | Avaliar o tom em uso real e manter verificação de fontes e contas, especialmente contas expressas em prosa. O smoke não garante ausência de erros ou recusas do modelo. |
| Instalação/atualização no destino | Confirmar versão em Sobre e testar atualização preservando dados/backup. Não afirmar que o aplicativo aberto neste notebook mudou apenas porque houve `git pull` ou assinatura do manifesto. |

## Retomada em qualquer PC

Continuar em **`main`**, fazendo `git status` antes de `git pull --ff-only`, sem descartar alterações locais. Preparação do ambiente no [README](../README.md#desenvolver-no-outro-pc). Não usar pastas antigas de instaladores como fonte; os assets atuais ficam na release e downloads locais podem ficar em `release/` (ignorada pelo Git).

Para versões antigas cujo aviso ainda consulta `/releases/latest`, uma prévia pode não aparecer. A 0.5 já usa a lista de releases; o feed público foi conferido oferecendo a 0.5.1 para a 0.5.0 e nenhuma versão nova para a própria 0.5.1. Se necessário, baixar a 0.5.1 pela página da release. O instalador não foi executado nesta rodada.

Conversas, bancos, documentos pessoais, áudio, modelos, credenciais e `.local/update-private-key.pem` ficam fora do Git. A chave original precisa de backup privado para assinar futuras releases em outro PC; não trocar a identidade pública para contornar sua ausência. Não há medição confiável dos créditos do agente: registrar checkpoints sem inventar percentuais.
