# Validação local da base 0.5

Data local: 29/10/2026. Base recuperada: `work/0.5`, commit `5123031`.
Pasta de trabalho: `ALT-current` dentro do workspace; a cópia antiga foi preservada.

## Verificado nesta máquina

- Compilação Python do backend, TypeScript/Vite e cinco testes Node passaram.
- Suíte Python após os ajustes de documentos: 127 passaram, um ignorado por privilégio de symlink. Inclui testes de métricas, PDF/Word, OCR seletivo, limites de trechos e capacidades do provedor.
- App Electron iniciado com perfil separado em `.local/ui-test-profile`, conectado ao Ollama real.
- No app aberto, Qwen 4B respondeu ao pedido sintético com “Conexão confirmada”.
- Whisper small baixado com autorização explícita para a pasta de testes. A API real `/voice/transcribe` processou áudio sintético pt-BR da Microsoft Maria, sem captura do microfone.
- A transcrição respondeu HTTP 200: áudio de 7 s, inferência de 4,2 s, total de 8,75 s incluindo carga. Reconheceu Spotify e “teste de voz local”, mas errou palavras e introduziu texto espúrio. Isso confirma o funcionamento do pipeline, não a qualidade do reconhecimento nem o microfone.

## Ajustes locais

- Personalidade: sem ferramenta, informa o limite em vez de prometer executar e pedir repetição. Confirmações dependem de resultado confirmado.
- Métricas de preparação, carga, leitura do contexto, geração e primeiro texto salvas com a mensagem e mostradas em “Desempenho”. Campos ausentes continuam como não informados.
- Botão Acesso total: regra específica de largura automática evita a largura de 27 px destinada a ícones. Texto sem quebra; a barra pode usar outra linha em janelas menores.
- A correção do botão foi recarregada e conferida visualmente no app, com a conversa preservada.
- PDFs digitalizados: leitura OCR local nas páginas sem texto; páginas com texto mantêm a extração normal. O usuário autorizou usar documentos de Downloads: PDF com texto (814 caracteres), catálogo digitalizado com 32 páginas (10.369 caracteres por OCR em 14,407 s) e Word (17.425 caracteres) foram lidos. Nenhum conteúdo desses documentos foi incluído no Git.
- A descrição de visão vem das capacidades reais de `/api/show`. O Qwen 3.5 4B informou `vision`; não há gerador de imagens integrado. A orientação não deve inventar aceleração por IDE nem negar visão por suposição.
- Ollama real: 4B e 9B acertaram os cinco códigos dos arquivos sintéticos (TXT, PDF textual, Word com tabela, PDF digitalizado e JPEG), total 10/10. Relatório em `document-chat-smoke.json`. Isso valida os casos curtos testados, não qualquer documento arbitrário.

## Medição inicial limitada

`scripts/benchmark_latency.py` usa apenas prompts sintéticos. Não executa chamadas de ferramenta.
Os resultados completos estão em `latency-initial.json`.

| Modelo | Primeiro texto, primeira carga | Primeiro texto, repetição carregada | Chamada completa para propor Spotify, carregado |
| --- | ---: | ---: | ---: |
| 4B | 23,344 s | 0,969 s | 13,453 / 10,250 s |
| 9B | 57,781 s | 0,813 s | 18,000 / 15,500 s |

A chamada de ferramenta só aparece no stream quando seus argumentos estão completos: essa coluna não é tempo até a primeira palavra nem tempo para abrir o programa. As ações não foram executadas pelo benchmark.

Na segunda chamada de Spotify, o 4B gastou 0,321 s lendo contexto e 9,835 s gerando; o 9B gastou 0,424 s lendo e 15,140 s gerando. Nesta amostra, gerar os argumentos pesou mais que reler o prompt. Não está demonstrado que a leitura do prompt seja o maior gargalo deste PC.

Havia um jogo aberto durante a medição. O Ollama informou o 9B inteiramente na GPU com contexto 8192. Isso não mede utilização da GPU pelo jogo nem prova que ele causou a lentidão. Os tempos não representam uma medição isolada da placa.

Ainda faltam os casos de conversa longa, memória e anexo, comparação de ferramentas estáveis, medição de abertura real de app e relatório antes/depois da etapa de velocidade. Nenhuma meta de desempenho foi declarada concluída.

## Pendências de validação e entrega

- Conferir também o layout em janela menor.
- Reiniciar o backend da janela de desenvolvimento para carregar OCR/autoconhecimento; Escape interrompeu o controle antes disso. A compilação e os testes de API usam o código novo, mas a instância já aberta ainda estava com módulos Python anteriores.
- Exercitar anexos reais (imagem/PDF/Word), microfone e fala no app, atalhos Windows e Game Mode com inferência na CPU.
- Claude real não foi testado com conta/chave; cobertura atual usa transporte simulado.
- Nenhum instalador 0.5 foi gerado; nenhuma alteração desta rodada foi publicada em `main`.
