# Continuidade — ALT-AI 0.5.2 em desenvolvimento

**Última decisão do dono:** manter processamento local; servidor próprio e iPhone independente ficam para depois. Pediu plano e envio de todo o trabalho ao Git. Começar por [PENDENCIAS-LOCAL.md](PENDENCIAS-LOCAL.md) e [CHECKPOINT-0.5.2.md](CHECKPOINT-0.5.2.md). Há metadados reais/cache/contexto na etapa 1 e melhorias autenticadas de streaming/cancelamento na PWA, com testes e compilação. **Não há instalador/release 0.5.2 nem atualização instalada.** Próximo técnico: gerar/testar o pacote final e validar no destino. Não provisionar servidor nem baixar modelos por causa do plano.

Ollama real foi consultado em banco temporário sem inferência: Qwen, Huihui e Hermes 3B encontrado já instalado. Não atribuir o download Hermes a esta rodada; não houve benchmark/resposta real dele. Tailscale e iPhone conectados foram observados, mas Serve/pareamento da ALT não foram concluídos. CLI de publicação em espera foi encerrada; configuração Serve final estava vazia. Não publicar dados da rede/códigos/tokens.

## Registro da entrega anterior — 0.5.1

**Planejamento seguinte:** [PLANO-ACAO-DRAEL.md](PLANO-ACAO-DRAEL.md) contém sequência, dependências, critérios de aceitação e evidências exigidas por etapa. Foi criado após a 0.5.1 e ainda não executa as melhorias futuras. Começar pelas validações da base e pela rodada de capacidades/cartões/continuidade; não declarar uma etapa concluída apenas pela tela/API.

Entrega de 30/10/2026 neste notebook: **0.5.1 publicada como prévia**, tag `750e2a0`, instalador de 219.521.408 bytes, SHA256 `3aaf630aacd05d722ca008fc045d2ec006488ad6248fe0c154f604d927434092`. Manifesto original Ed25519, digest GitHub e feed público conferidos. Código/renderer/backend empacotado aprovados (233 Python, 5 Node, 1 ignorado). [Validação e próximos passos](RELEASE-0.5.1.md).

Automático usa o tokenizer real, dados auxiliares têm orçamento, ferramentas formatadas são reservadas. Há ações diretas exatas para Notepad/Calculadora, catálogo Hermes 3B/8B (pesos deixados para depois pelo dono), tokenizers Hermes fixados e encerramento de trabalhadores antes do banco. Resposta real Huihui confirmada no Notebook, mas lenta sob carga; não é benchmark. Não afirmar Hermes real testado, abertura real de janela ou atualização instalada. Próximo: instalar/conferir versão, testar a janela; baixar Hermes quando escolhido; medir PC principal e validar hardware/iPhone conforme STATUS. A seção abaixo é o registro da release base 0.5.0, preservada sem alterações.

Atualizado em 30/10/2026 neste notebook. **Começar por [STATUS.md](STATUS.md)** e [CHECKPOINT-0.5.md](CHECKPOINT-0.5.md). `main` já reúne 0.4.0/0.4.1, 0.4.2 e 0.5; base funcional `e84df62`, igual ao commit da tag `v0.5.0`.

A release 0.5.0 está publicada como prévia. O instalador existente foi baixado e conferido pelo digest do GitHub (216.270.399 bytes, SHA256 `45fb094673c3e23d8d786f4de98fc410a88469993ebda08b4e74172b08ab6061`). A chave original foi encontrada neste notebook, corresponde à pública versionada e assinou o manifesto da 0.5; manifesto e SHA256 foram anexados à release. Não houve rebuild, instalação nem assinatura Windows Authenticode nesta rodada.

O repositório foi encontrado público; o feed da 0.5 usa a lista de releases e inclui prévias. A visibilidade não foi alterada aqui. Não seguir as antigas instruções de publicação/merge/instalação abaixo como se ainda fossem pendentes. Os testes funcionais descritos no checkpoint foram feitos no PC principal; neste notebook foram conferidos Git, artefatos, assinatura e feed.

Pendentes: nova medição da GPU no PC principal após reiniciar; microfone funcional; Tailscale/pareamento real do iPhone; Authenticode conforme a política do destino; revisão manual da janela, mais aplicativos/tarefas de janela, PDFs longos e personalidade. Nenhum desses testes de hardware foi repetido nesta rodada. Preservar a chave privada fora do Git e fazer backup privado.

## Registro histórico das rodadas anteriores

Os estados, versões instaladas, caminhos e bloqueios nas seções abaixo são históricos. O bloqueio 4551 da 0.3.1 não prova bloqueio atual da 0.5.

# Continuidade — ALT-AI 0.3.1 / desenvolvimento 0.4

**Ponto de retomada:** [STATUS.md](STATUS.md) reúne o que foi feito, evidências, estado do instalador e pendências das etapas 2–6. O checkpoint de documentação não representa novos testes ou instalação da atualização.

