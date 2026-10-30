# Correção do contexto — 0.5.1

Rodada de 30/10/2026 neste notebook. O usuário relatou o indicador “5.469 / 3.200 tokens” bloqueando o chat. A correção da 0.3.1 já usava o tokenizer do Qwen; a 0.5 introduziu uma nova rota Automático que a estimativa do compositor não resolvia.

## Causas reproduzidas

1. O compositor enviava `model: auto` para `/chat/estimate`. `auto` não é um motor, então caía na contagem conservadora por bytes em vez de usar o tokenizer do motor escolhido. No teste sintético Notebook/modo 2, “oi” era recusado por cerca de 4.386 unidades; com o Qwen escolhido, precisava de cerca de 1.200 tokens e cabia.
2. Leituras de até cinco janelas eram anexadas sem orçamento próprio. O teste sintético de pedido de clique com cinco leituras passou de 4.700 tokens, antes do histórico. Esses são dados auxiliares do aplicativo, não a mensagem/memória escolhida pelo usuário.
3. A prévia durante a digitação não incluía os IDs dos anexos nem era refeita ao alterar permissões. A conferência no envio era mais completa, deixando os indicadores inconsistentes.

## Alterações

- `/chat/estimate` resolve Automático com o roteador existente, informa o motor real e usa o seu contador. Não chama inferência, não envia dados à nuvem e não emite consentimento de nuvem. Escolha efetiva no envio e prévia/consentimento de nuvem continuam separados.
- Dados auxiliares são incluídos somente como blocos completos que caibam em seu orçamento. JSON e marcadores de conteúdo não confiável não são cortados pela metade. Dados omitidos podem ser lidos novamente por ferramenta; a omissão é informada no indicador.
- Mensagem, instruções do dono e memórias explicitamente escolhidas são preservadas. O limite físico não foi removido e o Notebook continua com 4.096 tokens totais; não há aumento silencioso do consumo de RAM/VRAM.
- Imagens/documentos entram na estimativa; suporte a imagem é conferido antes de atribuir uma falha ao contexto. Informações de capacidades foram compactadas, preservando os fatos de suporte do provedor.
- Indicador mostra o motor escolhido no Automático e a composição por mensagem, personalidade/memórias, ferramentas, dados auxiliares, imagens/documentos e histórico. Trocar permissões ou anexos refaz a conferência.
- Rascunho e histórico permanecem preservados quando um envio realmente não cabe. Não há corte silencioso de instruções/memórias escolhidas nem ampliação de permissões.
- O orçamento de ferramentas considera também as definições formatadas: um smoke real mostrou que só contar JSON compacto subestimava o prompt. Com a correção, a estimativa foi 1.461 tokens e o Ollama mediu 1.387; histórico longo reserva esse espaço.

## Ações simples e Hermes

O relato seguinte mostrou um problema diferente: “abre o bloco de notas” recebia uma análise inventada de pesquisa antiga, após quase oito minutos. Pedidos exatos e únicos para abrir Bloco de Notas ou Calculadora agora passam pelo caminho **ação local direta**, sem carregar modelo, anexar histórico ou consultar a nuvem. A UI identifica a execução local; a mensagem não é atribuída ao Qwen/Hermes. Regras do dono, modo Observação, aprovação, origem do iPhone e STOP continuam sendo aplicados pelo serviço de ferramentas. Falha ou resultado não verificado nunca vira confirmação de sucesso. Pedidos com anexos, resultados de ferramenta, negação, aspas, explicação ou várias ações não são interceptados.

Hermes 3 3B/8B foi acrescentado ao catálogo, com seus próprios tokenizers validados e suporte ao contrato de ferramentas Ollama. Os pesos não foram baixados; ver [HERMES.md](HERMES.md).

Durante a suíte completa apareceu uma violação de acesso nativa do SQLite: a thread do atalho de voz continuava consultando o banco durante `close()`. O fechamento agora usa o mesmo lock das consultas e encerra os trabalhadores de voz, alertas e monitoramento antes de fechar o banco. A regressão de encerramento verifica que esses trabalhadores terminam.

## Validação e distribuição

Validação do código: **233 testes Python passaram, 1 ignorado por privilégio de symlink, e 5 testes Node passaram**, após as correções de encerramento e orçamento. TypeScript/Vite compilou; o renderer sintético passou nos fluxos de Automático, composição, troca de permissões, rascunho, bloqueio legítimo, ação direta sem roteamento de modelo e catálogo Hermes 3B/8B. Regressões incluem modos 2/4, nuvem sem geração/consentimento, observações de janelas grandes, documentos/imagens no Notebook e blocos completos.

Os testes gerais de funcionalidades com nomes de modelo sintéticos agora usam perfil Desktop explícito, para que a contagem conservadora por bytes desses dublês não dependa da bateria/RAM da máquina de teste. Os testes de orçamento Notebook usam esse perfil explicitamente com tokenizer Qwen real. Também foi corrigido um falso roteamento: “abalado” não é pedido de “aba” do navegador; a instrução de acolhimento continua disponível.

Resposta local real concluída, em banco temporário, Notebook/modo 2: [relatório](chat-context-0.5.1-smoke.json). Automático escolheu Huihui 4B, respondeu “pronto.” e o contador estimou acima dos tokens reais. Foram cerca de 92 s neste notebook sob carga concorrente; isso comprova funcionamento, não uma melhoria de latência. Nenhuma ação Windows, arquivo pessoal ou API paga foi usada nesse smoke. Hermes não foi testado com pesos reais.

Em andamento: rebuild e smoke do pacote final 0.5.1. Atualizar com os resultados antes de publicar. O candidato inicial de instalador foi gerado antes dessas alterações e não deve ser distribuído. O controle nativo da área de trabalho estava indisponível (`Computer Use native pipe is unavailable`, erro 2); nenhuma abertura real do Bloco de Notas foi validada nesta sessão. Os testes da ação direta usam o serviço real de propostas/permissões e execução simulada, sem tocar documentos/janelas do dono.

O pacote 0.5.0 já publicado permanece inalterado. A correção está sendo preparada como **0.5.1**; atualizar o Git não troca o processo instalado/aberto. Authenticode continua dependência separada. Não declarar instalação concluída sem confirmação.

## Melhorias seguintes, na ordem

1. Validar e distribuir esta correção; medir novamente no PC principal com GPU recuperada.
2. Expor capacidades/contexto reais e um controle de orçamento adequado ao hardware, com escolha explícita do usuário.
3. Medir modo rápido/aprofundado e tamanhos do catálogo sem regredir a escolha de ferramentas.
4. Melhorar cartões de arquivos/resultados e compactação de conversas longas, preservando os originais e mostrando o que foi usado.
5. Planejar execução isolada de código e cofre local, com testes próprios. Essas propostas não estão entregues nesta correção.
