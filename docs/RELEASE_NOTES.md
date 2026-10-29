# ALT-AI 0.2.0 — personalidade, memória e ferramentas

Personalidade configurável: calma na fala, provocadora, irônica e desafiadora nas ideias. Perfil clicável, visual cyberpunk original, memória explícita editável/selecionável e mais controles de aparência.

Chat Qwen com propostas de cálculo, arquivos texto nas pastas autorizadas, pastas, Notepad/Calculadora, URLs, busca e leitura pública com fontes. Quatro modos de autorização salvos sem prazo até alterar/revogar. STOP e Modo Jogo revogam o acesso. Controle amplo cobre perfil pessoal/pastas supervisionadas; credenciais, AppData, sistema e shell arbitrário ficam excluídos. Sem mouse/teclado genéricos ou navegação logada.

Codex oficial autenticado ChatGPT com revisão de contexto por envio. Anthropic API opcional, desligada, com cofre Windows/orçamentos; ainda sem teste pago real. Claude por assinatura não integrado. ALT é o aplicativo/persona/agente; Qwen é seu modelo local de terceiros.

Instalador com interface, backend e runtime Python; não exige Node/Python para usar. Ollama/modelos configurados pelo app com confirmação de download. Perfis Notebook/Desktop, métricas disponíveis e Modo Jogo. Inferência depende do hardware: carregar o 4B em CPU pode levar dezenas de segundos.

Validação: 59 testes Python passaram, um symlink ignorado por privilégio Windows e um teste Node de assinatura passou; TypeScript/Vite compilou. Qwen/Codex e pesquisa pública tiveram testes reais com contexto sintético. Prints do usuário revisados; validação interativa do pacote final, Windows limpo e PC principal continuam pendentes.

Baixe o .exe para instalar. SHA256SUMS.txt confere integridade; manifesto Ed25519 permite atualização verificada pelo aplicativo. O manifesto não substitui certificado Windows Authenticode; esta prévia ainda não tem certificado Windows. Históricos/memórias locais não são criptografados. Voz, memória semântica, navegador interativo e iOS permanecem no roadmap.

Código completo e continuidade: README.md, docs/HANDOFF.md, docs/SECURITY.md e docs/ROADMAP.md. A chave privada de atualização não está no Git; seu proprietário precisa manter backup privado para assinar futuras versões.
