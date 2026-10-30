# Entrega 0.5.1 — 30/10/2026

[Release publicada como prévia](https://github.com/caio306santana/ALT-/releases/tag/v0.5.1), tag no código `750e2a08dd8d05168d4c4b48f3968757692f825f`. O código completo está em `main`; a documentação de entrega foi complementada após conferir a publicação.

| Artefato | Verificado |
| --- | --- |
| Instalador | `ALT-AI-Setup-0.5.1-x64.exe`, 219.521.408 bytes |
| SHA256 | `3aaf630aacd05d722ca008fc045d2ec006488ad6248fe0c154f604d927434092` |
| Atualização | `ALT-AI-0.5.1-update.json` assinado pela chave original Ed25519; validador da ALT conferiu o manifesto baixado publicamente contra o arquivo local |
| GitHub | Tamanho e digest do asset iguais aos locais; release publicada, não rascunho |
| Feed público | Oferece 0.5.1 para a 0.5.0; não oferece nova versão para a própria 0.5.1 |

Relatório estruturado: [release-0.5.1-verification.json](release-0.5.1-verification.json). A 0.5.0 foi preservada.

## Implementado

- [Orçamento de contexto corrigido](CHAT_CONTEXT_0.5.1.md): modelo Automático resolvido, tokenizers reais, reserva das definições formatadas e limitação de dados auxiliares, sem cortar instruções/memórias escolhidas silenciosamente.
- Pedidos exatos para abrir Bloco de Notas/Calculadora seguem por ação local direta, sem geração. Regras do dono, STOP, revisão no iPhone e aprovações continuam no serviço real de ferramentas; falha/resultado não confirmado não vira sucesso.
- [Hermes 3 3B/8B](HERMES.md) no catálogo, tokenizers oficiais separados, hashes/licença e payload Ollama de ferramentas. O download foi deixado para depois pelo dono.
- Encerramento de trabalhadores de voz/alertas/monitoramento antes de fechar banco; lock no fechamento SQLite elimina a corrida nativa reproduzida pela suíte.
- Pesquisa válida sem resultados tem estado próprio; falha de rede/formato continua sendo erro.

## Verificação e limites

233 testes Python passaram, 1 ignorado por privilégio de symlink; 5 Node passaram. Após a margem adicional das ferramentas Hermes, os 4 testes Hermes foram repetidos e passaram. TypeScript/Vite compilou. Renderer sintético oculto foi conferido, incluindo catálogo Hermes, indicador/detalhes, rascunho, aprovação, bloqueio legítimo e envio de ação direta mesmo sem modelo instalado. Capturas sintéticas foram inspecionadas; nenhum download foi acionado por esse teste.

`scripts/smoke_packaged.py` passou com o runtime congelado, banco temporário e perfil Notebook: saúde/versão/autenticação, armazenamento, personalidade, memória, regras/permissões, importação/recuperação, cálculo aprovado, estimativas Qwen/Hermes, caminho direto e Automático. Tokenizers do pacote têm os hashes versionados. O ASAR foi inspecionado para ausência de `.local`, chave privada, banco e `.env`.

[Smoke real Huihui 4B](chat-context-0.5.1-smoke.json): resposta “pronto.”, 1.461 tokens estimados versus 1.387 medidos pelo Ollama, cerca de 92 s sob carga concorrente. Comprova funcionamento; não demonstra aceleração nem representa benchmark do PC principal.

Ainda não validado nesta sessão: inferência com pesos Hermes (não baixados), janela real do Bloco de Notas (helper nativo indisponível, erro 2), instalação/atualização da ALT aberta, voz com pesos reais neste pacote e fluxo de iPhone/hardware do PC principal. As ações diretas foram testadas com execução simulada. Nenhum documento/janela do dono foi alterado. O backend congelado foi iniciado para teste; o instalador NSIS não foi executado.

O instalador ainda não tem Authenticode. O manifesto do projeto não substitui a confiança Windows; nenhuma proteção foi alterada. Modelos não estão embutidos no instalador.

## Próximo no computador de destino

1. Sair da ALT por Sobre → Sair, instalar a 0.5.1, reabrir e conferir a versão/dados. Não encerrar documentos de outros programas.
2. Testar “abre o bloco de notas” no modo escolhido e verificar a janela/resultados reais; depois testar mais aplicativos e tarefas de janela.
3. Quando desejar, baixar Hermes 3B ou 8B em Inteligências e medir conversa/ferramentas/português/latência. A seleção manual continua disponível; Automático pode escolher outro modelo instalado.
4. Repetir medição de GPU no PC principal após reinício, validar microfone, voz, PDFs longos, personalidade e Tailscale/iPhone conforme [STATUS](STATUS.md).

Demais sugestões do estudo [Drael](DRAEL_REVIEW.md), como modos rápido/aprofundado, execução isolada de código e cofre, continuam propostas futuras.
