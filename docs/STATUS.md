# Estado atual e próximos passos — ALT-AI

Atualizado em 29/10/2026. Este é o ponto de entrada para retomar o projeto em outro PC.

## O que deu certo

O código da correção **0.3.1 está em `main`**. A implementação ainda incompleta das etapas maiores está preservada em [`work/advanced-0.4`](https://github.com/caio306santana/ALT-/tree/work/advanced-0.4). Não confundir código em desenvolvimento com funcionalidade entregue no aplicativo instalado.

| Entrega | Estado e evidência |
| --- | --- |
| Contagem de contexto Qwen 3.5/Huihui | Feita no código. Usa tokenizer oficial local, com hash e licença; mensagem comum não é mais contada como bytes/tokens. |
| Conferência antes do envio | Feita. Mostra uso de contexto, preserva o rascunho quando o envio é recusado e mantém o histórico completo salvo. |
| Propostas sem prazo | Feitas para propostas novas. Pesquisa/cálculo e ações independentes de snapshots podem sobreviver ao reinício. STOP, recusa, regras e validação do alvo continuam valendo. |
| Interface do chat | Feita no código. Seletor de aprovação dentro do chat, modo real visível, leitura mais limpa, caixa de mensagem que cresce e rolagem que respeita a leitura. |
| Personalidade | Ajustada para atender primeiro ao pedido concreto, mantendo o tom aprovado: calma ao falar e provocadora nas ideias. Não representa a conclusão de toda a etapa 5. |
| Testes da correção | 82 testes Python passaram, 1 ignorado por privilégio de symlink; 3 testes Node passaram; TypeScript/Vite compilou; teste do renderer com dados sintéticos passou. |
| Chat local real | Qwen 3.5 4B respondeu à mensagem de 4.757 caracteres com memória selecionada no perfil Notebook. Estimativa: 1.517 tokens; Ollama: 1.470. Resposta completa em 74,39 s neste notebook/CPU. |

Essas são as evidências da rodada de correção, não uma nova execução de todos os testes neste checkpoint de documentação. Detalhes em [CHAT_FIX_0.3.1.md](CHAT_FIX_0.3.1.md) e [chat-context-smoke.json](chat-context-smoke.json).

## Impedimento para entregar a atualização instalada

O instalador 0.3.1 foi gerado e seu manifesto Ed25519/hash foi verificado. Porém, o teste do backend empacotado foi bloqueado antes de iniciar pelo Controle de Aplicativos do Windows: **WinError 4551**, eventos Code Integrity **3033/3077**, exigência de assinatura/política de integridade.

- **Não concluído:** smoke do runtime empacotado, instalação/atualização da 0.3.1 e aplicação da correção na ALT já aberta.
- A release [0.3.1 permanece em rascunho](https://github.com/caio306santana/ALT-/releases/tag/untagged-82010de874c86b9ed2df), com instalador, manifesto e SHA256 enviados. A última release publicada continua sendo a 0.3.0.
- Nenhuma proteção do Windows foi alterada ou contornada. O usuário informou não possuir certificado e autorizou deixar essa dependência explícita; nenhum certificado foi comprado/configurado.
- Instalador: `ALT-AI-Setup-0.3.1-x64.exe`, 134.257.757 bytes. SHA256: `831f1d72d7f07792f27250442cfc0a4bde1f8d52ee769a38b93fd0a3d4aa9e85`.

## Etapas maiores: nenhuma está integralmente concluída

| Etapa solicitada | Estado | O que falta para concluir |
| --- | --- | --- |
| 2 — Tarefas com várias ações | Parcial | Integrar TaskManager à API/interface; validar planejamento, aprovação, execução, conferência do resultado, pausa e retomada sem repetir ações concluídas. |
| 3 — Memória semântica/documentos/projetos | Parcial | Integrar Knowledge, importação nativa, indexação/busca semântica e resumos revisados por projeto. EmbeddingGemma já foi baixado com autorização; busca real ainda precisa de validação. |
| 4 — Controle de janelas Windows | Parcial | Integrar driver UI Automation, seleção/autorização nativa da janela e painel; testar leitura e interação em uma janela de teste própria. Não declarar controle universal do Windows. |
| 5 — Confiabilidade e personalidade | Parcial | Concluir validação determinística de cálculos, procedência/conferência de fontes e testes da personalidade em tarefas e debates reais. |
| 6 — Distribuição, backup e atualizações | Parcial | Integrar e testar backup/restauração, migrações e feed de atualização verificado; resolver a dependência de assinatura/confiança, validar instalação/atualização e testar no PC principal. |

Os módulos dessas etapas estão na branch de desenvolvimento e ainda não foram integrados à entrega 0.3.1. A lista específica dessa branch está em [PROGRESS-0.4.md](https://github.com/caio306santana/ALT-/blob/work/advanced-0.4/docs/PROGRESS-0.4.md).

## Ordem de retomada

1. Resolver a assinatura/confiança do novo runtime conforme a política deste Windows, mantendo as proteções do sistema.
2. Executar `scripts/smoke_packaged.py` com o pacote candidato; validar instalação e atualização preservando os dados. Publicar a 0.3.1 somente depois de confirmar esses resultados.
3. Retomar `work/advanced-0.4`, trazer as correções de `main` que forem necessárias e concluir uma etapa por vez, com integração e evidência de funcionamento antes de marcar como feita.
4. Testar no notebook e no PC principal Ryzen/RX 7600; desempenho/GPU e instalação em Windows limpo continuam pendentes.

## Continuidade em outro PC

Fontes, locks, testes e documentação estão no repositório privado. O [README](../README.md#desenvolver-no-outro-pc) contém a preparação do ambiente; [HANDOFF.md](HANDOFF.md) registra decisões e histórico técnico. Para explorar o trabalho incompleto após clonar, usar `git switch --track origin/work/advanced-0.4`; isso não é a versão pronta para instalar.

Dados pessoais, bancos SQLite, logs, modelos e credenciais ficam fora do Git. Preservar a chave privada de atualização em backup privado para assinar versões futuras; ela não é incluída no repositório. Não há acesso confiável ao percentual de créditos do agente: fazer checkpoints frequentes sem inventar esse percentual.
