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

## Validação final desta rodada

- 67 testes Python passaram; um teste de symlink foi ignorado por falta de privilégio Windows. Um teste Node de assinatura/adulteração/chave incorreta/rollback passou.
- TypeScript/Vite, PyInstaller e NSIS concluídos. O wrapper preserva o ambiente Windows no passo NSIS de electron-builder 26.18 (evita spawn UNKNOWN) e deixa o builder carregar package.json uma única vez (evita duplicar extraResources e EBUSY).
- Backend empacotado validou autenticação (401 sem token), SQLite/conversas, personalidade, memória, ferramentas, autorização persistente e telemetria Notebook, usando banco temporário.
- Corrigido o erro de contexto na análise de resultados: backend/context.py ajusta JSON ao espaço restante em bytes, preserva URLs inteiras e avisa sobre o trecho reduzido. Esquemas de ferramentas entram no orçamento. Personalidade/memórias escolhidas não são cortadas silenciosamente; o resultado completo continua no cartão/banco. O prefixo técnico do Electron foi removido das mensagens de erro da interface.
- Teste real scripts/smoke_analysis.py: Qwen 3.5 4B analisou um registro sintético extenso no perfil Notebook, resposta em 41,72 s, primeiro token em 38,12 s, 777 tokens de entrada, 19 de saída, 5,28 tokens/s. Resultado completo preservado. Não usou nuvem ou dados pessoais.
- Testes reais anteriores: Codex respondeu ALT-CODEX-OK. em 5,02 s com contexto sintético revisado; Qwen propôs pesquisa que permaneceu pendente em Observação; busca pública e leitura docs.ollama.com verificadas por HTTP.
- Nesta retomada o serviço Computer Use não conectou ao pipe nativo, mesmo após recuperação documentada. Não foi possível revisar interativamente o pacote final. Prints anteriores de ferramentas/modelos/histórico/personalidade/memória/sistema foram inspecionados. Não alegar teste visual completo.
- Notebook atual: Intel i5-1135G7/Iris Xe, inferência CPU. O PC principal Ryzen 9 3900/32 GB/RX 7600, Windows limpo e uso prolongado permanecem sem validação. Qwen 2B/9B não testados.

## Pacote e publicação

Artefatos finais publicados e verificados na prévia privada 0.2.0:
- Instalador: release/ALT-AI-Setup-0.2.0-x64.exe, **129.476.502 bytes**.
- SHA256: c7abd6f24ad9f9d9fca5efb0470448cf917bc3b9c12fd20874027fe4cd646cc1
- Manifesto: release/ALT-AI-0.2.0-update.json, assinatura Ed25519 verificada com a chave pública versionada e comparação de tamanho/hash/versão. Não é certificado Windows Authenticode.
- SHA256SUMS.txt gerado a partir deste arquivo final; não usar os intermediários anteriores.
- Release privada publicada: https://github.com/caio306santana/ALT-/releases/tag/v0.2.0
- Estado da publicação: concluída. Os três assets estão uploaded; tamanho e SHA256 do instalador retornados pelo GitHub coincidem com o arquivo local. Repositório permanece privado. A tag aponta para o commit 3d16ff0; alterações posteriores são documentação.

A prévia 0.1 continua disponível para histórico. A tag de release corresponde ao código do pacote; commits posteriores de documentação não modificam o binário.

## Aplicar a correção no aplicativo aberto

Encerre em Configurações → Sobre → Sair da ALT-AI, instale a 0.2 e reabra. O × apenas oculta na bandeja. A janela antiga não carrega o backend novo automaticamente. Não apagar os dados do usuário. A primeira instalação 0.2 é manual: a 0.1 ainda não possui verificador de atualização.

Para testar só os fontes atuais, sair e executar npm.cmd start (usa frontend compilado e Python da .venv) ou npm.cmd run dev. A seleção de memórias muito grande ainda pode exceder legitimamente o contexto; nesse caso reduzir seleção/instruções ou usar Desktop. Não descartar escolhas silenciosamente nem aumentar o consumo do notebook sem pedido.

## Outro PC e assinatura

**Chave privada de atualização: .local/update-private-key.pem, ignorada pelo Git. Fazer backup privado para continuar assinando do outro PC. Nunca publicar.** Chave pública em assets/update-public-key.pem. Um clone contém os fontes, não a chave privada. Authenticode exige certificado/serviço externo ainda não configurado; nenhum secret foi enviado ao GitHub.

Para desenvolver: Git, Node 24 e Python 3.12; clonar, npm.cmd ci, criar .venv, instalar requirements-lock.txt e npm.cmd run dev. Usar .cmd evita npm.ps1 bloqueado. Backend/Electron exigem sair e reabrir após mudanças. Para usar, instalar a release e configurar Ollama/modelo com consentimento. Não copiar bancos/cofre/logs/chaves privadas para Git.

SQLite local sem criptografia para conversas/memórias. A 0.2 adiciona tabelas, sem migração reversa. Fazer backup antes de downgrade. Não publicar dados pessoais.

## Próximos passos reais

1. Conferência visual final de Perfil/navegação/escala/temas e autorização sem prazo após reabrir, quando o serviço de controle visual estiver disponível.
2. Instalação em Windows limpo e no PC Ryzen/RX 7600, medir GPU realmente utilizada e estabilidade prolongada. Modelos opcionais só após consentimento.
3. Navegador interativo isolado e GUI com permissões granulares, mais apps, busca recursiva e proteção de documentos ao fechar programas. A pesquisa atual só lê páginas HTTPS públicas sem login/JS.
4. Memória com importação/resumos/busca semântica, tarefas/rotinas, temas completos, APIs adicionais/fallback autorizado; voz e iOS continuam no ROADMAP.
5. Certificado Authenticode, feed autenticado de atualização, migrações/backup, testes de junctions e coletores de GPU/temperatura.

Retomada de 29/10 concluída no código e no pacote, após pausa anterior por cota. O usuário autorizou prosseguir. Não habilitar API paga, baixar outros modelos, publicar a chave privada ou alterar visibilidade do repositório.
