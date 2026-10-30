# Plano de ação — melhorias do Drael para a ALT

Preparado em **30/10/2026**. Base: ALT **0.5.1**, código funcional da tag `750e2a0` e documentação em `main` conferida em `d2d3521`. **Este documento é um plano; não implementa as etapas futuras.**

Objetivo: tornar a ALT mais útil para conversar, pesquisar e executar tarefas, com respostas e resultados claros, menor espera e continuidade entre pedidos. A identidade, personalidade e regras editáveis continuam sendo da ALT; Qwen, Huihui e Hermes são motores de terceiros.

## Referências e limites do estudo

A documentação pública do Drael descreve descoberta das capacidades do modelo, esforço de raciocínio por pedido, ferramentas com resultados estruturados, execução isolada e proteção do histórico armazenado. São referências de produto/arquitetura declaradas pelo serviço; não houve validação de sua infraestrutura privada. O estudo está em [DRAEL_REVIEW.md](DRAEL_REVIEW.md).

As decisões abaixo são propostas para a ALT. Não dependem de assinar o Drael, copiar seus bundles, descobrir seus pesos ou adotar suas decisões comerciais. Os testes precisam medir o resultado nos nossos modelos e computadores. Nenhuma garantia de velocidade, qualidade ou ausência de recusas pode ser deduzida do nome de um modelo.

Fontes primárias conferidas nesta preparação:

