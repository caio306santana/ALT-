# ALT 0.5 — plano único: assistente estilo JARVIS completo

Repositório: `C:\Users\caios\ALT-`. Base: branch `work/0.4.2` (0.4.2 publicada, commit `3d54d10`), mais o trabalho ainda sem commit descrito na etapa 0. Branch nova: `work/0.5`, com um commit por etapa. No fim: instalador, GitHub e merge no `main`.

## Contexto

O usuário quer a ALT como uma assistente de verdade, misturando a Alt Cunningham e o JARVIS:
- obedece;
- fala e ouve;
- vê a tela;
- abre e controla tudo no PC;
- lembra das coisas;
- fala por conta própria na hora certa;
- funciona no iPhone sem App Store.

Ele pediu **um plano geral só**, sem dividir em versões, usando duas referências:
- **OpenJarvis** (Stanford), em `C:\Users\caios\Downloads\ALT--main\referencia jarvis\OpenJarvis-main\OpenJarvis-main\src\openjarvis\`, abreviado aqui como `oj/`;
- **Mark-LVI**, em `C:\Users\caios\Downloads\ALT--main\refrencia 2\Mark-LVI-main\Mark-LVI-main\`, abreviado como `mk/`.

Os dois são código de terceiros. **Nada deles é executado, importado ou copiado.** As ideias são reescritas no estilo da ALT. Os pontos fracos que encontrei não são copiados. No `mk/`:
- servidor em `0.0.0.0` por HTTP;
- firewall alterado com elevação;
- segredo dentro da URL;
- celular com acesso a todas as ferramentas.

No `oj/`, a pasta `mining/` (cripto) fica de fora.

Decisões do usuário:
- palavra de ativação "Hey Jarvis" agora, com "Ei ALT" treinado como opção depois de validado;
- voz feminina natural: Kokoro "Dora" pt-BR, com a Maria (SAPI) de reserva;
- iPhone por Tailscale e PWA, sem Telegram.
- Preferência confirmada nesta sessão: híbrido, com modelo local para pedidos simples e nuvem para os complexos, sempre com prévia e aprovação. Isso não ativa a API paga nem envia dados sozinho.

A versão instalada no PC dele ainda é a 0.4.1, a da personalidade que discute e do bug do Bloco de Notas. Tudo aqui só chega a ele pelo instalador do fim.

Regra de segurança que vale para todas as etapas:
- comandos do PowerShell sempre passam pelo cartão;
- só um clique na interface aprova uma ação; o modelo nunca se aprova;
- conteúdo de site, arquivo, janela ou anexo é dado, nunca instrução;
- o STOP corta tudo.

---

## Etapa 0 — fechar o que está aberto

O working tree tem, sem commit:
- rodada de correção de ferramenta (`api.py`, `tool_error`);
- `windows_keys`;
- Claude com ferramentas;
- voz por Whisper (`backend/voice/transcriber.py`, `VoiceButton.tsx`);
- anexos (`backend/attachments.py`, `Attachments.tsx`);
- Game Mode na CPU;
- `APP_FACTS`;
- dependências do faster-whisper em `requirements*` e `backend.spec`.

1. **Consertar `backend/personality.py` L10-14.** O heredoc do bash quebrou as strings:
   - L12-13: `APP_FACTS='` seguido de uma quebra de linha real. Deve virar `APP_FACTS='\n'+'Recursos…`. O fim, `+'\n'`, já foi corrigido.
   - L11: o `\bvoz\b` ficou com caracteres de backspace.
   - Ler o trecho e usar **Edit**. Nunca editar código com heredoc do bash.
2. Rodar `py_compile` em todos os `.py` alterados e varrer o diff atrás de strings quebradas.
3. Testes que faltam, em `tests/test_attachments.py`:
   - TXT anexado entra no `user_content` como dado e continua no turno seguinte;
   - JPEG chega em `images`;
   - bytes que não são JPEG são recusados;
   - modelo sem `vision` recebe 409;
   - Codex com imagem é recusado;
   - a estimativa do Claude conta 1600 tokens por imagem;
   - excluir a conversa apaga os arquivos;
   - `/voice/transcribe` recusa áudio inválido e recusa quando está suspenso.
4. Rodar `npm.cmd test` e `npm.cmd run build`, depois commit "0.5 etapa 0".

## Etapa 0.5 — velocidade (vem antes de tudo, porque é o que o usuário mais sente)

O usuário reclama que a ALT está lenta. Nas conversas que ele colou: 4 tok/s, 180 s por resposta e 600 tokens de discurso.

O que as referências mostram:
- `mk/providers/llm_openai.py` L82-100: **de 89 a 94% do tempo antes da primeira palavra é leitura do prompt**, e a declaração das ferramentas é a maior parte. Cortar para 14 ferramentas e 12 mil caracteres tirou um terço do prompt de todo turno.
- `oj/prompt/builder.py` L23-186: o prompt tem um **prefixo fixo**, e a parte dinâmica vai no fim, para o Ollama reaproveitar o cache.
- `mk/providers/engine_pipeline.py` L385-410: aquecimento faz a primeira frase cair de 8,9 s para 1,2 s.

A ALT hoje faz o oposto: o enum de ferramentas e o contexto do turno (escopos, programas, janelas, memórias, orientação) entram no **início** do prompt, e mudam a cada mensagem. Por isso o Ollama relê tudo toda vez.

1. **Medir antes de mexer.** `scripts/bench_latency.py` roda no 4B e no 9B e registra, a partir dos campos do Ollama `load_duration`, `prompt_eval_count`, `prompt_eval_duration`, `eval_duration` e o tempo até a primeira palavra:
   - primeira mensagem com o modelo frio;
   - segunda mensagem;
   - pedido com ferramenta;
   - conversa longa;
   - com memória lembrada;
   - com anexo.

   O resultado vai para `docs/latency.json`. Esses números passam a aparecer na mensagem e num painel "Desempenho" em Monitoramento, separados por etapa: carregar, ler, pensar, ferramenta, voz (`mk/providers/engine_pipeline.py` L650-700).
2. **Prompt que o Ollama reaproveita**:
   - o sistema fixo (identidade, regras, personalidade) fica **sempre igual e no começo**;
   - todo o resto vai num bloco "CONTEXTO DESTE TURNO" no fim da mensagem do usuário: escopos, programas, janelas, situação, memórias lembradas, anexos e autoconhecimento do turno;
   - a data fica num formato que só muda uma vez por dia;
   - arquivos: `api.py` (`context_for`), `personality.py`.
3. **Ferramentas estáveis**:
   - testar no `bench_latency` o enum filtrado por mensagem (atual) contra um conjunto **fixo por modo de permissão**, com orçamento de no máximo 14 ferramentas e 12 mil caracteres, ferramentas centrais primeiro e descrição curta (`mk/providers/schema.py` L272-377);
   - o conjunto fixo mantém o prefixo idêntico entre turnos e o cache vale;
   - fica o que der menor tempo até a primeira palavra **sem perder acerto** no `smoke_full_access`;
   - a rodada de correção reaproveita o mesmo prefixo.
4. **Modelo sempre carregado**:
   - pré-carregar o modelo escolhido ao abrir o app, ao trocar de modelo e ao sair do Game Mode, com uma chamada vazia que usa o mesmo `num_ctx`;
   - `keep_alive` de 30 min no desktop e 5 min no notebook, configurável;
   - Whisper e a voz Dora aquecidos em segundo plano no início (`mk/providers/stt_whisper.py` L251-284).
5. **Não recarregar o modelo à toa**:
   - o mesmo `num_ctx` em **todas** as chamadas do perfil (chat, resumo, avaliação, tarefas, extração de memória). Trocar o `num_ctx` faz o Ollama recarregar o modelo. Conferir os chamadores de `performance_profile` em `evaluations.py`, `memory/continuity.py` e `tasks.py`;
   - o **EmbeddingGemma roda na CPU** (`num_gpu: 0` em `Ollama.embed`), para não tirar o modelo de conversa dos 8 GB de VRAM;
   - resumo de conversa e extração de memória só depois de 60 s parada, pausados assim que o usuário digita ou fala. Fila de baixa prioridade em `knowledge.schedule_summary`.
6. **Respostas no tamanho certo**:
   - `num_predict` de 1024 no desktop para conversa;
   - a personalidade curta já reduz o texto.
7. **Detectar a placa de vídeo dividida**:
   - se o `/api/ps` mostrar `size_vram < size`, ou outro processo estiver usando muito a GPU (contadores `GPU Engine` do Windows), aviso claro: "o modelo está X% no processador porque a placa de vídeo está ocupada (jogo?): use o 4B ou o Game Mode";
   - o mesmo dado aparece no painel Desempenho.
8. **Ajustes do servidor Ollama** (com consentimento):
   - oferecer `OLLAMA_FLASH_ATTENTION=1` e `OLLAMA_KV_CACHE_TYPE=q8_0` como variáveis de usuário e reiniciar o Ollama;
   - medir antes e depois na RX 7600 e **só manter se ficar mais rápido e as respostas continuarem corretas**, porque o suporte varia em placa AMD.
9. **Velocidade percebida**: a fala frase a frase, a confirmação na hora (etapa de voz) e a escolha automática do 4B para o simples (etapa de modelo automático) entram nas etapas delas, medidas pelo mesmo `bench_latency`.

Meta, a confirmar contra a medição inicial, com o modelo já carregado no desktop:
- **4B:** primeira palavra em menos de 1,5 s;
- **9B:** em menos de 3 s;
- pedido de ação simples (abrir um programa) concluído em menos de 3 s no 4B.

O relatório final compara os números de antes e depois.

Testes:
- o prefixo do sistema é idêntico byte a byte entre dois turnos com ferramentas diferentes;
- o contexto do turno fica no fim;
- todas as chamadas do perfil usam o mesmo `num_ctx`;
- o embed manda `num_gpu: 0`;
- o resumo não começa enquanto há conversa ativa.

## Etapa 1 — ações que dizem a verdade e erram menos

1. **Contrato de resultado** (`mk/core/outcome.py`):
   - Toda ferramenta devolve `status ∈ {done, unverified, failed, ask, started}` mais fatos, e o resultado é guardado em `actions.result`.
   - Para o modelo, cada estado que não é `done` termina com uma instrução fixa em pt-BR, por exemplo "NÃO confirmado; não diga que foi feito".
   - O cartão só mostra ✓ quando o estado é `done`; `unverified` mostra "pedido enviado, não confirmado".
   - Arquivos: `backend/tools/outcome.py` (novo), `service.py` (cada ramo de `execute`), `ChatActionCard.tsx` (`summary`).
2. **`open_app` verificado** (`mk/actions/open_app.py` L248-368, `mk/core/appidentity.py` L578-608 e L771-843):
   - antes de abrir, tira uma foto dos PIDs; depois verifica a cada 0,25 s, por até 12 s, se surgiu o processo, e responde `done` ou `unverified`;
   - **se o programa já está aberto, traz a janela para frente** em vez de abrir outra cópia, usando `ShowWindow`/`SetForegroundWindow` com `AttachThreadInput`;
   - o mesmo `focus()` passa a ser usado por `WindowsUI.press`, acabando com o "o Windows não deixou trazer a janela";
   - arquivos: `backend/tools/app_catalog.py`, `backend/tools/windows_ui.py`, `service.py`.
3. **`close_app` verificado** (`mk/core/appidentity.py` L446-562 e L656-740, `mk/actions/computer_control.py` L332-456):
   - pontuação exata/prefixo/contém, com mínimo de 4 letras para busca parcial;
   - empate entre programas diferentes dá `ask`;
   - agrupa por processo e nunca força o fechamento;
   - `done` só se os PIDs sumirem em até 6 s; se não, avisa que "pode estar pedindo para salvar";
   - protege os processos da própria ALT, os irmãos do Electron, o Python e o **Ollama**;
   - substitui `close_by_name` em `service.py`.
4. **Fronteira de conteúdo não confiável** (`mk/core/outcome.py` L184-258):
   - envolver em marcadores `<<<NÃO CONFIÁVEL fonte=…>>> … <<<FIM>>>`, neutralizando marcadores que já venham no texto, tudo o que vem de fora: busca, página, `read_text`, `windows_read`, anexos e resultado de ferramenta em `context_for`;
   - tirar os marcadores na hora de exibir;
   - função única em `backend/tools/outcome.py`, usada por `api.py` e `attachments.py`.
5. **Reparos para modelo pequeno**:
   - descartar chamada que só tem `/think` ou `/no_think` (`oj/engine/ollama.py` L35-70);
   - texto puro vira o único campo exigido (`oj/agents/orchestrator.py` L231-298);
   - os dois rodam antes da rodada de correção em `api.py`.
6. **Trava contra loop** (`oj/agents/loop_guard.py`, `mk/providers/engine_pipeline.py` L498-536):
   - nos planos (`backend/tasks.py`), a mesma ação idêntica 3 vezes é bloqueada, e o vai e volta A-B-A-B também;
   - chamada repetida igual devolve o resultado em cache;
   - no máximo 4 rodadas de ferramenta por turno.
7. **Autoconhecimento derivado** (`mk/main.py` L248-310 e L1131-1170):
   - o prompt diz o que ela **pode e não pode** neste turno: as ferramentas oferecidas, o modo de permissão, Game Mode, voz, visão do modelo atual, e "o que não está listado está fora do alcance";
   - substitui o `APP_FACTS` fixo, sempre dentro do orçamento do notebook;
   - cada ferramenta ganha uma descrição curta (`brief`) para o enum (`mk/providers/schema.py` L272-377);
   - arquivos: `personality.py`, `chat_tools.py`.
8. **Exemplos aprendidos com o histórico** (`oj/skills/overlay.py`, `oj/learning/agents/skill_optimizer.py` L245-256):
   - 2 ou 3 turnos falsos (pedido → chamada certa), tirados de ações `complete` da tabela `actions` para as ferramentas oferecidas;
   - só o pedido curto e os argumentos, sem conteúdo;
   - some quando não cabe no orçamento;
   - fica só se o smoke mostrar que não piora.

Testes em `tests/test_reliability.py`:
- estados e instruções fixas;
- `open_app` "já aberto" foca e não duplica (com fake do enum de janelas);
- empate no `close_app` dá `ask`;
- os processos próprios e o Ollama nunca são alvo;
- os marcadores são neutralizados;
- `/no_think` é descartado;
- texto puro vira o campo exigido;
- o loop guard barra a terceira repetição;
- os exemplos only vêm de ações completas.

## Etapa 2 — permissões inteligentes e desfazer

1. **"Sempre permitir" por risco** (`oj/tools/approval_store.py` L28-43 e L299-363):
   - botão no cartão para abrir app, site ou pasta, para atalhos, volume e mídia;
   - guardado em uma tabela `remembered_approvals(tool, target)`, consultada em `can_auto` nos modos 2 e 3;
   - **nunca** para `run_command`, `close_app`, `write_text` nem download;
   - lista com "remover" em Controle e regras (`WorkspacePanels.tsx`).
2. **Contaminação da sessão** (`oj/security/taint.py` `SINK_POLICY`, `oj/security/injection_scanner.py`):
   - se uma leitura trouxer segredo, dado pessoal ou token de template de chat, a conversa fica marcada;
   - até o STOP ou uma conversa nova, site, download, escrita e atalhos voltam ao cartão mesmo no modo 4;
   - o cartão mostra o motivo.
3. **Desfazer** (`mk/core/undo.py`, `mk/actions/file_controller.py` L20-90):
   - pilha de 10 por sessão:
     - `write_text` restaura a versão anterior (já guardada em `file-history`);
     - arquivo criado é apagado se não mudou;
     - download feito é apagado;
     - volume e brilho voltam ao valor lido antes;
   - ferramenta `undo` ("desfaz") e botão "Desfazer" no cartão concluído;
   - arquivos: `backend/tools/undo.py` (novo), `service.py`.
4. **Confirmação que só a interface dá** (`mk/core/confirm.py`):
   - auditar se nenhum caminho aceita aprovação vinda do modelo;
   - cartões críticos expiram em 90 s.

Testes:
- "Sempre permitir" recusa as ferramentas proibidas;
- com taint, `open_url` no modo 4 pede cartão;
- desfazer `write_text` restaura o conteúdo e desfazer download apaga o arquivo.

## Etapa 3 — ferramentas novas: tela, sistema e lembretes

1. **Ver a tela** (`mk/actions/screen_processor.py` L92-103, `mk/main.py` L1323-1357):
   - `screen_look` captura o monitor principal (biblioteca `mss`), reduz para JPEG de 1280 px e manda como imagem no mesmo turno ao Qwen, que tem visão;
   - pausa mínima de 4 s entre capturas; o prompt deixa claro que "a captura é do computador do usuário";
   - no modo 4 roda direto; nos outros, mostra o cartão;
   - palavras-chave: "olha minha tela", "o que tem na tela", "lê isso aqui".
2. **Sistema** (`mk/actions/computer_settings.py` L97-190 e L957-1022):
   - `system_volume` (definir, mudo, mais, menos) via `pycaw`;
   - `system_brightness` via WMI;
   - `media_key` (tocar/pausar, próxima);
   - leitura antes e depois para virar `done`; sem mudança vira `unverified`;
   - guarda o valor anterior para o desfazer.
   - Fica de fora: desligar, reiniciar e Wi-Fi.
3. **Lembretes que tocam com a ALT fechada** (`mk/actions/reminder.py` L146-199):
   - `reminder_create`, `reminder_list`, `reminder_cancel` via `schtasks /Create /XML`: TimeTrigger, InteractiveToken, LeastPrivilege, StartWhenAvailable;
   - a ação é um PowerShell que mostra uma notificação do Windows com o texto lido de um arquivo, nunca interpolado no comando;
   - depois de criar, confere com `/Query`;
   - criar e cancelar entram no desfazer;
   - lista em uma aba nova "Rotinas".

Testes:
- `screen_look` (com fake do `mss`) envia a imagem;
- a pausa entre capturas é respeitada;
- o XML do lembrete escapa o texto e nunca o põe na linha de comando;
- o volume sem mudança dá `unverified`.

## Etapa 4 — voz estilo JARVIS (o backend cuida de ouvir e falar)

A voz sai do renderer e passa para o backend. Isso permite atalho global de segurar para falar, palavra de ativação, fala frase a frase e corte da fala sem depender de a janela estar aberta.

1. **`backend/voice/loop.py`** (novo), com a captura em `sounddevice` a 16 kHz:
   - **Segurar para falar global** (`mk/core/hotkey.py`): verificação de `GetAsyncKeyState` 30 vezes por segundo, com 60 ms de debounce. Atalho configurável, padrão **Ctrl+Espaço** (diferente do atalho que abre a janela).
   - **Palavra de ativação** (`mk/core/wake_word.py`):
     - openwakeword `hey_jarvis` com limiar 0,5, inferência em thread separada;
     - fila que descarta quadros quando enche e é esvaziada depois de cada detecção;
     - enquanto ela dorme, **nenhum áudio vai para o Whisper**;
     - dorme sozinha depois de 120 s sem fala;
     - opcional, com download e consentimento;
     - "Ei ALT" treinado: script `scripts/train_wake_word.py`, que gera amostras sintéticas com a própria voz da ALT e treina com o openwakeword. Entra como opção só se passar no teste de falsos positivos (gravação de 30 min de ruído e fala comum, com menos de 1 ativação por hora).
   - **Fim da fala sem botão** (`mk/providers/engine_pipeline.py` L262-305): VAD de energia com piso adaptativo, 700 ms de silêncio, mínimo de 250 ms de fala, máximo de 30 s.
   - **Não responder à própria voz:** microfone em silêncio enquanto ela fala, mais o atraso do buffer e 250 ms (`mk/main.py` L956-960). O corte por voz fica desligado, como no Mark; cortar é pelo atalho, pela palavra de ativação ou pelo STOP.
   - **Whisper** (`mk/providers/stt_whisper.py` L64-77, 238, 251-284):
     - aquecimento com 0,1 s de silêncio ao carregar, o que leva a primeira frase de 8,5 s para cerca de 1 s;
     - descarta clipes com menos de 0,25 s;
     - usa metade dos núcleos;
     - medir beam 1 contra beam 5 com a dica de vocabulário.
   - **Transcrição** (`mk/providers/stt_whisper.py` L178-202): a fala transcrita vai como evento para a interface, que envia a mensagem com `speak:true`.
2. **Falar** (`backend/voice/speech.py`):
   - Kokoro com `lang_code 'p'` e voz `pf_dora` (`oj/speech/kokoro_tts.py` L33-105 e L146-235, `mk/core/tts.py` L208, L301-347);
   - aquecimento, pausas de pontuação limitadas a 500 ms;
   - fila produtor/consumidor que sintetiza o trecho N+1 enquanto toca o N;
   - reprodução em blocos de 50 ms, para o corte ser instantâneo (`mk/providers/audio.py` L158-172).
   - **Verificar primeiro** se o pacote `kokoro` e o espeak-ng instalam no Windows e entram no PyInstaller. Se não, a reserva é a Maria, chamada por PowerShell com o texto num arquivo UTF-8 (`mk/providers/tts_system.py` L33-44 e L227-251), e tratando "sucesso com 0 bytes" como erro.
3. **Fala frase a frase enquanto o modelo escreve** (`mk/providers/engine_pipeline.py` L465-469, L792-973):
   - em `api.py` `generate()`, com `speak:true`, um filtro de raciocínio remove `<think>`, segurando os últimos 11 caracteres;
   - divide as frases em `.!?…` seguidos de espaço, ou corta a cada 320 caracteres;
   - tira emoji, código e URLs;
   - manda para a fila do `speech` **sem pausar o stream do Ollama**, ao contrário do Mark.
4. **Confirmação na hora**: o prompt manda dizer uma frase curta antes de uma ferramenta demorada, como "Abrindo o Spotify" (`mk/core/prompt.txt` L73-95). A frase é falada antes do resultado chegar.
5. **Interface**:
   - o `VoiceButton` passa a ligar e desligar a escuta do backend;
   - estados: dormindo, ouvindo, pensando, falando;
   - painel "Voz" em Configurações:
     - escolha do microfone e da saída (`mk/core/audio_devices.py`: sem duplicatas entre APIs de áudio, só dispositivos que funcionam);
     - botão TESTE com medidor ao vivo e veredito "nada chegou" ou "baixo demais" (L445-534);
     - atalho de segurar para falar;
     - palavra de ativação ligada ou desligada, com o "Ei ALT" experimental;
     - voz Dora ou Maria, velocidade, botão "ouvir exemplo";
   - eventos de voz chegam por um stream `/voice/events`, levado pelo processo principal como o `api:stream`;
   - a permissão de microfone no renderer, adicionada antes, é removida: a captura agora é do backend.
6. Dependências: `sounddevice`, `openwakeword` (os modelos ONNX baixam com consentimento), `kokoro` (verificar); `backend.spec` atualizado.

Testes (sem microfone real):
- o VAD em sinais sintéticos;
- filtro de `<think>` com tag partida entre trechos;
- divisor de frases ("3.14" não corta);
- dormir depois de 120 s, com relógio falso;
- áudio com a ALT dormindo nunca chega ao Whisper;
- o STOP esvazia a fila de fala.

## Etapa 5 — memória que aprende, com revisão

1. **Extração automática** (`oj/memory/extractor.py`, `oj/memory/service.py` L212-243):
   - depois de uma resposta completa, uma fila de baixa prioridade pede ao modelo um array JSON de fatos duráveis (no máximo 10, de até 200 caracteres), tolerando saída suja;
   - varredura de injeção em cada fato;
   - tudo vira **sugestão pendente**, reaproveitando `continuity/draft` e `approve`; nada entra sem o usuário aprovar;
   - desligado por padrão, com interruptor em Controle e regras;
   - não roda no Game Mode.
2. **Lembrança com orçamento** (`mk/memory/memory_manager.py` L194-324):
   - o prompt leva identidade, um núcleo recente pequeno e um índice das outras chaves;
   - o resto vem pela busca semântica (EmbeddingGemma) quando o pedido pede;
   - ferramenta `memory_recall`.
3. **"Da última vez"** (`mk/main.py` L2037-2063, `pop_last_session`): o resumo da última conversa (já existe) é dito uma vez no resumo da manhã e marcado como usado.
4. **Painel de memórias**: data de quando aprendeu, origem (você, automática aprovada) e esquecer com um clique; texto escapado.

Testes:
- a extração só cria sugestões;
- JSON sujo é aceito;
- um fato com injeção é marcado;
- o orçamento do notebook é respeitado;
- o "da última vez" é consumido uma vez só.

## Etapa 6 — ALT proativa

1. **Agendador** (`oj/scheduler/scheduler.py` L191-333, `oj/scheduler/tools.py`):
   - tabela `routines`, com tipos `once`, `interval` e diário/semanal (cron simples) no fuso local;
   - uma thread verifica a cada 60 s e registra cada execução;
   - ferramentas `routine_create` e `routine_list` (criar sempre pelo cartão);
   - rotinas rodam no modo de permissão atual, e o PowerShell continua pedindo cartão.
2. **Resumo da manhã** (`oj/agents/morning_digest.py` L62-98 e L161-187, `mk/main.py` L1901-2033):
   - na hora marcada (padrão 8h) ou quando abrir o PC pela primeira vez no dia;
   - conteúdo: cumprimento ("Bom dia, {nome}"), hora, clima, lembretes do dia, "da última vez", tópicos acompanhados;
   - prompt de "só fatos dos dados", até 120 palavras, sem markdown, com uma autoavaliação e uma regeneração (implementar de verdade; no OpenJarvis esse passo nunca chega a rodar);
   - entregue por voz, numa notificação do Windows e por push no iPhone (etapa 8);
   - **Clima:** Open-Meteo, grátis e sem chave. Pede consentimento na primeira vez, porque é uma consulta à internet; a cidade vem da configuração.
3. **Falar por conta própria, sem incomodar** (`mk/actions/proactive.py` L37-42):
   - só depois de 15 min de silêncio, com intervalo mínimo de 20 min;
   - nunca interrompe, alterna os temas, pode ficar quieta;
   - **horário de silêncio** (padrão 22h-8h) e limite diário (padrão 4);
   - desligado por padrão.
4. **Acompanhar tópicos** (`mk/actions/background_monitor.py` L134-141): uma checagem diária na busca, avisando só quando a manchete principal muda.
5. **Alertas do PC** (`mk/actions/system_monitor.py` L13-21 e L154-200):
   - CPU acima de 90% por 3 leituras seguidas, RAM acima de 90%, temperatura acima de 85 °C, GPU;
   - 5 min de intervalo entre alertas por métrica;
   - quieta enquanto você fala;
   - opcional.
6. Aba **Rotinas** na interface: rotinas, lembretes, horário do resumo, horário de silêncio, tópicos, alertas.

Testes:
- o agendador com relógio falso;
- o horário de silêncio e o limite diário barram;
- o resumo sem dados não inventa;
- as rotinas respeitam o modo de permissão.

## Etapa 7 — escolha automática de modelo

`oj/learning/routing/complexity.py` L117-223, `router.py` L144-181, `learned_router.py`:
- **Pontuação 0-1 por regras em pt-BR:**
  - tamanho do pedido;
  - código ou matemática;
  - raciocínio em várias etapas;
  - quantidade de perguntas;
  - pedido criativo.
- **Escolha "Automático" no seletor:**
  - pontuação baixa ou ação simples → 4B;
  - média → 9B;
  - alta ou várias etapas → 9B com plano (`tasks`), ou o Claude se estiver configurado. A nuvem sempre passa pela prévia de consentimento; nada vai para ela sozinho.
- **Game Mode:** força o 4B na CPU.
- **Ajuste pelo histórico:** depois de 5 amostras por tipo de pedido, uma tabela `routing_stats` (sucesso das ações, avaliações) refina a escolha.
- **Visibilidade:** a escolha aparece na mensagem ("respondido pelo 9B · motivo").

Testes: pontuação dos exemplos; o Game Mode força o 4B; a nuvem nunca é escolhida sem consentimento.

## Etapa 8 — iPhone sem App Store (Tailscale + PWA)

Referências: `oj/` (`frontend/vite.config.ts` L25-42, `server/app.py` L539-560, `server/auth_middleware.py` L104-124) e o fluxo de QR do `mk/dashboard/server.py`, **só a ideia**.

1. **Gateway remoto** (`backend/remote/`, novo):
   - um segundo app FastAPI em `127.0.0.1:47823`, separado da API do desktop e do token dela;
   - serve a PWA e um conjunto pequeno de rotas: conversar (stream), anexos, transcrever, falar (WAV), cartões pendentes (aprovar ou recusar), status;
   - verifica `Origin` e `Host`; limite de tentativas em todas as rotas de autenticação.
   - **Política do celular:**
     - toda ação vinda do celular vira cartão, sem execução automática;
     - `run_command` só é aprovado no PC;
     - sem acesso a arquivos fora do workspace.
2. **Tailscale**:
   - Controle e regras → "Celular" detecta `tailscale status --json`;
   - com o consentimento do usuário, roda `tailscale serve --bg --https=443 http://127.0.0.1:47823` (só na tailnet, **nunca** `funnel`);
   - mostra a URL `https://<pc>.<tailnet>.ts.net`;
   - o "Desligar" roda `tailscale serve reset`;
   - sem Tailscale instalado: instruções e link para baixar.
