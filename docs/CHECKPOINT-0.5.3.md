# Checkpoint 0.5.3 — etapas 2 e 3 do plano Drael

30/10/2026, no notebook. A 0.5.2 foi publicada antes, a partir do commit limpo `2b7d3dd` ([RELEASE-0.5.2.md](RELEASE-0.5.2.md)). Esta rodada implementou as **etapas 2 e 3** do [plano Drael](PLANO-ACAO-DRAEL.md), seguindo a ordem de [PENDENCIAS-LOCAL.md](PENDENCIAS-LOCAL.md).

## Etapa 2 — cartões legíveis (implementado e testado)

- **Selo do cartão segue o que a ferramenta observou:** Concluído, Não confirmado, Falhou, Precisa de escolha, Em andamento e "Sem resultados" para pesquisa vazia. Estados de proposta aparecem em português. Nenhum cartão diz mais "CONFIRMADO" para um resultado que não foi confirmado.
- **Pesquisa:** lista de fontes com título, domínio e trecho. **Leitura de página:** título, URL, data e aviso de corte. **Comando:** código de saída e saída. O JSON bruto fica em "Dados técnicos".
- **Arquivo gravado ou baixado:** botões **Mostrar na pasta** e **Exportar cópia**. O caminho e os links vêm da ação salva, por rotas do backend que não estão na lista de rotas do renderer. O processo principal confere e nunca executa o arquivo. Um link de fonte só abre se veio daquela pesquisa.
- **Cartões críticos** informam o prazo de 90 s. Na prática, isso só ocorre fora do Acesso total.
- **Testes:** API (arquivo, fontes e recusas) e renderer sintético com todos os selos, cliques e janela de 460 px. As capturas foram inspecionadas.

## Etapa 3 — contexto em todas as rodadas e continuidade (implementado e testado)

- **`fit_round` antes de cada chamada ao modelo,** inclusive nas rodadas de pesquisa, leitura, captura e correção. A ordem de corte:
  1. reduz os resultados antigos de ferramenta da própria resposta;
  2. tira o histórico antigo;
  3. por último, reduz o resultado mais novo.

  O prompt do sistema e a mensagem do dono nunca saem, e o `num_predict` acompanha o espaço que sobra. Se mesmo assim não couber, a resposta termina com orientação clara, e o que foi obtido continua nos cartões.
- **Resumo de continuidade** (`backend/memory/summaries.py`) para as mensagens que não cabem mais no contexto:
  - gerado em segundo plano só depois de 60 s sem resposta em andamento, e cancelado quando outra resposta começa;
  - guardado separado das memórias e rotulado como texto derivado, que não é memória, instrução nem autorização;
  - não é gerado se as mensagens antigas tiverem segredo;
  - desligável em Controle e regras;
  - o chat avisa quando foi usado; as mensagens originais continuam salvas;
  - no corte, sobrevive ao histórico bruto (`alt_keep`).

  A tabela é criada sob demanda, como as demais extensões locais. **Desvio do plano:** não houve migração de schema, para não impedir voltar à 0.5.2.
- **Anexo longo:** você passa a ver quantos caracteres do arquivo o modelo leu. O aviso do trecho manda o modelo não afirmar nada sobre a parte que não viu.

### Smoke real — conversa longa + pesquisa ([continuity-0.5.3-smoke.json](continuity-0.5.3-smoke.json))
Qwen 3.5 4B, perfil Notebook (4096), banco temporário, pesquisa pública real.

- **Resumo** das 16 mensagens antigas em 167 s, com as decisões certas (Python/FastAPI, React, "15 de dezembro"). Na primeira execução, o resumo inventou o ano "2024"; o prompt foi corrigido e a repetição saiu fiel.
- **Resposta com pesquisa:** todas as chamadas couberam (2.193 e 2.057 tokens de entrada + 940 de ferramentas + 768 de resposta). A resposta usou o resumo (FastAPI e React) e citou URLs da pesquisa.
- **Defeito encontrado e corrigido:** na primeira execução, o corte descartava o resumo antes do histórico bruto.
- **Limites observados:** o modelo pesquisou, mas não leu uma fonte, apesar do pedido; e escreveu termos técnicos errados ("WebGLSSL", "GPUCompute"). Ambos são qualidade do 4B, não orçamento.

