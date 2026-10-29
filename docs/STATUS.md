# Estado atual e próximos passos — ALT-AI

Atualizado em 29/10/2026. Este é o ponto de entrada para retomar o projeto em outro PC.

## Versões

| Versão | Onde está | Estado |
| --- | --- | --- |
| 0.3.1 | `main` | Correção do chat (contexto Qwen, propostas sem prazo, aprovação no chat). **Instalada e em uso neste notebook.** Release no GitHub ainda em rascunho. |
| 0.4.2 | `work/0.4.2` | Personalidade Alt + JARVIS, acesso total de verdade (qualquer programa pelo nome, sites no navegador padrão, janelas sem autorizar uma a uma, PowerShell com cartão), botão de Acesso total no chat e STOP visível. Testada no PC principal (Ryzen 9 3900 / RX 7600). Instalador ainda não gerado. |
| 0.4.0 | `work/advanced-0.4` | Etapas 2, 3 e 5 integradas, modo Acesso total, aviso de atualização e novo design. Instalador gerado, manifesto Ed25519 conferido e backend empacotado testado neste notebook **sem bloqueio do Windows**. [Release v0.4.0 em rascunho](https://github.com/caio306santana/ALT-/releases) com instalador, manifesto e SHA256. Cópia em `Downloads\ALT-AI-0.4.0`. Ainda não mesclada em `main`. |

## O que a 0.4.2 entrega (PC principal, 29/10/2026)

Motivo: pedindo "abra uma nova aba no google", a ALT abriu o Bloco de Notas depois de um discurso questionando o pedido, e depois disse não ter permissões com o modo 4 ligado. Causas: tom padrão "provocadora, irônica e desafiadora" com frases de debate fixas (ignoravam os controles), roteamento por palavra-chave ("abra" oferecia só `open_app`), `app` com padrão `notepad` e só dois apps conhecidos.

| Entrega | O que faz |
| --- | --- |
| Personalidade Alt + JARVIS | Novo padrão: direta, calma, obedece primeiro e confirma em uma frase. Ironia só com o controle ≥ 40 e debate só com ≥ 60 ou quando o usuário pede opinião. Instalações com o tom antigo migram sozinhas; tom personalizado é preservado. |
| Roteamento de ferramentas | Nos modos 3 e 4, abrir site e abrir programa são oferecidos em toda mensagem. "navegador" sozinho é o navegador do usuário; o navegador ALT entra quando já há página aberta nele ou quando o pedido diz "navegador ALT". `app` não tem mais padrão: sem nome, a proposta é recusada. |
| Qualquer programa instalado | `backend/tools/app_catalog.py`: lê o Menu Iniciar (.lnk) e `Get-StartApps` (apps da Store), resolve pelo nome falado (chrome → Google Chrome) e abre sem registro. Neste PC: 191 programas. Fora do modo 4 continua valendo o registro por hash. |
| Sites no navegador padrão | `open_url` aceita `youtube.com` sem esquema e só a pesquisa (vira busca no Google). O prompt informa o navegador padrão lido do registro (aqui, Google Chrome). |
| Janelas no modo 4 | `windows_read/invoke/type` aceitam o título ou o programa de qualquer janela aberta; exclusões (terminais, UAC, gerenciadores de senha, campos de senha, a própria ALT) continuam. |
| PowerShell | Ferramenta `run_command` e capacidade `shell`: roda como usuário comum, 60 s de limite, saída até 8 KB, STOP mata o processo. **Sempre** pede aprovação no cartão, inclusive no modo 4. Fechar programa que a ALT não abriu também pede. |
| Interface | Botão "Acesso total" ao lado da caixa de texto (borda vermelha enquanto ligado); STOP ALL ACTIONS virou botão de verdade; saíram "Enter para enviar" e "Processamento local pelo Ollama"; ações simples concluídas viram uma linha ("✓ Spotify aberto"); Controle e regras mostra os programas detectados no modo 4. |

Testes: 111 testes Python passaram (1 ignorado, symlink), testes Node e build TypeScript/Vite passaram. Smoke real `scripts/smoke_full_access.py` (dry run, nada executado) em [full-access-smoke.json](full-access-smoke.json): **10/10 com Qwen 3.5 4B e 10/10 com Qwen 3.5 9B** (sites, programas, pesquisa, comando com cartão, fechar com cartão, conversa sem debate). Execução real conferida: aba do Google no Chrome, Calculadora pelo catálogo, `Get-Date` com acentuação, STOP encerrando `Start-Sleep 30` em 2 s.

Desempenho na RX 7600 (Ollama 0.40.13, 100% GPU): Qwen 3.5 4B ~56 tokens/s (3,1 GB); Qwen 3.5 9B ~17 tokens/s (5,7 GB com contexto 8k), cerca de 5 s por ação.

Risco conhecido do modo 4: texto de sites e janelas pode tentar enganar o modelo (prompt injection) e virar ações sem revisão; comandos e fechamentos continuam com cartão e o STOP fica sempre visível.

## O que a 0.4.0 entrega

| Entrega | O que faz | Evidência |
| --- | --- | --- |
| 2 — Tarefas com várias ações | Tela **Tarefas**: o modelo local planeja; você revisa ou edita; a ALT executa e confere cada passo; pausar e retomar sem repetir ações. O plano recebe só as ferramentas que o objetivo pede. Uma rodada automática corrige plano incompleto (ex.: arquivo sem nome). Arquivos ficam na pasta escolhida para a tarefa. | Testes automatizados e smoke real com Qwen 3.5 4B ([agent-stages-smoke.json](agent-stages-smoke.json)). |
| 3 — Memória semântica, documentos e projetos | Projetos; importar PDF, DOCX, TXT e MD; documentos divididos por título e parágrafo; busca por significado com EmbeddingGemma (prompts recomendados do modelo); "Recuperação semântica" no chat, com volta para busca por termos; resumos por projeto sempre revisados antes de virar memória. | Smoke real: 4/4 buscas corretas; o chat respondeu com o trecho certo do documento. |
| 5 — Confiabilidade e personalidade | Cada resposta do chat é conferida: contas escritas são recalculadas, e links que não vieram de pesquisa real são sinalizados. Mensagens com sinais claros de momento difícil recebem instrução explícita de acolhimento. Laboratório com casos reais e verificações automáticas. | Smoke real dos casos de personalidade; testes automatizados. Avaliação humana do tom continua com o usuário. |
| Acesso total (modo 4) | Tudo que não estiver bloqueado em Controle e regras executa sem aprovação: internet, downloads (nova ferramenta), arquivos em qualquer pasta local, apps, navegador e tarefas. Versões anteriores de arquivos sobrescritos ficam em `file-history`. Sempre fora: credenciais/AppData, compartilhamentos de rede, shell, administrador, executar arquivos baixados. STOP revoga tudo. | Testes automatizados. |
| Aviso de nova versão | Ao abrir (e a cada 6 h), consulta a última release do GitHub, mostra as **notas da versão**, baixa, confere a assinatura Ed25519 e o SHA-256 e oferece "instalar e reiniciar". | Teste Node com release simulada. |
| 4 — Controle de janelas do Windows | Em Ferramentas → "Janelas do Windows autorizadas": escolha uma janela aberta e confirme no diálogo nativo. A ALT lê botões e campos (senhas ignoradas; terminais, janelas de segurança e a própria ALT excluídos), clica e digita pelo mesmo caminho de propostas e aprovações; leitura antiga é recusada. O chat recebe as janelas autorizadas e a última leitura; tarefas podem usar uma janela. | Teste real em `scripts/smoke_windows_ui.py` com o Mapa de Caracteres aberto pelo teste ([windows-ui-smoke.json](windows-ui-smoke.json)): leu 21 elementos, digitou, marcou uma caixa (11 controles novos apareceram) e recusou leitura desatualizada. Corrigidos: erro de modo COM, editor tipo Document (Bloco de Notas do Windows 11) e quebra de linha no valor do campo. |
| 6 — Backup e restauração | Em Sistema → "Backup e restauração": exportar um ZIP (com hash) para levar a outro PC e restaurar com validação. Antes de restaurar, a ALT guarda uma cópia dos dados atuais; autorizações de pastas e janelas são zeradas e o app reinicia. Backup automático diário (últimos 7). Chaves de API nunca entram. | Teste automatizado de ida e volta. Corrigido: conexões SQLite que ficavam abertas e travavam os arquivos no Windows. |
| Design | Barra lateral com nomes, conversas recentes, recolhível; cabeçalho único; menos brilhos e cantos cortados; textos maiores; os temas e cores continuam. | Capturas do smoke visual (`node scripts/run-chat-ui-smoke.mjs`, imagens em `.local/`). |

Também: `pypdf`, `python-docx` e `lxml` entraram nos requisitos (antes faltariam no pacote).

## Testes desta rodada

- 95 testes Python passaram (1 ignorado por privilégio de symlink); testes Node passaram; TypeScript/Vite compilou; smoke visual do renderer passou.
- Smoke real em `scripts/smoke_agent_stages.py` (Qwen 3.5 4B + EmbeddingGemma, perfil Notebook, CPU). Resultados e respostas completas em [agent-stages-smoke.json](agent-stages-smoke.json).

Resultados do smoke real (última rodada):

| Verificação | Resultado |
| --- | --- |
| Busca semântica | 4/4 consultas com o item certo em primeiro (antes da divisão por seções: 3/4). |
| Chat com recuperação semântica | Respondeu "22h, terminal 2, adaptador tipo F" a partir do documento; 49 s. |
| Tarefa de 3 passos planejada pelo Qwen | Concluída e conferida (calcular, gravar, ler); 78 s. |
| Pausar e retomar | Numa rodada anterior, retomou sem repetir ações. Na última, a tarefa parou antes da pausa porque o modelo pôs "listar arquivos" com caminho de arquivo; o validador de plano agora pede correção nesse caso. Repetir o teste. |
| Desabafo ("perdi meu emprego") | Antes: ironia e lição. Depois da instrução de acolhimento: resposta acolhedora, sem debate. |
| Fontes sem internet | **Falhou:** o modelo disse ter internet e listou fontes. A verificação automática detectou; no chat, links não confirmados aparecem marcados. |
| Contas no meio do texto | **Variável:** numa rodada acertou (R$ 105 / R$ 735), na seguinte errou em prosa ("12,5% é um quarto"); a conferência só pega contas escritas como expressão. |
| Pedido prático | Lista correta, mas passou do limite de palavras e abriu com comentário irônico. |

Conclusão: a infraestrutura das etapas 2, 3 e 5 funciona com o modelo real; a qualidade do Qwen 4B ainda varia entre rodadas, principalmente em fontes e contas em prosa.

## Instalar a 0.4.0 neste notebook

O instalador e o manifesto assinado ficam em `C:\Users\prici\Downloads\ALT-AI-0.4.0\`.

1. Na ALT aberta: Sobre → **Sair da ALT-AI** (o × só esconde na bandeja).
2. Execute `ALT-AI-Setup-0.4.0-x64.exe`. Conversas, memórias e configurações são preservadas; antes de atualizar o banco a ALT salva um backup em `%APPDATA%\alt-ai\data\backups`.
3. O **Controle Inteligente de Aplicativos** do Windows está ligado e pode bloquear o instalador ou o backend novo, porque não têm assinatura digital (aconteceu com a 0.3.1 recém-gerada). Nenhuma proteção foi alterada pelo agente. Se bloquear, as opções são: certificado de assinatura de código, ou o dono decidir sobre essa proteção do Windows.

## Aviso de atualização e repositório privado

O aviso consulta `releases/latest` do GitHub sem login. Com o repositório **privado**, o app não enxerga as releases e informa isso. Para funcionar, uma das opções:

- tornar este repositório público (decisão do dono, depois de revisar), ou
- publicar só os instaladores num repositório público separado e apontar `ALT_UPDATE_FEED` / a constante em `apps/desktop/electron/update-feed.cjs` para ele.

A release precisa ser **publicada** (não rascunho), com tag `vX.Y.Z` e os arquivos `ALT-AI-Setup-X.Y.Z-x64.exe` e `ALT-AI-X.Y.Z-update.json`. Publicar como release normal, não *pre-release*: o GitHub não devolve pre-releases em `releases/latest`.

Instalador 0.4.0: `ALT-AI-Setup-0.4.0-x64.exe`, 139.882.074 bytes, SHA256 `a36673b5060d3ee70e478c3108e08c6ea6bc688e7a90516e63d55efe5bf38d3b`. A checagem de plano que recusa “listar arquivos” com caminho de arquivo entrou depois deste build e vai na próxima versão.

## Próximo passo imediato (sessão encerrada perto do limite)

O código da **0.4.1** (etapa 4 — janelas do Windows, backup/restauração na interface e as correções do teste real) está completo e testado em `work/advanced-0.4` (98 testes Python passando), mas **o instalador 0.4.1 ainda não foi gerado**. A release v0.4.0 em rascunho não contém a etapa 4 nem o backup.

Para gerar e publicar o rascunho:

```powershell
npm.cmd run dist
npm.cmd run release:manifest
.venv\Scripts\python.exe scripts\smoke_packaged.py
gh release create v0.4.1 release\ALT-AI-Setup-0.4.1-x64.exe release\ALT-AI-0.4.1-update.json release\SHA256SUMS.txt --draft --target work/advanced-0.4 --title "ALT-AI 0.4.1"
```

Último teste real de janela: o Qwen planejou ler e digitar no Mapa de Caracteres, mas deixou o texto vazio; o validador agora exige o texto (e o alvo) antes da revisão. Repetir `scripts/smoke_windows_ui.py` depois do build.

## O que falta

| Item | O que falta |
| --- | --- |
| Assinatura Windows | Certificado de assinatura de código para o instalador e o backend; sem ele, executáveis novos podem ser bloqueados. |
| Janelas do Windows | Testar com mais aplicativos reais; apps que não expõem acessibilidade (alguns jogos e apps antigos) não podem ser controlados. Tarefas planejadas pelo Qwen em janelas ainda precisam de mais validação. |
| Tarefas | Testar tarefas longas com navegador ALT; editor de plano ainda é JSON. |
| Documentos | Validar PDFs longos e DOCX reais; PDFs digitalizados precisam de OCR (não incluído). |
| Personalidade | Avaliação humana em uso real; as verificações automáticas são heurísticas. |
| PC principal | Testar no Ryzen 9 3900 / RX 7600 e em Windows limpo; medir desempenho com GPU. |
| `main` | Mesclar `work/advanced-0.4` em `main` depois da revisão do dono. |

## Continuidade em outro PC

Fontes, locks, testes e documentação estão no repositório. O [README](../README.md#desenvolver-no-outro-pc) contém a preparação do ambiente; [HANDOFF.md](HANDOFF.md) registra decisões e histórico; [PROGRESS-0.4.md](PROGRESS-0.4.md) detalha a 0.4. Usar `git switch --track origin/work/advanced-0.4` para continuar.

Dados pessoais, bancos SQLite, logs, modelos e credenciais ficam fora do Git. Preservar a chave privada de atualização (`.local/update-private-key.pem`) em backup privado para assinar versões futuras. Não há acesso confiável ao percentual de uso da sessão do agente: fazer checkpoints frequentes.
