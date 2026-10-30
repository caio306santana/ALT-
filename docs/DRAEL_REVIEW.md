# Drael como referência para a ALT

**Atualização da entrega:** a distinção entre pesquisa vazia e erro técnico abaixo já está no instalador **0.5.1**. As observações sobre “posterior à 0.5.0” descrevem o momento do estudo original. O [plano de ação atual](PLANO-ACAO-DRAEL.md) separa o que foi entregue das melhorias futuras, com dependências e critérios de conclusão.

Análise em 30/10/2026 da página solicitada, `https://drael.sh/pt`, da documentação oficial e dos arquivos públicos que `/pt` e `/chat` carregam. Objetivo: identificar melhorias para a ALT, preservando sua identidade e o processamento local.

## Escopo e confiança

- **Observado:** páginas/documentação obtidas por GET sem autenticação; dois bundles JavaScript e dois CSS ligados explicitamente por essas páginas. Inventário com URLs, tamanhos e SHA256 em [drael-public-inventory.json](reference/drael-public-inventory.json).
- **Estático:** referências a raciocínio por pedido, limite de contexto, retomada/regeneração de stream e armazenamento local IndexedDB/AES-GCM aparecem no bundle do chat. Isso demonstra código publicado, não execução ou eficácia dessas funções.
- **REA parcial:** a análise atingiu o prazo de 10 s, preservando evidência. Resumo: 5 arquivos relevantes, 1 JavaScript analisado, 62 findings; cobertura de aplicação e semântica **parcial**, com 5/24 desconhecidos. Parent: `ev_b3793f91c5b12634d715f7a048d3572cf72d15dd7b293a9b886fbf257d8ad58e`; resumo: `ev_b75d1f83e4f71b335f14206d35a70d0530952707e37d0db5c5850196f60b1d9b`.
- **Não observado:** operação real do chat pago, backend privado, pesos, infraestrutura de isolamento, cifragem no servidor ou desempenho. A abertura de navegador isolado com depuração foi rejeitada pela revisão automática (`blocked by policy`); nenhuma aprovação/proteção foi contornada.

Os bundles de terceiros ficaram somente em `.local/` para inspeção inerte; não foram incorporados à ALT. Não foi criada conta, executado instalador/script do Drael ou feita chamada paga. A identidade `drael-v1` não revela qual modelo/pesos estão por trás dela.

## Comparação e propostas

| Referência observada/documentada | Estado da ALT 0.5 | Decisão para a ALT |
| --- | --- | --- |
| Capacidades e limites declarados pelo modelo [D1, D3] | `Ollama.capabilities()` já consulta capacidades, mas o seletor usa principalmente tags e o contexto vem do perfil. | Expandir metadados visíveis: imagem, ferramentas, contexto ativo e raciocínio, deixando desconhecido quando o provedor não informar. Evitar controles que o motor não suporta. |
| Raciocínio por pedido e canal separado [D2] | Qwen usa `think:false` fixo em `backend/providers/ollama.py`. | Propor modo rápido/aprofundado explícito, somente quando suportado, com orçamento/latência visíveis. Não copiar a decisão do Drael de ignorar limites de saída em certos pedidos. |
| Catálogo compacto e retirada de ferramentas na última rodada [D4] | Catálogo estável da ALT foi medido no PC principal; `backend/api.py` já limita rodadas e retira ferramentas no final. | Manter o que já funciona. Comparar tamanhos de catálogo com os mesmos casos/latência antes de mudar; seis ferramentas de um produto web não equivalem a todas as ações Windows da ALT. |
| Resultado vazio separado de falha técnica [D4] | Busca válida sem fontes virava `ValueError`, igual a indisponibilidade. | **Implementado nesta rodada:** resposta com `ok`, `found` e lista vazia; erro técnico continua erro. HTML de bloqueio/estrutura inválida não vira “nada encontrado”. |
| Código em ambiente isolado, com rede por execução [D4] | `run_command` executa no Windows do usuário, com cartão, timeout e STOP. | Projetar uma ferramenta opcional de execução isolada para código gerado. Não apresentar PowerShell como sandbox. Depende de ambiente apropriado, testes de isolamento e decisão sobre dependências. |
| Arquivos/resultados vinculados à conversa [D2] | ALT já tem anexos, projetos e histórico de ações, mas resultados extensos ainda podem virar JSON no chat. | Evoluir cartões de artefatos: arquivo gerado, saída/erro, fontes, duração e ação de abrir/exportar; priorizar resumo legível e detalhes sob demanda. |
| Armazenamento local cifrado declarado e primitivas no bundle [D5] | SQLite local da ALT não é cifrado; cofre de credenciais usa proteção separada. | Estudar cofre opcional de conversas/documentos com migração, recuperação e backup. Não prometer proteção apenas por adicionar uma chamada AES. |

## Ajuste já aplicado à ALT

Em `backend/tools/research.py`, pesquisa RSS válida sem fontes utilizáveis agora termina como observação concluída, com `found:false`. A resposta informa que isso não prova ausência da informação. Respostas inválidas/HTML de bloqueio e falhas de rede continuam falhas, sem fontes inventadas. O histórico de ações preserva a distinção; permissões e execução automática não foram ampliadas.

**Este ajuste é posterior ao instalador 0.5.0 da tag `e84df62`.** O instalador assinado nesta rodada não foi recompilado e não contém essa alteração. Validação: **36 testes passaram** em `tests/test_research_results.py`, `tests/test_agent_web.py` e `tests/test_context.py`, com NumPy 2.5.4 conforme o lock. Cobrem busca vazia, erro de transporte, XML/HTML inválido, fontes utilizáveis, histórico de ação, permissões e contexto. Nenhum dado do usuário foi enviado para avaliar a alteração; não foi repetida a suíte inteira da 0.5 nem feita uma medição real do modelo para esse ajuste.

## O que não dá para concluir

A promessa comercial de ausência de recusas não é demonstração técnica. Os termos mencionam restrições próprias [D6]. Há também descrições divergentes sobre visão nativa versus transcrição de imagens e sobre provedores em algumas páginas [D1, D2, D4, D5]; essas diferenças impedem inferir a arquitetura interna como fato. O site não disponibilizou os pesos nem demonstrou que usa Qwen. Não há base para prometer que a ALT terá o mesmo comportamento apenas copiando um prompt.

## Prioridade seguinte

1. Mostrar capacidades/orçamento reais do motor no chat e melhorar cartões de resultados/artefatos.
2. Medir modo rápido/aprofundado e tamanho do catálogo no hardware principal recuperado.
3. Planejar execução isolada e cofre local com testes próprios, sem misturar essas propostas com funcionalidades entregues.

## Fontes primárias

- **D1:** [Quickstart](https://drael.sh/docs/quickstart).
- **D2:** [Chat completions](https://drael.sh/docs/chat).
- **D3:** [Limits](https://drael.sh/docs/limits).
- **D4:** [Tools](https://drael.sh/docs/tools).
- **D5:** [Privacidade](https://drael.sh/pt/legal/privacy).
- **D6:** [Termos](https://drael.sh/pt/legal/terms).
- Página solicitada: [Drael em português](https://drael.sh/pt); erros: [Errors](https://drael.sh/docs/errors).

Fontes descrevem o produto do Drael. A coluna sobre ALT foi conferida no repositório; propostas são decisões de projeto nossas, não afirmações sobre comportamento interno do Drael.