Atualização de 29/10/2026: ver `CHAT_FIX_0.3.1.md` para escopo e evidências da correção de contexto, propostas sem prazo e interface. O runtime novo foi bloqueado pelo Controle de Aplicativos (WinError 4551; eventos Code Integrity 3033/3077). Pacote gerado, mas smoke empacotado e instalação não aprovados. Manter release 0.3.1 em rascunho. Nenhuma proteção Windows foi alterada.

`main` contém a correção isolada sobre a base 0.3. O trabalho incompleto das etapas 2–6 está preservado em `work/advanced-0.4`, documentado em `docs/PROGRESS-0.4.md` nessa branch: TaskManager, Knowledge, UIA, backup/migrações ainda precisam de integração/validação. EmbeddingGemma baixado com autorização; certificado Authenticode não disponível, dependência expressamente adiada pelo usuário. Não declarar as etapas completas.

Instalador local `release/ALT-AI-Setup-0.3.1-x64.exe`, 134.257.757 bytes, SHA256 `831f1d72d7f07792f27250442cfc0a4bde1f8d52ee769a38b93fd0a3d4aa9e85`, manifesto Ed25519 verificado. Isso não supera política de assinatura do Windows. Não substituir a instalação aberta sem concluir a validação.

Próximo: resolver confiança/assinatura conforme política local, rodar smoke empacotado e instalação/atualização; retomar depois as integrações avançadas. Preservar `.local/update-private-key.pem` fora do Git e fazer backup privado; não publicar banco, credenciais, logs nem modelos. Não há medição confiável de créditos do agente.

## Registro histórico da entrega anterior (0.3.0)

# Continuidade — ALT-AI 0.3.0

Atualizado em 29/10/2026. Repositório privado: https://github.com/caio306santana/ALT-.git. Manter a visibilidade. Fontes completos e instalador Windows com Electron/FastAPI/runtime Python incluídos.

## Escopo e decisões do usuário

O usuário pediu executar os passos 2, 3, 4 e 5 da próxima entrega: painel de regras sob seu controle, comparação de modelos locais, navegador interativo/ferramentas Windows e memória de continuidade. Quer liberdade de discussão e regras transparentes, definidas por ele. Não prometer que instruções do aplicativo removem comportamentos aprendidos dos pesos ou regras de serviços externos.

Personalidade mantida: calma na fala, provocadora, irônica e desafiadora nas ideias, com paciência. Editor disponível. ALT é o produto/persona/memória/agente; Qwen e Huihui são modelos de terceiros, não pesos exclusivos treinados por nós.

Autorizou dependências/Python/Ollama, Qwen original 4B e, nesta rodada, download e comparação de huihui_ai/qwen3.5-abliterated:4b (3.315.333.475 bytes). Não baixar outros modelos sem consentimento. Nenhuma API paga habilitada nem chamada de nuvem feita nesta rodada.

Autorizações sem prazo, persistentes até alterar/revogar. STOP/Modo Jogo/Observação e remoção de escopo revogam o estado salvo. O usuário pediu checkpoints antes de esgotar cota; não há medição confiável da cota pelo agente.

## Entregue no código 0.3

- Controle e regras: regras de conversa editáveis; bloquear/perguntar/permitir por capacidade; recuperação manual/automática de memórias. Escrita via canal nativo com revisão, fora do broker genérico. Mostra prompt efetivo e limites de modelo/aplicativo/Windows/serviços. Alterar política cancela propostas e ações de ferramentas em andamento, preservando o modo escolhido.
- Permitir automaticamente atua nos modos 3/4 e escopos já autorizados. Observação não executa. Gravação no perfil e fechamento de apps mantêm revisão individual. Respostas de páginas/modelos nunca concedem autorização.
- Navegador ALT real: janela Electron separada, sessão em memória, Node desligado/sandbox/contextIsolation, HTTPS público via proxy CONNECT que valida todos os IPs de DNS e fixa a conexão no IP público; Chromium valida TLS. Sem rede privada, downloads ou permissões de câmera/microfone.
- Ler página/elementos, abrir/voltar, clicar/digitar por snapshot e ID observado. Elementos alterados e campos protegidos são recusados. Conteúdo de páginas é dado não confiável. Fila DesktopBridge autenticada consumida por Electron main; páginas e renderer não recebem token ou acesso ao IPC nativo. STOP/Modo Jogo interrompem o navegador.
- Navegação pode ser usada pelo painel e por propostas do chat. O chat recebe uma observação recente limitada ao contexto; não há loop autônomo ilimitado. Uma janela/aba por vez. Interações podem enviar dados ao site e seguem as regras do usuário.
- Aplicativos .exe cadastrados por seletor nativo e conferidos por hash antes de abrir; sem argumentos arbitrários. Solicitação de fechamento normal só de processos rastreados pela ALT, com PID/tempo de criação. Programas podem pedir para salvar; apps que transferem a janela a outro processo podem não ser rastreados. Nunca forçar encerramento de documentos.
- Busca recursiva de arquivos em escopos, com cancelamento/tempo/quantidade limitados e exclusão de caminhos sensíveis. Leitura/gravação anteriores preservadas.
- Rascunho de continuidade local com revisão/edição antes de salvar. Mudança de conversa invalida o rascunho. Origem em conversa/mensagens registrada. Não existe extração silenciosa automática.
- Importar JSON exportado da ALT com validação antes de transação, deduplicação e preservação dos registros atuais. Recuperação por termos/acento normalizado; opt-in automático com ajuste ao contexto e identificação das memórias usadas. Não é busca vetorial/semântica. Prévia/recibo de nuvem inclui o contexto realmente enviado.
- Laboratório local em Inteligências: um a três modelos instalados, mesmos casos, respostas/métricas/limite de saída, cancelamento/STOP e notas humanas editáveis. Não aceita modelos de nuvem nem inventa notas ou saldo. Mostra quando o limite de saída foi atingido.
- Biblioteca de modelos inclui a variante Huihui autorizada. Não trocamos o padrão do usuário automaticamente. think:false também se aplica à variante Qwen 3.5.

