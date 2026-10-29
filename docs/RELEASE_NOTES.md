# ALT-AI 0.3.0 — suas regras, navegador e continuidade

Novo painel Controle e regras: instruções de conversa editáveis, permissões por capacidade e recuperação manual/automática de memória. Veja o prompt e os limites de cada camada. Suas regras persistem até alterar; STOP continua disponível. O aplicativo não reescreve os pesos do modelo nem as regras dos serviços externos.

Navegador ALT em janela/sessão separada com páginas JavaScript, leitura de elementos, cliques, digitação e voltar. Conexões HTTPS públicas passam por proxy com DNS/IP validado e TLS. Não usa sua sessão do navegador pessoal. Downloads, permissões especiais e campos protegidos ficam fora; observações antigas são recusadas. Ações seguem suas autorizações.

Ferramentas Windows ampliadas: registrar aplicativos .exe pelo seletor nativo, abrir executável conferido por hash, solicitar fechamento normal de processos rastreados e buscar arquivos em subpastas autorizadas. Sem shell arbitrário ou encerramento forçado de documentos.

Memória: rascunhos de continuidade gerados localmente e revisados antes de salvar, origem em conversa/mensagens, importação JSON atômica/deduplicada e recuperação por termos relacionada ao pedido. A recuperação automática é opcional e aparece no contexto enviado; ainda não é memória semântica.

Laboratório de modelos locais com respostas, tempos, limites de saída e suas notas. Huihui Qwen 3.5 4B disponível no seletor e testado após autorização de download. Relatório completo em docs/MODEL_COMPARISON_0.3.md. Os testes encontraram erros reais e não demonstram um vencedor geral nem ausência universal de recusas.

Validação: 74 testes Python passaram, um symlink ignorado por privilégio Windows e três testes Node passaram. TS/Vite compilou; navegador real Electron oculto validou HTTPS e DOM sintético de leitura/clique/digitação. Comparação real dos dois modelos e resumo local revisado foram testados sem nuvem/dados pessoais. Revisão visual completa, Windows limpo e PC principal permanecem pendentes.

Instalador inclui Electron/backend/runtime Python. Ollama e modelos são separados, com confirmação de download. Manifesto Ed25519 e SHA256 verificam a atualização; esta prévia ainda não possui certificado Windows Authenticode. Encerre a versão anterior em Sobre → Sair, instale e reabra. O × apenas oculta a janela.

Código e continuidade completos em README.md, docs/HANDOFF.md e docs/ROADMAP.md. Chave privada de atualização fora do Git; manter backup privado para assinar no outro PC.
