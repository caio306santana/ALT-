# Estado atual e próximos passos — ALT-AI

Atualizado em 29/10/2026. Este é o ponto de entrada para retomar o projeto em outro PC.

## Versões

| Versão | Onde está | Estado |
| --- | --- | --- |
| 0.3.1 | `main` | Correção do chat (contexto Qwen, propostas sem prazo, aprovação no chat). **Instalada e em uso neste notebook.** Release no GitHub ainda em rascunho. |
| 0.4.0 | `work/advanced-0.4` | Etapas 2, 3 e 5 integradas, modo Acesso total, aviso de atualização e novo design. Instalador gerado para teste local (ver abaixo). Ainda não mesclada em `main`. |

## O que a 0.4.0 entrega

| Entrega | O que faz | Evidência |
| --- | --- | --- |
| 2 — Tarefas com várias ações | Tela **Tarefas**: o modelo local planeja; você revisa ou edita; a ALT executa e confere cada passo; pausar e retomar sem repetir ações. O plano recebe só as ferramentas que o objetivo pede. Uma rodada automática corrige plano incompleto (ex.: arquivo sem nome). Arquivos ficam na pasta escolhida para a tarefa. | Testes automatizados e smoke real com Qwen 3.5 4B ([agent-stages-smoke.json](agent-stages-smoke.json)). |
| 3 — Memória semântica, documentos e projetos | Projetos; importar PDF, DOCX, TXT e MD; documentos divididos por título e parágrafo; busca por significado com EmbeddingGemma (prompts recomendados do modelo); "Recuperação semântica" no chat, com volta para busca por termos; resumos por projeto sempre revisados antes de virar memória. | Smoke real: 4/4 buscas corretas; o chat respondeu com o trecho certo do documento. |
| 5 — Confiabilidade e personalidade | Cada resposta do chat é conferida: contas escritas são recalculadas, e links que não vieram de pesquisa real são sinalizados. Mensagens com sinais claros de momento difícil recebem instrução explícita de acolhimento. Laboratório com casos reais e verificações automáticas. | Smoke real dos casos de personalidade; testes automatizados. Avaliação humana do tom continua com o usuário. |
| Acesso total (modo 4) | Tudo que não estiver bloqueado em Controle e regras executa sem aprovação: internet, downloads (nova ferramenta), arquivos em qualquer pasta local, apps, navegador e tarefas. Versões anteriores de arquivos sobrescritos ficam em `file-history`. Sempre fora: credenciais/AppData, compartilhamentos de rede, shell, administrador, executar arquivos baixados. STOP revoga tudo. | Testes automatizados. |
| Aviso de nova versão | Ao abrir (e a cada 6 h), consulta a última release do GitHub, mostra as **notas da versão**, baixa, confere a assinatura Ed25519 e o SHA-256 e oferece "instalar e reiniciar". | Teste Node com release simulada. |
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

A release precisa ser **publicada** (não rascunho), com tag `vX.Y.Z` e os arquivos `ALT-AI-Setup-X.Y.Z-x64.exe` e `ALT-AI-X.Y.Z-update.json`.

## O que falta

| Item | O que falta |
| --- | --- |
| Assinatura Windows | Certificado de assinatura de código para o instalador e o backend; sem ele, executáveis novos podem ser bloqueados. |
| 4 — Controle de janelas Windows | Driver UI Automation existe (`backend/tools/windows_ui.py`), mas faltam seletor nativo de janela, painel e testes numa janela própria. |
| 6 — Backup e restauração | `backend/maintenance.py` existe sem interface; migrações automáticas já rodam com backup. |
| Tarefas | Testar tarefas longas com navegador ALT; editor de plano ainda é JSON. |
| Documentos | Validar PDFs longos e DOCX reais; PDFs digitalizados precisam de OCR (não incluído). |
| Personalidade | Avaliação humana em uso real; as verificações automáticas são heurísticas. |
| PC principal | Testar no Ryzen 9 3900 / RX 7600 e em Windows limpo; medir desempenho com GPU. |
| `main` | Mesclar `work/advanced-0.4` em `main` depois da revisão do dono. |

## Continuidade em outro PC

Fontes, locks, testes e documentação estão no repositório. O [README](../README.md#desenvolver-no-outro-pc) contém a preparação do ambiente; [HANDOFF.md](HANDOFF.md) registra decisões e histórico; [PROGRESS-0.4.md](PROGRESS-0.4.md) detalha a 0.4. Usar `git switch --track origin/work/advanced-0.4` para continuar.

Dados pessoais, bancos SQLite, logs, modelos e credenciais ficam fora do Git. Preservar a chave privada de atualização (`.local/update-private-key.pem`) em backup privado para assinar versões futuras. Não há acesso confiável ao percentual de uso da sessão do agente: fazer checkpoints frequentes.