### Smoke real — anexos longos ([documents-long-0.5.3-smoke.json](documents-long-0.5.3-smoke.json))
Arquivos sintéticos com um fato na primeira página ("AURORA-17") e outro na última ("48 mil reais"). Qwen 3.5 4B, Notebook e EmbeddingGemma.

**Anexo direto no chat:**

| Arquivo | Tamanho | Caracteres extraídos | Caracteres enviados ao modelo |
| --- | --- | --- | --- |
| PDF de 20 páginas | 26.756 bytes | 15.581 | 5.141 |
| DOCX | 37.021 bytes | 8.819 | 4.797 |

- **Cobertura informada:** nos dois casos, o aviso de quanto foi lido chegou à interface.
- **Pergunta sobre o início:** resposta certa nos dois ("AURORA-17").
- **Pergunta sobre o fim:** nenhum valor inventado.
  - Na primeira execução, o modelo afirmou que o PDF "não contém" o orçamento, quando só tinha visto o início. Isso levou ao aviso de trecho mais rígido.
  - Na repetição, o PDF ainda abre com "não contém", mas logo esclarece que a leitura foi restrita ao trecho inicial; o DOCX ressalva "nesta seção que foi carregada".
  - Conclusão: com o 4B, a ressalva melhora, mas não sai perfeita.

**Pelo Projeto:**
- Indexação em 20 trechos; a busca semântica achou a página 20.
- A resposta veio correta em 10 s: "48 mil reais", citando a página 20.
- Na primeira execução, o mesmo valor foi recuperado, mas o modelo o interpretou errado.

**Defeito do script, corrigido:** reaproveitava um anexo de outra conversa; a API recusou corretamente com "Anexe de novo".

## Validação

- **Suíte:** 254 testes Python passaram, 1 ignorado por privilégio de symlink; 5 Node passaram. Build TypeScript/Vite ok.
- **Renderer sintético:** passou, incluindo cartões e janela estreita.
- **Testes novos:**
  - `test_result_cards.py`: arquivo e fontes vindos da ação;
  - `test_context_rounds.py`: quatro resultados grandes de pesquisa no Notebook, todas as chamadas ≤ 4096, e o resumo sobrevivendo ao corte;
  - `test_continuity_summaries.py`: rótulo, segredo, desligar e cancelamento;
  - cobertura de anexo em `test_attachments.py`.

## Pacote 0.5.3 — gerado, NÃO publicado

O instalador foi gerado a partir do commit limpo `785b810` (`release/ALT-AI-Setup-0.5.3-x64.exe`, local, fora do Git).

**Bloqueio:** o `scripts/smoke_packaged.py` falhou duas vezes com **WinError 4551**. O Controle Inteligente de Aplicativos do Windows bloqueou o `alt-backend.exe` novo, que não tem assinatura. O backend da 0.5.2 passou nessa mesma checagem horas antes.

**Decisão:** nenhuma proteção do Windows foi alterada nem contornada. A release **não foi publicada**, porque um backend bloqueado deixaria quem atualizasse sem a ALT funcionando. Nenhum manifesto foi assinado para este pacote.

**Caminhos para o dono decidir:**
- assinatura Authenticode, que é a solução definitiva;
- configuração do Controle Inteligente de Aplicativos neste PC, decisão exclusiva do dono;
- testar o pacote no PC principal, se lá a proteção estiver desligada.

Depois de uma dessas opções, repetir: smoke empacotado, manifesto, release e feed.

## Não concluído / não alegar
- Revisão manual da janela instalada; teste real de abertura do Bloco de Notas/Calculadora (adiado porque o Bloco de Notas do dono estava aberto com texto não salvo).
- Perda de cache de prompt com o resumo ainda não medida. Também falta a opção de dividir o pedido quando nem a mensagem cabe.
- Fora deste notebook: PC principal, microfone e iPhone. Authenticode ausente.
