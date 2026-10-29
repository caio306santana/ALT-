# Solução de problemas

## O botão enviar não está disponível

Abra Inteligências, atualize a lista e selecione um modelo instalado. Se STOP estiver ativo, retome. Confira se o campo contém texto. A versão atual seleciona o primeiro modelo local quando ainda não há preferência e atualiza a descoberta ao voltar para a janela e a cada 10 segundos visíveis.

## Ollama offline

Abra o Ollama. O serviço precisa responder em `http://127.0.0.1:11434`. O app não configura exposição na rede. Não é necessário escolher Claude Code/Codex/OpenCode na página Apps do Ollama para a ALT-AI funcionar.

## Resposta demora

O primeiro pedido carrega pesos em RAM/VRAM e pode levar mais tempo. Confira Sistema e os logs do Ollama; CPU pode ser significativamente mais lenta. O chat Qwen 3.5 desativa raciocínio interno nesta versão. A janela mostra processamento até chegar conteúdo real, sem resposta fictícia. Interrompa pelo quadrado ou STOP. Não é necessário disparar mensagens repetidas, pois elas podem entrar em fila no Ollama.

## Modelo 9B / GPU

Comece pelo 4B. O 9B é opcional. O tamanho em disco não equivale à memória total de inferência. Não trocar drivers nem forçar overrides de GPU sem diagnóstico. O coletor mostra nome/driver da GPU e alocação de modelos quando informada pelo Ollama; uso/temperatura/VRAM total ainda podem estar indisponíveis.

## Janela sumiu

Use Ctrl+Shift+Espaço ou o ícone da bandeja. O × oculta; para encerrar use Sair. Atalhos globais podem estar ocupados por outro programa.

## Falha de inicialização

Verifique `backend.log` dentro de `%APPDATA%/ALT-AI` ou `%APPDATA%/alt-ai`. Não publique logs sem revisar dados. A instalação inclui o runtime Python; no desenvolvimento é necessário criar `.venv`. `npm.cmd start` remove `ELECTRON_RUN_AS_NODE` herdado de IDEs para iniciar o Electron como aplicativo.

## Continuar desenvolvimento

Leia HANDOFF.md, confirme `git status` e use o clone mais recente. Não envie `.env`, bancos, logs ou credenciais ao Git. Locks estão versionados para instalação reproduzível.