## Validação atual

74 testes Python passaram; um symlink ignorado por privilégio Windows. Três testes Node passaram (URLs/IPs, CONNECT/DNS privado ou misto, assinatura). TS/Vite compilou. Smoke Electron oculto do próprio navegador passou: HTTPS docs.ollama.com via proxy, DOM sintético de leitura/clique/digitação, snapshot antigo e senha recusados. Não é controle da área de trabalho ou de contas pessoais, nem revisão visual completa da UI.

Comparação real inicial com seis respostas e repetição de duas discussões com 256 tokens concluídas em Notebook/CPU. Relatório completo em MODEL_COMPARISON_0.3.md e dados sintéticos em model-comparison-0.3.json. Qwen respondeu 642 na conta 17×19, Huihui respondeu 323. Ambos discutiram RBU sem recusa, mas isso não prova ausência de recusas geral. Houve erros de linguagem/alegações sem fonte. Nenhuma nota humana inventada. Temperatura/amostragem foram padrões dos modelos; outros processos estavam abertos. Não declarar um vencedor geral.

Teste real scripts/smoke_continuity.py passou: Qwen resumiu registro sintético Aurora; nenhuma memória antes de revisão; edição aprovada salva com origem. Testes anteriores da 0.2: Codex sintético, pesquisa pública e análise de resultado Notebook sem erro de contexto.

Notebook atual i5-1135G7/Iris Xe usa CPU. PC principal Ryzen 9 3900/32 GB/RX 7600 e Windows limpo continuam sem validação. Não prometer resposta instantânea ou aceleração AMD confirmada. Revisão visual final da interface depende de serviço Computer Use, indisponível na retomada anterior.

## Distribuição e instalação

Pacote 0.3 concluído: NSIS, smoke empacotado e manifesto Ed25519/hash verificados. Instalador ALT-AI-Setup-0.3.0-x64.exe com 129.517.936 bytes. SHA256: 3365e2660c75c518d68af91d5bb4b669c2d4c991290f8cf04352782003b9dab0. Browser empacotado corresponde ao fonte testado e runtime backend corresponde ao smoke aprovado. Manifesto regenerado após ajuste final de versão na interface. Release privada publicada: https://github.com/caio306santana/ALT-/releases/tag/v0.3.0. Os três assets estão uploaded; tamanho e digest SHA256 do instalador no GitHub conferem com o arquivo local. Tag de código: eca1776. Commits posteriores de documentação não modificam o binário.

Build: npm.cmd run dist. Wrapper scripts/build-windows.cjs preserva ambiente no passo NSIS electron-builder 26.18 e evita configuração duplicada/extraResources concorrentes. Não publicar o pequeno gerador intermediário de uninstaller. release:manifest recusa arquivos abaixo de 10 MB.

**Chave privada .local/update-private-key.pem permanece fora do Git. Fazer backup privado para assinar no outro PC. Nunca publicar.** Chave pública em assets/update-public-key.pem. Manifesto Ed25519 não é Authenticode. Certificado Windows e feed automático continuam pendentes; nenhum secret foi enviado ao GitHub.

Para aplicar: Sobre → Sair da ALT-AI, instalar a versão nova e reabrir. O × apenas oculta na bandeja. Preservar dados locais. Para desenvolver: clonar, Node 24/Python 3.12, npm.cmd ci, .venv + requirements-lock.txt e npm.cmd run dev. Fontes mudados em backend/Electron exigem reiniciar.

SQLite de conversas/memórias não é criptografado. Credencial Anthropic opcional usa DPAPI separado. Não versionar bancos, logs ou chaves. Migrações adicionam tabelas; não há downgrade reverso automático, fazer backup.

## Pendências reais

1. Revisão visual completa de Controle/Navegador/Memória/Laboratório e instalação em Windows limpo/PC principal; teste prolongado e GPU real.
2. Memória semântica/importação de documentos, resumos automáticos por projeto e recuperação mais refinada; hoje é rascunho revisado e busca por termos.
3. Mais abas e tarefas longas de navegador, automação genérica da GUI Windows, tratamento de apps que mudam PID, rotinas e integrações adicionais.
4. Certificado Authenticode, feed autenticado, backup/migrações, coletores GPU/temperatura, voz e iOS, conforme ROADMAP.

Não confundir ampliação dos passos solicitados com todas as fases do MASTER PROMPT concluídas.
