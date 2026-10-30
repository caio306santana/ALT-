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

## Validação e distribuição

Validação do código: **199 testes Python passaram, 1 ignorado por privilégio de symlink, e 5 testes Node passaram**. TypeScript/Vite compilou; o renderer sintético passou nos fluxos de Automático, composição, troca de permissões, rascunho e bloqueio legítimo. Regressões incluem modos 2/4, nuvem sem geração/consentimento, observações de janelas grandes, documentos/imagens no Notebook e blocos completos.

Os testes gerais de funcionalidades com nomes de modelo sintéticos agora usam perfil Desktop explícito, para que a contagem conservadora por bytes desses dublês não dependa da bateria/RAM da máquina de teste. Os testes de orçamento Notebook usam esse perfil explicitamente com tokenizer Qwen real. Também foi corrigido um falso roteamento: “abalado” não é pedido de “aba” do navegador; a instrução de acolhimento continua disponível.

Em andamento: validação de resposta local real, geração e smoke do pacote 0.5.1. Atualizar esta seção com os resultados antes de publicar o instalador.

O pacote 0.5.0 já publicado permanece inalterado. A correção está sendo preparada como **0.5.1**; atualizar o Git não troca o processo instalado/aberto. Authenticode continua dependência separada. Não declarar instalação concluída sem confirmação.

## Melhorias seguintes, na ordem

1. Validar e distribuir esta correção; medir novamente no PC principal com GPU recuperada.
2. Expor capacidades/contexto reais e um controle de orçamento adequado ao hardware, com escolha explícita do usuário.
3. Medir modo rápido/aprofundado e tamanhos do catálogo sem regredir a escolha de ferramentas.
4. Melhorar cartões de arquivos/resultados e compactação de conversas longas, preservando os originais e mostrando o que foi usado.
5. Planejar execução isolada de código e cofre local, com testes próprios. Essas propostas não estão entregues nesta correção.
