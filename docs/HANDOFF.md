# Continuidade — ALT-AI 0.2.0

Atualizado em 29/10/2026. Repositório privado: https://github.com/caio306santana/ALT-.git. Manter a visibilidade. Entrega: fontes completos e instalador Windows com Electron, backend e runtime Python. Node/Python só são necessários para desenvolver.

## Pedidos e decisões

- Avançar personalização, memória, integrações oficiais, ferramentas Windows, desempenho e distribuição. Voz/iOS ficam no roteiro.
- Personalidade aprovada: calma na forma de falar, provocadora, irônica e desafiadora nas ideias, com paciência. Editor continua disponível. Personalidade não altera permissões.
- ALT é o produto/persona/memória/agente. Qwen 3.5 4B é o modelo de terceiros instalado; não existe modelo exclusivo treinado pela ALT.
- Último pedido: autorizações **sem prazo, até alterar ou revogar**, inclusive ao reabrir o app. Implementado em tabela SQLite própria. STOP, Modo Jogo, Observação e remoção de escopo revogam o estado salvo; retomar não restaura acesso anterior. Propostas/recibos de nuvem continuam de uso único com validade de cinco minutos.
- Instalação de dependências, Python/Ollama, download/teste Qwen 4B e publicação de fontes/instalador foram autorizados. Outros modelos exigem confirmação. Nenhuma API paga habilitada/testada com chave real.
- Usuário pediu aviso aos 90% de créditos; agente não possui medição confiável da cota da conta. Fazer checkpoints sem inventar percentuais.

## Implementado

Chat Ollama real: streaming, erros, cancelamento, histórico, recuperação após interrupção e think:false no Qwen. Perfis Notebook/Desktop e telemetria disponível.

Personalidade aplicada ao contexto local/nuvem; Perfil clicável e nome do usuário opcional. CSS cyberpunk original rosa/ciano com recortes/HUD. Aparência, temas, escala, opacidade, efeitos, bordas, atalho global, topo e janela configuráveis.

Memória explícita CRUD/busca/desativação/exportação JSON. Até 300 registros; selecionar até dez por envio, sujeito ao contexto. Sem extração automática ou busca semântica. Históricos e memórias não são criptografados.

Ferramentas estruturadas propostas no chat Qwen: calcular, listar/ler/gravar texto, abrir pasta, Notepad/Calculadora, URL, pesquisa e leitura pública. Cartões/resultados persistem ligados à conversa; análise usa trecho limitado do resultado.

Modo 1 Observação; 2 Assistido com aprovação individual; 3 leitura autorizada de pasta; 4 amplo supervisionado do perfil pessoal e pastas escolhidas. Somente cálculo/leitura/listagem podem executar automaticamente em 3/4. Gravações e consultas externas continuam supervisionadas; perfil exige confirmação nativa adicional para gravação. Sem shell arbitrário, GUI genérica, credenciais/AppData/sistema ou elevação de privilégios.

Pesquisa Bing RSS e páginas HTTPS: fontes, DNS/IP público fixado, TLS, limites de bytes/redirecionamentos/tipos. Sem cookies, sessões logadas, JavaScript ou execução de downloads. Não é navegador interativo.

Codex CLI oficial autenticado ChatGPT com prévia exata/recibo por envio. Scratch isolado, configuração/hooks/plugins/ferramentas pessoais desligados, permissões restritas. Sem fallback pago automático nem acesso automático aos executores locais ALT.

Anthropic API opcional e desligada: DPAPI, verificação de autenticação/modelos, preços/orçamentos e reservas. Contratos automatizados passaram; nenhuma chamada paga real. Claude por assinatura indisponível; não extrair tokens nem contornar restrições do provedor.

Modo Jogo suspende/revoga ações, tenta descarregar o modelo selecionado e oculta janela. Não garante liberação integral de RAM/VRAM.

Atualização local verificada por manifesto Ed25519, hash/tamanho/anti-rollback, confirmação e nova validação antes da instalação. Não é feed automático nem certificado Windows Authenticode.

## Evidência e limites

- 59 testes Python passaram; um ignorado porque este usuário Windows não pode criar symlinks. Um teste Node de assinatura/adulteração/chave incorreta/rollback passou. Inclui persistência dos modos 2/3/4, avanço do relógio, reinício e revogação persistente.
- TypeScript/Vite compilou. Registrar o resultado final PyInstaller/NSIS e smoke empacotado abaixo, antes da publicação.
- Codex real respondeu ALT-CODEX-OK. em 5,02 s com contexto sintético revisado. Qwen 4B questionou uma premissa e propôs pesquisa estruturada; a consulta permaneceu pendente em Observação. Pesquisa pública e leitura docs.ollama.com verificadas por HTTP real.
- Notebook Intel i5-1135G7/Iris Xe: Ollama em CPU, aproximadamente 3,5–4 tokens/s. Carregamento/contexto frio levou 40–80 s. PC principal Ryzen 9 3900/32 GB/RX 7600 ainda não validado; Qwen 2B/9B não testados.
- Controle visual retornou interrupção física por Esc. Não insistir em automação na mesma rodada. Usuário enviou prints de ferramentas/modelos/histórico/personalidade/memória/sistema, inspecionados. Os prints ainda mostram o build anterior com minutos. Perfil/pacote final precisam de validação interativa; não alegar revisão visual completa.
- Windows limpo, certificado Authenticode e uso prolongado no PC principal permanecem pendentes. Sem migração reversa de banco; fazer backup antes de downgrade. A 0.2 adiciona tabelas.

