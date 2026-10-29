# Solução de problemas

## O botão enviar não está disponível

Abra Inteligências, atualize a lista e selecione um modelo instalado. Se STOP estiver ativo, retome. Confira se o campo contém texto. A versão atual seleciona o primeiro modelo local quando ainda não há preferência e atualiza a descoberta ao voltar para a janela e a cada 10 segundos visíveis.

## Ollama offline

Abra o Ollama. O serviço precisa responder em `http://127.0.0.1:11434`. O app não configura exposição na rede. Não é necessário escolher Claude Code/Codex/OpenCode na página Apps do Ollama para a ALT-AI funcionar.

## Resposta demora

O primeiro pedido carrega pesos em RAM/VRAM e pode levar mais tempo. Confira Sistema e os logs do Ollama; CPU pode ser significativamente mais lenta. O chat Qwen 3.5 desativa raciocínio interno nesta versão. A janela mostra processamento até chegar conteúdo real, sem resposta fictícia. Interrompa pelo quadrado ou STOP. Não é necessário disparar mensagens repetidas, pois elas podem entrar em fila no Ollama.

Em notebook, use Automático ou Notebook econômico em Comportamento. O limite de saída menor pode encerrar textos longos; peça continuação quando necessário. O perfil reduz contexto e threads, mas não garante baixa temperatura ou aceleração de GPU. Qwen 2B é opcional para tarefas mais leves. O perfil desktop permanece para o Ryzen/RX 7600 do computador principal.

## Modelo 9B / GPU

Comece pelo 4B. O 9B é opcional. O tamanho em disco não equivale à memória total de inferência. Não trocar drivers nem forçar overrides de GPU sem diagnóstico. O coletor mostra nome/driver da GPU e alocação de modelos quando informada pelo Ollama; uso/temperatura/VRAM total ainda podem estar indisponíveis.

## Janela sumiu

Use Ctrl+Shift+Espaço ou o ícone da bandeja. O × oculta; para encerrar use Sair. Atalhos globais podem estar ocupados por outro programa.

## Falha de inicialização

Verifique `backend.log` dentro de `%APPDATA%/ALT-AI` ou `%APPDATA%/alt-ai`. Não publique logs sem revisar dados. A instalação inclui o runtime Python; no desenvolvimento é necessário criar `.venv`. `npm.cmd start` remove `ELECTRON_RUN_AS_NODE` herdado de IDEs para iniciar o Electron como aplicativo.

## Continuar desenvolvimento

Leia HANDOFF.md, confirme `git status` e use o clone mais recente. Não envie `.env`, bancos, logs ou credenciais ao Git. Locks estão versionados para instalação reproduzível.

## Prévia 0.2

Clique no círculo inferior para abrir Perfil. Personalidade fica em Configurações; memória no ícone de cérebro. Para ações pelo chat, selecione um modelo Ollama/Qwen, peça a ação e revise o cartão. Ative a sessão correspondente em Ferramentas. Codex nesta prévia usa conversa/código com seus executores desligados.

Pesquisa usa HTTPS público sem cookies/JavaScript. Página com login ou renderização obrigatória por JS pode falhar; isso não indica que o chat local precisa de internet. O perfil amplo exclui AppData/credenciais/sistema e não equivale a controle de mouse/teclado de qualquer programa.

A versão 0.2 corrige o estouro de contexto ao analisar resultados: ajusta o trecho em bytes ao espaço livre, preserva URLs inteiras e mantém o resultado completo no cartão. A personalidade e as memórias escolhidas são preservadas. Se a própria mensagem com suas instruções/memórias exceder o perfil, reduza esses itens ou escolha Desktop. O primeiro pedido com personalidade/ferramentas pode levar dezenas de segundos na CPU deste notebook.

Depois de atualizar o código ou instalar uma versão nova, encerre de verdade em Sobre → Sair da ALT-AI e reabra. O × apenas oculta na bandeja; não reinicia o backend. Uma janela antiga continua com o comportamento anterior até ser encerrada.

Para atualizações verificadas, baixe o instalador e o manifesto da mesma release e use Sobre → Verificar atualização baixada. Versão igual/antiga ou conteúdo modificado é recusado. A primeira instalação 0.2 é manual; 0.1 ainda não tem esse verificador.

## Controle, navegador e memória — 0.3

Em Controle e regras, edite suas regras e decisões por capacidade e confirme a revisão nativa. Permitir automaticamente atua nos modos 3/4; Assistido continua pedindo revisão individual e Observação não executa. As regras e o modo ficam salvos sem contagem de minutos.

No Navegador ALT, prepare a abertura, revise o cartão e aprove. A janela é separada do navegador pessoal. Depois de mudar de página/elementos, faça nova leitura antes de clicar/digitar. Campos protegidos precisam de preenchimento manual; não há automação de senhas/CAPTCHA ou download. STOP/Modo Jogo interrompem a navegação. Em erro de DNS/TLS, não contornar o bloqueio nem desativar proteção do Windows.

Registre aplicativos pelo seletor .exe em Controle. Após atualização do executável, registre novamente se o hash mudou. A solicitação de fechamento é normal e só alcança processos rastreados pela ALT; apps que repassam a janela a outro processo podem não fechar. Não forçar encerramento de documentos.

Em Memória, abra Resumo de continuidade, escolha conversa e modelo local, gere o rascunho, revise e salve. Uma conversa alterada exige resumo novo. Importação aceita JSON exportado da ALT; valida antes de inserir e ignora duplicatas. A recuperação automática é por termos relacionados, não busca semântica, e é ativada em Controle. O chat informa quais memórias entraram.

Em Inteligências, o Laboratório compara modelos locais instalados com prompts sintéticos. Carregamento em CPU pode levar dezenas de segundos e a rodada pode durar minutos. Limite de saída atingido não é resposta completa: veja o indicador. Notas são suas, não classificação automática. Huihui foi baixado e testado neste PC com consentimento; no outro PC os pesos precisam de download separado.