3. **Pareamento**:
   - QR code com a URL e um código de uso único, válido por 2 min, no `#fragmento`, que nunca vai para logs;
   - a troca devolve um token por aparelho, guardado com hash no SQLite, num cookie `Secure; HttpOnly; SameSite=Strict`, com validade de 30 dias renovável;
   - lista de aparelhos com nome e último acesso, e revogar um por um.
4. **PWA**:
   - build separado do React, com layout de celular, `manifest`, `apple-touch-icon` e service worker que não guarda a API em cache;
   - "Adicionar à Tela de Início" no Safari;
   - microfone do iPhone grava PCM e manda para `/transcribe`;
   - a resposta toca no iPhone (WAV da voz Dora) ou no PC, à escolha.
5. **Notificações** (iOS 16.4+, PWA na Tela de Início):
   - Web Push com VAPID (`pywebpush`, opcional) para o resumo da manhã, lembretes e cartões pendentes;
   - o conteúdo da notificação é curto; o detalhe fica no app.
6. Documento `docs/IPHONE.md` com o passo a passo para o usuário: instalar o Tailscale nos dois, parear e adicionar à Tela de Início.

Testes:
- o gateway recusa o token do desktop e vice-versa;
- o código de pareamento vale uma vez só e expira;
- o celular não executa nada sozinho;
- `run_command` não é aprovável remotamente;
- `Origin` errada recebe 403;
- o limite de tentativas funciona;
- revogar derruba a sessão.