## Distribuição e outro PC

npm.cmd run dist usa scripts/build-windows.cjs. O wrapper preserva o ambiente Windows no passo NSIS de electron-builder 26.18: o código da dependência passava somente __COMPAT_LAYER ao execFile, perdendo SystemRoot/PATH e causando spawn UNKNOWN. Mantém a cadeia normal NSIS/assinatura. A execução do gerador funcionou preservando o ambiente.

Nunca publicar o gerador intermediário NSIS como instalador. release:manifest recusa arquivos abaixo de 10 MB.

**Chave privada de atualização: .local/update-private-key.pem, ignorada pelo Git. Fazer backup privado para continuar assinando do outro PC. Nunca publicar.** Chave pública em assets/update-public-key.pem. Clone não contém chave privada. Authenticode exige certificado/serviço ainda não configurado. Nenhum secret foi enviado ao GitHub.

Para desenvolver: Git, Node 24 e Python 3.12; clonar, npm.cmd ci, criar .venv, instalar requirements-lock.txt e npm.cmd run dev. Usar .cmd evita npm.ps1 bloqueado. Backend/Electron exigem sair e reabrir após mudança. Para usar: instalador da release e setup Ollama/modelo. Não copiar bancos/cofre/logs/chaves privadas para Git.

## Próximos passos

1. Instalar e validar em Windows limpo/PC principal, incluindo GPU realmente utilizada. Testar uso prolongado no notebook e modelos opcionais só com consentimento.
2. Revisar pacote final: Perfil, navegação, escala/tema e autorização sem prazo após reabrir.
3. Navegador interativo isolado e GUI com permissões granulares, mais apps, busca recursiva, proteção de documentos ao fechar programas.
4. Memória com importação/resumos/busca semântica, tarefas/rotinas, temas completos, APIs adicionais/fallback autorizado. Roteiro completo em ROADMAP.md.
5. Certificado Authenticode, feed autenticado, migrações/backup, testes de junctions e coletores GPU/temperatura.

## Registro final

Build/publicação em validação. Atualizar link, tamanho e SHA256 após compilação final; não usar hash de intermediários.

## Pausa solicitada pelo usuário — checkpoint antes do limite

O usuário pediu parar tudo e atualizar o Git, informando 2% de cota restante e renovação em duas horas. Desenvolvimento e compilação interrompidos. Não publicar a 0.2 com o pacote atual sem concluir os passos abaixo.

- Fontes de personalidade/memória/provedores/ferramentas/perfil/visual/persistência já salvos no Git. Último ajuste do wrapper NSIS evita configuração duplicada: passar package.json.build novamente à API concatenava extraResources e criava duas cópias concorrentes do backend, causando EBUSY. Agora o build normal deixa electron-builder carregar package.json; o assinado recebe caminho do arquivo de configuração.
- Validação final já feita: 59 testes Python passaram, um symlink ignorado; um teste Node passou; TypeScript/Vite e PyInstaller concluíram. Inspeção estática de app.asar confirmou texto sem prazo e página Perfil no frontend empacotado. Não equivale a teste visual.
- A última montagem chegou ao NSIS sem os erros anteriores, mas foi interrompida a pedido do usuário antes de confirmar término. Não considerar release/ALT-AI-Setup-0.2.0-x64.exe válido até novo build bem-sucedido.
- Não foi publicada release v0.2.0. A v0.1.0 continua sendo a prévia publicada. Manifesto/SHA256 locais de builds anteriores podem estar desatualizados e devem ser regenerados após concluir o pacote.

### Retomar por esta ordem

1. Não refazer implementação nem downloads já concluídos. Ler este HANDOFF e consultar git status. A janela atual usa o build anterior e não atualiza o backend só por recarregar a interface.
2. Executar node scripts/build-windows.cjs para concluir somente empacotamento (frontend/backend atuais já compilados). Se os fontes forem alterados, usar npm.cmd run dist. Não iniciar múltiplos builds concorrentes.
3. Após término bem-sucedido, executar .venv/Scripts/python.exe scripts/smoke_packaged.py. Valida runtime incluído, autenticação, armazenamento, personalidade/memória, ferramentas e permissão sem prazo em banco temporário.
4. Executar npm.cmd run release:manifest apenas depois do instalador final. Verificar assinatura com update-security.cjs, tamanho e SHA256. Não executar o instalador durante essa verificação. A chave privada original existe apenas em .local, fora do Git.
5. Atualizar este documento e RELEASE_NOTES com resultado real, tamanho/hash e pendências. Commit/push. Publicar prévia privada v0.2.0 com instalador, manifesto Ed25519 e SHA256SUMS.txt, usando docs/RELEASE_NOTES.md. Verificar assets enviados.
6. Revisão visual final/Perfil e instalação Windows limpo/PC Ryzen/RX 7600 continuam pendentes. Controle visual detectou Esc; prints do usuário foram revisados. Retomar automação visual só com nova solicitação.

Não habilitar API paga, baixar outros modelos, publicar chave privada nem alterar visibilidade do repositório.
