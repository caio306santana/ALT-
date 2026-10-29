# ALT-AI — trabalho em andamento

Checkpoint de 29/10/2026. A versão publicada continua sendo 0.3.0.

## Prioridade atual: erro de contexto e fluidez do chat

O cálculo anterior usava bytes UTF-8 como limite conservador de tokens. Isso pode recusar mensagens comuns em português que cabem no Qwen. Está em implementação a contagem pelo tokenizer oficial Qwen 3.5, com hash/proveniência fixos, indicador antes do envio e recuperação do rascunho quando o backend recusa a mensagem. O seletor de aprovação dentro do chat e ajustes de leitura também foram solicitados.

## Etapas solicitadas pelo usuário

| Etapa | Estado neste checkpoint | O que falta |
| --- | --- | --- |
| 2 — tarefas com várias ações | Em desenvolvimento | Integrar TaskManager à API/UI; testar pausa, retomada e revisão das ações. |
| 3 — memória semântica/documentos/projetos | Em desenvolvimento | EmbeddingGemma baixado com autorização; integrar Knowledge, importação nativa, indexação e revisão de resumos; validar busca real. |
| 4 — interação com controles Windows | Em desenvolvimento | Driver UI Automation escrito; integrar seleção/autorização nativa e painel; testar com janela própria. |
| 5 — confiabilidade/persona | Parcial | Ajuste do prompt para atender primeiro ao pedido concreto; falta validação de cálculos/fontes e testes da experiência final. |
| 6 — distribuição/backup/migrações | Em desenvolvimento | Módulos de backup e migração escritos; falta integração e validação, feed de atualização e novo pacote. Certificado Authenticode depende de aquisição/configuração pelo dono. |

O usuário informou que não tem certificado de assinatura Windows e autorizou concluir os demais itens deixando essa dependência explícita. Não comprar certificado nem afirmar que o instalador tem assinatura Authenticode.

Os novos módulos ainda não integrados não representam etapas concluídas. Manter fontes no Git para continuidade em outro PC. Bancos, modelos, chaves privadas, credenciais e logs continuam fora do repositório.
