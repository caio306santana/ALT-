# Limites de segurança da prévia

- Renderer com sandbox, contextIsolation e nodeIntegration desativado; navegação/janelas externas bloqueadas. CSP sem scripts remotos; links do chat não abrem sites automaticamente; HTML do modelo não é executado. A CSP de desenvolvimento permite o preâmbulo React local, removido no build de produção.
- Backend somente loopback, porta aleatória e token efêmero. Todas as rotas exigem autenticação. A ponte não é um proxy HTTP genérico.
- Nenhuma ferramenta de shell, filesystem ou automação de apps disponível para o modelo. A consulta fixa de inventário Windows é implementada pelo coletor do aplicativo, sem entrada do modelo.
- Nenhum provedor pago ou upload de arquivos disponível. Não são extraídas sessões de Claude/ChatGPT, cookies ou credenciais. Proxies HTTP do ambiente não são usados no tráfego Ollama.
- Conteúdo de mensagens é renderizado como texto/Markdown, não autorização. O motor independente rejeita toda execução de ferramentas nesta versão.
- STOP bloqueia novas gerações e downloads até retomada explícita; respostas parciais ficam marcadas e não entram no próximo contexto.
- Dados são locais, mas SQLite não é criptografado. Não digite segredos no chat. Não existe detecção perfeita de senhas arbitrárias; armazenamento seguro de credenciais é requisito antes da fase de nuvem.
- Exclusão pela interface remove registros do histórico, mas não promete apagamento forense do disco, backups ou páginas SQLite.
- A instalação do Ollama exige diálogo nativo explícito e usa um identificador fixo do winget; o site alternativo é uma URL oficial fixa. Download de modelo exige confirmação separada e aceita apenas `qwen3.5:4b` ou `qwen3.5:9b`.
- Administradores locais e processos maliciosos no mesmo usuário não estão isolados por este mecanismo de token. O app não é um sandbox de análise de malware nem substitui o antivírus.

Antes de liberar ferramentas reais: implementar autorização por recurso/prazo, deny por padrão, resolução de caminhos/junctions, isolamento, scanner de downloads, auditoria e testes adversariais. Não aumentar permissões ao mudar de modelo.