## Etapa 9 — validação real, documentação, instalador e GitHub

Pendência acrescentada pelo usuário durante o teste no PC: validar os três botões da tela **Sobre** (Versões e instaladores, Procurar nova versão e Verificar atualização baixada) no aplicativo instalado, com a release correta e o manifesto verificado. Atualizar também o texto da tela, que ainda diz que voz/GUI genérica estão apenas no roteiro. Não marcar como pronto só porque a interface mostra os botões.

Checkpoint solicitado: manter no GitHub uma lista do que terminou, do que foi testado e do que falta. O agente não tem acesso confiável ao percentual de créditos/contexto do cliente; não inventar detecção dos 2%. Antes de encerrar uma rodada, atualizar `docs/CHECKPOINT-0.5.md` e publicar os fontes sem dados locais, modelos ou credenciais.

1. **Smoke real** com o Ollama, nos modelos 4B e 9B, com `scripts/smoke_full_access.py` ampliado:
   - casos atuais;
   - `windows_keys` no Chrome;
   - nome de programa errado (correção);
   - "olha minha tela";
   - volume;
   - lembrete;
   - "já está aberto" foca;
   - anexo de print e de PDF;
   - com e sem os exemplos aprendidos;
   - resultado em `docs/full-access-smoke.json`.
2. **Voz real**:
   - WAV da SAPI pelo pipeline;
   - medir o tempo até o primeiro áudio da Dora e a latência de ouvir → primeira palavra falada;
   - falsos positivos do "Hey Jarvis" com 15 min de áudio comum.
