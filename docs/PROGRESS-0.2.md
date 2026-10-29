# ALT-AI 0.2 — trabalho em andamento

Pedido de 29/10/2026: avançar personalização, memória, integrações oficiais, ferramentas Windows com permissões, desempenho e distribuição. Não incluir voz/iOS nesta rodada. Manter commits e continuidade no Git.

Personalidade aprovada: **calma na forma de falar; provocadora, irônica e desafiadora nas ideias**, questionando premissas e contradições com paciência. Identidade original, consistente entre provedores. Ajustes continuam editáveis, mas esse é o padrão aceito.

## Checkpoint de implementação

- Novos módulos backend: personalidade, biblioteca de memória CRUD/exportação/seleção explícita, recibos de consentimento de contexto de nuvem de uso único, ferramentas assistidas com escopo e aprovação individual, adaptadores Codex CLI/Anthropic API, cofre DPAPI, orçamento estimado e Game Mode.
- Personalidade aplicada ao prompt real do chat local; memórias só entram por IDs selecionados. Não presumir memória semântica ou extração automática já pronta.
- Ferramentas propostas: cálculo, listar/ler/gravar texto em pastas escolhidas, abrir pasta, Bloco de Notas/Calculadora e URLs HTTPS. Sem shell arbitrário, executáveis por caminho, exclusão ou fechamento de processos pessoais. Escritas têm diff, impressão do estado do arquivo e substituição atômica.
- Codex detectado nesta máquina via CLI oficial, autenticado com ChatGPT. Adaptador usa workspace vazio, desativa ferramentas, hooks/plugins/memórias e configuração pessoal; permissões restritas, sem executar com acesso total. Pendente teste real do fluxo e cancelamento.
- Claude por assinatura indisponível: documentação oficial do Agent SDK exige aprovação Anthropic para oferecer login/limites claude.ai em produtos terceiros. Alternativa API implementada, desligada até chave, modelo, preços e orçamento configurados explicitamente. Nunca extrair tokens de sessão ou iniciar gasto por fallback automático.
- Cofre DPAPI e API Anthropic ainda precisam de testes de contrato; nenhuma chave real recebida e nenhum pedido pago autorizado/executado.
- 14 testes anteriores passaram após primeiras alterações. Novos testes e interface dos módulos ainda pendentes neste checkpoint.

## Próximos passos imediatos

1. Interface para personalidade/temas/layout/atalhos, memória e seleção de contexto, painel de ferramentas/permissões, configurações de provedores e prévia de nuvem, Game Mode.
2. Ampliar ponte Electron com allowlists e diálogos nativos para pasta/exportação/cofre. Nunca permitir renderer escolher endpoint arbitrário, executável ou path de gravação do main process.
3. Testes novos de credenciais, expiração/replay/alteração de contexto, orçamento, scopes/traversal/junctions, escrita concorrente, STOP e Game Mode.
4. Testar Codex com um prompt sintético autorizado e chat Qwen/persona, sem transmitir conversas pessoais nos testes. Caso runtime não suporte restrições, manter indisponível em vez de degradar isolamento.
5. Atualizar versão, documentação e HANDOFF; compilar e validar pacote, publicar nova prévia privada quando pronta.

## Limites externos

Assinatura Authenticode exige certificado/serviço de assinatura que ainda não foi configurado. Preparar pipeline e verificações, sem alegar instalador assinado. Atualização automática não pode instalar binário sem validação de confiança. PC Ryzen/RX 7600 continua fora desta sessão e precisa de validação física posterior.
