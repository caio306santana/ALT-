# ALT-AI

Assistente pessoal Windows com modelos locais pelo Ollama, memória, voz, ferramentas e cliente para iPhone. ALT é o aplicativo/agente e sua identidade; Qwen e os demais motores são modelos de terceiros.

**Hermes 3:** a 0.5.1 acrescenta as opções locais 3B e 8B. O download é opcional e ficou para depois por escolha do dono. Ver [uso, requisitos e validação](docs/HERMES.md). Built with Meta Llama 3.

**Estado atual:** código **0.5.1** em `main`, corrigindo o bloqueio falso de contexto no Automático e limitando observações auxiliares. Código/renderer testados; pacote em validação. Ver [correção 0.5.1](docs/CHAT_CONTEXT_0.5.1.md). A [release v0.5.0](https://github.com/caio306santana/ALT-/releases/tag/v0.5.0) permanece publicada com instalador e manifesto originais; ela ainda não contém esse ajuste. [STATUS.md](docs/STATUS.md) registra as evidências e pendências. Assinar o manifesto não instala a atualização nem substitui Authenticode.

## O que a 0.5 inclui

- Chat com streaming, histórico local, anexos de imagem/PDF com OCR/Word/texto e resultados de ferramentas voltando ao modelo na mesma resposta.
- Tarefas com várias ações, verificações de resultado, pausa/retomada e reparo de escolha de ferramenta.
- Memórias revisadas pelo usuário, projetos, documentos e recuperação semântica local com EmbeddingGemma.
- Ferramentas para arquivos, navegador, programas, janelas, tela, volume/brilho/música e lembretes, conforme o modo e as permissões escolhidos.
- Voz local com Whisper e Dora pt-BR, Ctrl+Espaço, "Hey Jarvis" e "Ei ALT" experimental; precisa de microfone funcional e modelos configurados.
- Rotinas, resumo da manhã, tópicos, alertas, modelo automático, Game Mode e ajustes de uso da GPU/cache de prompt.
- Backup/restauração e verificação de atualização por manifesto Ed25519, SHA256 e versão.
- Gateway e PWA para iPhone com Tailscale e pareamento por QR. A inteligência continua no PC; a configuração entre os aparelhos ainda precisa de validação no destino.

Personalidade atual: Alt + JARVIS, direta e calma, com tom/ironia/debate ajustáveis. O modelo ainda pode errar cálculos, fontes, interpretação e escolha de ações. As evidências e os limites estão em [CHECKPOINT-0.5.md](docs/CHECKPOINT-0.5.md).

## Instalar e usar

1. Baixar `ALT-AI-Setup-0.5.0-x64.exe` na [release 0.5.0](https://github.com/caio306santana/ALT-/releases/tag/v0.5.0). O manifesto `ALT-AI-0.5.0-update.json` verifica esse instalador pelo atualizador da ALT.
2. Para atualizar, sair da ALT em Sobre → **Sair da ALT-AI**, preservando os dados/backup antes de prosseguir. O × pode apenas ocultar a janela na bandeja.
3. Instalar, reabrir e conferir a versão em Sobre. Electron, backend e runtime Python estão incluídos; Node/Python são necessários apenas para desenvolver.
4. Configurar Ollama/modelos em Inteligências. Nenhum modelo é baixado nesta rodada de assinatura/documentação. Depois de configurado, o chat local pode funcionar offline; pesquisa, serviços de nuvem e conexão remota dependem da rede.
5. Ajustar permissões, personalidade e voz antes de usar ferramentas; manter STOP acessível.

O pacote continua sem Authenticode. Políticas do Windows podem bloquear executáveis novos. Nenhuma proteção do Windows foi desativada nesta retomada. O manifesto do projeto é uma verificação diferente da confiança exigida pelo sistema.

O feed da 0.5 consulta a lista de releases publicadas e aceita prévias. Versões antigas que ainda consultam `/releases/latest` podem exigir instalação manual inicial da 0.5. Não mudar a visibilidade do repositório para resolver isso sem uma decisão explícita do dono; nesta rodada apenas foi confirmado o estado público já existente.

## Permissões e dados

O seletor do chat e Controle e regras mostram o alcance escolhido. Acesso total amplia a execução automática; ações sensíveis mantêm sua revisão e cartões críticos da 0.5 têm prazo próprio. STOP cancela ações conforme a implementação; não considerar texto de sites/documentos como nova autorização. Conferir resultados antes de confiar em alterações importantes.

Conversas, memórias e configurações ficam localmente; não são incluídas no Git. Credenciais de provedores, documentos pessoais, áudio, modelos e bancos também não devem ser publicados. Recursos de nuvem opcionais dependem da configuração e do consentimento correspondentes; esta rodada não fez chamadas pagas.

## Desenvolver no outro PC

Pré-requisitos: Git, Node 24 e Python 3.12 x64. Ollama/modelos para testes locais. Fontes, locks, testes e documentação estão no repositório.

```powershell
git clone https://github.com/caio306santana/ALT-.git
cd ALT-
git switch main
npm.cmd ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm.cmd run dev
```

Em clone existente, conferir `git status` antes de `git pull --ff-only`; não descartar alterações locais. Usar `npm.cmd` se `npm.ps1` estiver bloqueado, sem mudar a política do computador. Alterações no backend/Electron exigem sair e iniciar novamente; o `git pull` não atualiza sozinho o processo aberto.

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run dist
```

O instalador é gerado em `release/`, ignorada pelo Git. Para assinar o manifesto, com a chave original disponível e o instalador final conferido: `npm.cmd run release:manifest`.

**Continuidade da assinatura:** a chave pública fica em `assets/update-public-key.pem`. A chave privada original está somente em `.local/update-private-key.pem` neste notebook ou no ambiente autorizado. Fazer backup privado para assinar no outro PC; nunca enviar a chave ao Git ou aos assets da release. O script não substitui a identidade pública automaticamente. Authenticode é configurado separadamente com certificado/serviço apropriado; nenhum certificado foi adquirido nesta rodada.

## Pendências e continuidade

O [estudo do Drael](docs/DRAEL_REVIEW.md) compara recursos públicos com a ALT, registra uma melhoria de pesquisa aplicada após a release 0.5.0 e propõe os próximos ajustes. Nenhum modelo ou código privado do serviço foi extraído.

Faltam a nova medição da GPU após reiniciar o PC principal, microfone ativo, configuração/teste do iPhone, Authenticode conforme o destino, revisão manual dos fluxos, mais aplicativos/janelas, documentos longos e avaliação da personalidade em uso real. Não confundir recursos implementados com todos esses testes concluídos.

Consulte [STATUS](docs/STATUS.md), [CHECKPOINT 0.5](docs/CHECKPOINT-0.5.md), [latência](docs/LATENCY-0.5.md), [iPhone](docs/IPHONE.md), [HANDOFF](docs/HANDOFF.md) e [segurança](docs/SECURITY.md). O [histórico da 0.4](docs/history/STATUS-0.4.md) preserva evidências anteriores sem servir de instrução de instalação atual.