3. **App** (`npm.cmd run dev`), à mão:
   - segurar para falar;
   - palavra de ativação;
   - cortar a fala;
   - colar um print;
   - Game Mode conversando;
   - resumo da manhã forçado;
   - pareamento do iPhone pelo Tailscale (se o usuário tiver instalado).
4. **Regras dos testes:**
   - fechar só processos abertos por mim, pelo PID (nunca `taskkill /IM`);
   - não mexer nos dados reais do usuário: usar uma pasta temporária.
5. **Versão e documentação:**
   - **0.5.0** em `package.json`, `package-lock.json`, `backend/maintenance.py` e `api.py`;
   - atualizar `docs/STATUS.md`, `docs/SECURITY.md` (microfone no backend, gateway remoto, taint, sempre permitir, desfazer, lembretes, nuvem), `backend/voice/README.md` e `docs/IPHONE.md`.
6. **Instalador:**
   - `npm.cmd run dist`, depois `release:manifest` (a chave `.local/update-private-key.pem` nunca é publicada), depois `scripts/smoke_packaged.py`;
   - conferir se o PyInstaller levou ctranslate2, onnxruntime, av, sounddevice, openwakeword e kokoro;
   - informar o tamanho.
7. **GitHub:**
   - commits por etapa em `work/0.5`, depois `git merge origin/main` e push;
   - merge no `main` com `git push origin work/0.5:main`; se houver proteção, passar o link do PR (não há `gh`).
8. **Assinatura de código:** explicar as opções ao usuário (Azure Trusted Signing, certificado OV), porque não dá para fazer daqui.

## Fora do plano, de propósito

- O avatar holográfico com sincronia labial do Mark-LVI: muito grande e pouco ligado ao que falta.
- O painel automático da área de transferência: manda ao modelo tudo o que você copia.
- O aprendizado com retreino de modelo (LoRA): pesado demais para 8 GB.
- Os conectores de Mac.
- O Telegram: recusado pelo usuário.

## Respostas já dadas ao usuário

- **Arquivos:**
  - programa em `%LOCALAPPDATA%\Programs\ALT-AI`;
  - dados em `%APPDATA%\ALT-AI\data`;
  - modelos em `%USERPROFILE%\.ollama\models`;
  - código em `C:\Users\caios\ALT-`.
- **GPU:** os 4 tok/s eram a GPU dividida com o jogo. Respostas curtas e o Game Mode na CPU resolvem.
- **Anexos:** o clipe nunca tinha sido implementado.