- [Drael — capacidades publicadas](https://drael.sh/docs/quickstart), [orçamento de contexto](https://drael.sh/docs/limits).
- [Drael — raciocínio por pedido](https://drael.sh/docs/chat), [ferramentas, resultados e execução isolada](https://drael.sh/docs/tools).
- [Drael — declaração de privacidade](https://drael.sh/pt/legal/privacy).
- [Ollama — controles de raciocínio e descoberta por modelo](https://docs.ollama.com/capabilities/thinking).
- [Microsoft — Windows Sandbox, requisitos e limites](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/).

## O que já está entregue

- [x] Pesquisa válida sem resultados é distinta de falha técnica; incluído no instalador 0.5.1.
- [x] Estimativa inicial resolve o modelo Automático e usa tokenizers Qwen/Hermes; dados auxiliares têm orçamento e o indicador discrimina componentes.
- [x] Catálogo estável/filtrado, limite de rodadas e retirada das ferramentas na rodada final já existem. Falta medir alternativas; não é preciso reconstruir isso do zero.
- [x] Ações diretas exatas para Bloco de Notas/Calculadora dispensam geração, respeitando o serviço de permissões. Falta validar a janela real.
- [x] Históricos, anexos, projetos, recuperação semântica e rascunhos de resumo já existem. Isso ainda não equivale à compactação geral de toda conversa.
- [x] Cofre de credenciais DPAPI existe; conversas, documentos, índices e backups não ganham cifragem por causa dele.
- [x] Código, instalador e manifesto 0.5.1 publicados, com testes registrados em [RELEASE-0.5.1.md](RELEASE-0.5.1.md).

Esses itens não são entregas novas deste plano. A instalação no destino, a avaliação Hermes real e os testes de hardware continuam pendentes.

## Sequência e dependências

| Etapa | Entrega | Prioridade | Esforço relativo | Depende de |
| --- | --- | --- | --- | --- |
| 0 | Validar a base e medir os dois PCs | Imediata | Médio | Instalação da 0.5.1 e acesso aos PCs |
| 1 | Mostrar capacidades e contexto reais | Alta | Médio | 0 para validar hardware; desenvolvimento pode começar antes |
| 2 | Cartões de pesquisa, ações e arquivos | Alta | Médio | Contratos de resultados existentes |
| 3 | Continuidade e orçamento em todas as rodadas | Alta | Alto | 1 e resultados estruturados da 2 |
| 4 | Modos rápido/aprofundado | Média | Médio | 0, 1 e 3 |
| 5 | Escolha de ferramentas mais eficiente | Média | Alto | 0, 2, 3 e medições da 4 |
| 6 | Executar código em ambiente isolado, opcional | Posterior | Alto | Estudo de compatibilidade + 2 e 5 |
| 7 | Cofre opcional de conversas e documentos | Posterior | Alto | Projeto de chaves, backup e migração |

Esforço relativo não é promessa de prazo. Cada etapa terá seu próprio resultado e evidência; uma dependência externa pendente deve aparecer como tal. Não marcar toda uma etapa concluída por ter criado apenas sua tela ou API.

### 0. Validar a base e estabelecer medições

**Estado: pendente de execução nos PCs.**

Entregas:

- Instalar a 0.5.1, conferir versão/dados preservados e testar abertura real do Bloco de Notas/Calculadora conforme o modo escolhido.
- Medir notebook e PC principal separadamente, registrando hardware, modelo/quantização, contexto ativo, catálogo, carga concorrente e se o modelo estava frio ou carregado.
- Repetir os mesmos pedidos de saudação, debate, pesquisa com leitura, documento e tarefa de janela. Medir pelo menos cinco repetições nas condições comparáveis, com mediana e pior caso; não tratar uma amostra isolada como benchmark.
- Avaliar Hermes somente depois do download escolhido pelo dono. A decisão atual é deixá-lo para depois; usar os modelos já instalados para iniciar a linha de base.

**Concluída quando:** instalação/dados conferidos; janelas reais observadas; relatórios separados por PC com tempos até primeiro texto, primeira ação, total, leitura do contexto, geração e RAM/VRAM quando disponíveis. Dependências de hardware/modelo que não puderem ser testadas ficam explicitamente abertas. Evidência simulada não substitui execução real.

Pontos de partida: `scripts/benchmark_latency.py`, `scripts/smoke_full_access.py`, `backend/monitoring/inference.py`, `docs/LATENCY-0.5.md`.

### 1. Capacidades reais no seletor e no chat

**Estado: planejada; parte do contador já existe.**

Entregas:

- Mostrar suporte informado para texto, imagem, ferramentas e raciocínio; informar desconhecido quando o motor não fornecer metadados.
- Distinguir máximo declarado pelo modelo, contexto ativo do perfil e espaço disponível para este envio. Um modelo suportar contexto maior não significa que ele esteja ativado ou caiba no notebook.
- Consultar metadados do Ollama, incluindo controles de raciocínio quando fornecidos; invalidar o cache após troca/atualização de modelo e lidar com versões que não exponham esses campos.
- Manter visíveis o motor escolhido pelo Automático e a execução de ação direta. Recursos ausentes devem ter explicação curta e uma alternativa adequada.
- Ajustes maiores de contexto são escolhas explícitas com uso de memória a medir; sem ampliação silenciosa de RAM/VRAM.

**Concluída quando:** Qwen, Huihui, Hermes instalado e provedor desconhecido são tratados corretamente; trocar modelo atualiza capacidades; ausência de metadados não gera capacidades inventadas; imagem não é enviada a modelo que declarou não suportá-la; indicador corresponde ao payload e ao perfil efetivos. A validação com Hermes real fica aberta se seus pesos continuarem adiados.

Código provável: `backend/providers/ollama.py`, `/models` e `/chat/estimate` em `backend/api.py`, `apps/desktop/src/App.tsx`, `packages/shared-types/index.ts`.

### 2. Resultados legíveis e arquivos úteis no chat

**Estado: planejada; cartões e estados de resultado já existem.**

Entregas:

- Pesquisa apresenta fontes, título, trecho e estado da consulta. Separar pesquisa executada de fatos verificados; fonte não consultada não recebe selo de confirmação.
- Estados visíveis: aguardando aprovação, executando, concluído, não confirmado, sem resultados, falhou e interrompido. Atualizar tanto cartões compactos quanto os que mostram detalhes.
- Corrigir o caso atual de `ChatActionCard`: um cartão não compacto com `action.state === 'complete'` recebe “CONFIRMADO”, embora o resultado ainda possa exigir outra classificação. Revisar também mensagens fixas sobre prazo de cartões críticos.
- Arquivos gerados ganham cartão com nome, tipo, tamanho, origem e botões de abrir/exportar; logs e JSON ficam em detalhes opcionais. Abertura/exportação usa referências validadas pelo aplicativo e as permissões aplicáveis.
- Execução mostra saída, erro, duração e truncamento sem exigir que o usuário interprete JSON. O resultado completo permanece no registro local.
- A análise usa apenas dados retornados e identifica links sem origem confirmada. Disponibilizar verificação por leitura da fonte conforme as autorizações.

**Concluída quando:** pesquisa vazia, falha de rede, link inventado, abertura não observada e execução interrompida têm mensagens distintas; nenhum estado de falha/não confirmação vira selo de sucesso. Arquivos abrem/exportam pelo fluxo autorizado; teste de UI cobre conteúdo extenso e janela estreita. Resultados completos e fontes continuam recuperáveis após reabrir a conversa.

Código provável: `apps/desktop/src/components/ChatActionCard.tsx`, `backend/tools/outcome.py`, `backend/tools/research.py`, `backend/verification.py`, armazenamento de ações/anexos e IPC de arquivos no Electron.

### 3. Conversas longas e contexto entre ferramentas

**Estado: planejada; a correção inicial da 0.5.1 não encerra este trabalho.**

Entregas:

- Recalcular o orçamento antes de **cada** chamada ao motor, inclusive após pesquisa, leitura de página, captura de tela e correção de ferramenta. Hoje o orçamento inicial é mais completo que o caminho das rodadas seguintes.
- Retornar resultados estruturados compactos, mantendo URLs, identificadores e marcadores de dados completos. Preservar o resultado original fora do prompt.
- Preparar resumo de continuidade quando o histórico crescer: decisões, fatos com origem, tarefas abertas e trechos relevantes. Mostrar que é resumo e permitir consultar o original; preferência de geração/uso controlada pelo dono.
- Reaproveitar os rascunhos de projeto existentes, distinguindo memória aprovada de resumo derivado da conversa. Um resumo não pode conceder permissões nem criar uma falsa memória factual.
- Preservar mensagem, regras e memórias escolhidas. Quando o pedido isolado não couber, oferecer divisão em partes/anexo indexado ou troca explícita de perfil; não apenas devolver um erro genérico nem apagar texto silenciosamente.
- Manter a parte estável do prompt entre turnos; compactar em pontos definidos e medir a perda/reutilização de cache.

**Concluída quando:** conversa extensa, PDF longo e uma sequência de quatro retornos de ferramentas permanecem dentro do contexto em todas as chamadas, ou terminam com orientação clara antes de chamar o modelo. Originais continuam salvos; decisões e identificadores relevantes são preservados nos casos de regressão; resumo não fabrica fontes/permissões; reduzir contexto não perde o rascunho.

Código provável: `backend/context.py`, `context_for` e loop de ferramentas em `backend/api.py`, `backend/memory/knowledge.py`, `backend/attachments.py`, indicador no compositor.

### 4. Modos rápido e aprofundado por pedido

**Estado: planejada.**

Entregas:

- Seletor simples **Rápido / Aprofundado**, habilitado somente quando houver suporte verificado. Explicar indisponibilidade nos demais modelos; não enviar flags Qwen ao Hermes por semelhança de nome.
- Adaptar parâmetros aos valores declarados pelo motor. Quando a versão do Ollama não publicar controles, manter comportamento atual ou usar perfil de compatibilidade validado, sem presumir suporte.
- Reservar contexto e saída para o modo escolhido; manter cancelamento e limites adequados ao hardware. Aprofundado não autoriza ações adicionais nem envia à nuvem automaticamente.
- Mostrar estado de trabalho e tempos, sem expor raciocínio interno bruto como justificativa ou prova de exatidão. Medir qualidade pelas respostas finais, ações e resultados observados.
- Pedidos diretos de abrir aplicativos continuam sem geração. A seleção do dono prevalece sobre decisões automáticas compatíveis.

**Concluída quando:** payload corresponde ao controle aceito, cancelamento funciona durante carregamento/geração, respostas não terminam vazias por consumo do orçamento e comparação repetível mede qualidade e espera. Não chamar o modo de mais rápido/aprofundado com base apenas na existência do botão; registrar limitações quando não houver ganho demonstrado.

Código provável: `backend/providers/ollama.py`, modelos de requisição, `backend/monitoring/performance.py`, `apps/desktop/src/App.tsx`, `PerformanceDetails.tsx`.

### 5. Ferramentas mais eficientes e ações confiáveis

**Estado: planejada; o catálogo estável atual é a referência a superar.**

Entregas:

- Comparar catálogo estável com grupos menores por pedido: pesquisa, aplicativos, arquivos e janelas. Não adotar o número de ferramentas do Drael sem medir o efeito nos modelos locais.
- Preservar ferramentas necessárias, esquema aceito e cache; ampliar o catálogo quando o pedido realmente precisar. Ações diretas atuais continuam pelo serviço de ferramentas.
- Normalizar os resultados das ferramentas para estado, dados, fontes, duração e truncamento, sem eliminar os detalhes próprios de cada ferramenta.
- Impedir repetições indevidas e diferenciar falha segura para tentar de novo de ação cujo resultado ficou desconhecido. Escrita, clique e envio não podem ser repetidos às cegas.
- Dar retorno de progresso, cancelar com STOP e encerrar rodadas em resposta útil com o que foi observado; sem afirmar execução por ter apenas preparado uma proposta.

**Concluída quando:** todos os casos obrigatórios de escolha/validação de ferramentas passam; nenhum caso de ação duplicada ou ampliação indevida de autorização passa a ocorrer; o catálogo candidato tem ganho medido em leitura do prompt/primeira ação sem perda nos casos críticos. Se não superar a referência, manter o estável e registrar a comparação.

Matriz sugerida: abrir aplicativo, abrir site, pesquisar e ler fonte, localizar/ler arquivo, gerar artefato, interagir com janela, falha de observação, STOP, repetição e alteração de permissão. Avaliar escolha em simulação e execução real separadamente.

Código provável: `backend/tools/chat_tools.py`, `backend/tools/service.py`, `backend/api.py`, `backend/evaluations.py`, scripts de benchmark/smoke e testes do agente.

### 6. Execução isolada de código, opcional

**Estado: planejada, com decisão de infraestrutura pendente.**

Objetivo: pedir “analise este CSV e gere um gráfico” e receber um artefato verificável com saída e erro claros.

Entregas:

- Fazer estudo de compatibilidade dos PCs e escolher um runtime separado, com isolamento real, limite de CPU/memória/processos/tempo, cancelamento e diretório por tarefa. `venv`, pasta temporária ou PowerShell como usuário não bastam para chamar algo de sandbox.
- Avaliar Windows Sandbox/VM ou outro runtime adequado. Windows Sandbox depende da edição/virtualização e não está disponível no Windows Home; não assumir disponibilidade neste notebook. Rede e compartilhamentos precisam de configuração explícita.
- Começar com Python e um conjunto pequeno de operações de dados. Publicar entrada somente dos arquivos selecionados; saída é conferida antes de importar para a conversa/pasta do dono.
- Rede desligada como padrão desse ambiente; o dono pode habilitar o acesso suportado. Sem nova instalação, habilitação do Windows ou download nesta etapa de planejamento. Dependências e consumo entram na decisão antes da implementação.
- Exibir código, estado, saída, erro, arquivos e motivo de interrupção. Comando Windows existente continua identificado como execução no próprio PC, com suas regras atuais.

**Concluída quando:** testes mostram fronteira entre execuções e host, rede conforme escolha, bloqueio de caminhos/credenciais não compartilhados, limites efetivos, cancelamento e artefatos corretos para CSV/gráfico. Se o runtime não puder ser oferecido com essas propriedades, a etapa permanece incompleta; não renomear uma execução comum como isolada.

Entrega separada, com decisão técnica registrada e smoke do instalador no Windows compatível. Esforço/consumo só podem ser estimados após o estudo.

### 7. Cofre opcional de conversas e documentos

**Estado: planejada, com projeto de chaves e recuperação pendente.**

Entregas:

- Definir exatamente o que será protegido: conversa, memórias, conteúdo de documentos, anexos, vetores/índices, temporários e backups. Metadados que permanecerem legíveis precisam ser declarados.
- Escolher biblioteca e formato de armazenamento mantidos; comparar opções antes de adicionar dependências. Evitar criptografia criada no projeto.
- Projetar chave, bloqueio/desbloqueio, recuperação e exportação para outro PC. O DPAPI atual de credenciais não é, sozinho, um formato portátil de recuperação.
- Migrar a base existente com backup, verificação e recuperação de interrupção. Versões sem suporte ao formato novo devem recusá-lo claramente; não tentar abrir o banco cifrado como SQLite comum.
- Proteger também cópias e índices derivados; declarar o alcance e os limites durante uma sessão desbloqueada. Planejar como reindexar documentos após restauração e como lidar com perda de chave.
- Ativação opcional e controlada pelo dono. Não apagar a base original antes de validar migração e recuperação; definir retenção das cópias anteriores com escolha explícita.

**Concluída quando:** testes cobrem migração, interrupção, senha/chave incorreta, bloqueio, backup/restauração em outro perfil/PC e atualização de versão; conteúdo privado não aparece em cópias/índices que deveriam estar protegidos. Documentar o que pode ser recuperado sem a chave e o que não pode, sem prometer proteção de uma sessão já desbloqueada.

Código provável: `backend/memory/store.py`, migrações, `backend/security/vault.py`, `backend/maintenance.py`, armazenamento de anexos/índices, fluxos de perfil e instalação.

## Entregas por rodada

**Rodada A — clareza e continuidade:** linha de base da etapa 0, capacidades da 1, cartões da 2 e orçamento/continuidade da 3. Os componentes de software podem avançar enquanto uma medição de outro PC estiver pendente, mas essa evidência não será declarada concluída.

**Rodada B — velocidade e uso de ferramentas:** etapas 4 e 5, com comparação contra a linha de base. Resultado pode ser manter uma configuração atual quando a alternativa não demonstrar melhora.

**Rodada C — recursos opcionais maiores:** etapas 6 e 7, cada uma em entrega própria após decisão de infraestrutura/dependências e testes de isolamento ou recuperação. Não são requisitos para distribuir as melhorias de chat das rodadas anteriores.

Não reservar números de versão antes de implementar e validar o escopo real. Cada rodada deve ter código completo, documentação, instalador e evidências próprias.

## Critério comum para marcar uma etapa como feita

- [ ] Comportamento implementado no backend e interface, conforme aplicável.
- [ ] Testes relevantes de sucesso, falha e regressão passaram; aprovações, STOP, histórico e escolha de modelo continuam funcionando.
- [ ] Verificação real no ambiente/modelo necessário concluída; distinguir explicitamente simulação e execução real.
- [ ] Indicadores e textos refletem o que aconteceu; não há capacidades, resultados ou desempenho inventados.
- [ ] Alterações no armazenamento têm migração, backup e recuperação testados.
- [ ] Runtime/instalador final conferido quando houver alteração distribuída; documentação e manifesto da release correspondem ao artefato.
- [ ] Commit publicado com evidências e próximos passos. O aplicativo instalado só é considerado atualizado após confirmar a versão no destino.

Modelo do registro: **feito / pendente / bloqueado por dependência**, commit, testes executados, resultado observado e próximo passo concreto. Uma API ou tela pronta com validação real pendente não fecha a etapa completa.

## Fora do escopo deste plano

Não inclui treinar um modelo exclusivo, comprar serviços/certificados, contratar Drael, gerar imagens com novos pesos ou baixar Hermes agora. Voz, iPhone, Authenticode e validações de documentos/personalidade continuam no [STATUS](STATUS.md); não foram concluídos por este planejamento.

Personalidade e regras escolhidas pelo dono continuam preservadas. Estas melhorias tratam de usabilidade, contexto, execução e privacidade; não reescrevem os pesos dos modelos nem garantem a mesma resposta entre motores.
