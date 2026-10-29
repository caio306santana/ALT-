# Continuidade — ALT-AI

Última atualização: 29/10/2026. Prévia 0.1.0 — Fases 1 e 2 implementadas. Instalador final em validação.

## Escopo autorizado

Implementar Fases 1 e 2 do MASTER PROMPT: Electron/React/TypeScript, FastAPI, SQLite, permissões básicas e chat Ollama com streaming. Gerar instalador Windows e publicar código completo em https://github.com/caio306santana/ALT-.git. Repositório privado; não alterar visibilidade. Instalação de dependências do projeto, Python e Ollama autorizada pelo usuário. Posteriormente autorizou baixar/testar Qwen 3.5 4B. Nenhuma API paga habilitada. Outros downloads de modelos precisam de confirmação explícita na interface.

## Checkpoint atual

- Interface React real: chat Markdown, modelos locais, histórico, métricas, permissões, aparência, temas, temporizador de foco, bandeja, topo, atalho global e posição da janela restaurada.
- Ponte Electron limitada, sandbox/contextIsolation e backend autenticado em loopback/porta efêmera. Token não exposto ao React.
- SQLite com conversas, mensagens, configurações e auditoria; checkpoints parciais e recuperação após encerramento.
- Chat Ollama real com streaming/cancelamento/erros. STOP bloqueia novas gerações/downloads até retomar. Nenhuma ferramenta de OS disponível ao modelo.
- Descoberta automática ao focar a janela e a cada 10 segundos visíveis; preferência inicial por Qwen 4B. Apenas modelos locais detectados disponíveis.
- Setup com instalação Ollama por winget após diálogo nativo e downloads opcionais Qwen 2B/4B/9B, restritos a essas tags e com confirmação.
- Perfil automático notebook/desktop e escolha manual em Comportamento. Notebook: 4K contexto/768 saída/até 4 threads/keep-alive 2m; desktop: 8K/4096/5m.
- CPU/RAM/disco reais; nome GPU/driver por consulta Windows fixa; alocação de modelos via Ollama. Uso/temperatura/VRAM total indisponíveis quando não coletados.
- PyInstaller + electron-builder/NSIS geram instalador com Electron/backend/runtime Python incluídos. Não exige Python ou Node para usar no outro PC.
- Fontes e locks versionados, ícone próprio, documentação completa e workflow manual de build Windows.

## Testes e diagnóstico já realizados

- 14 testes automatizados passaram: auth/origem/host, persistência/reinício, seleção/troca/isolamento de conversas, falhas/partials, STOP, cancelamento antes de headers, crash, configurações, ferramentas negadas, exclusão em cascata e perfis.
- Build TypeScript/Vite e primeira compilação PyInstaller/NSIS concluídos. Recompilação final com perfis em andamento.
- Janela real inspecionada com Computer Use; chat/painel e controles presentes.
- Qwen 3.5 4B baixado: 3.324.173.934 bytes, Q4_K_M, 4.2B. Smoke com backend/SQLite real respondeu `ALT-AI local funcionando.` e persistiu mensagens.
- Teste quente, sem fila: primeiro token 0,66 s, total 2,14 s, 7 tokens. Outro teste após mudança de contexto e durante compilação levou 49,59 s. Esses números não são garantia de desempenho/cold start.
- O notebook atual é Intel i5-1135G7/Iris Xe. Ollama informou VRAM 0 bytes, inferência CPU (~4 tokens/s). Diferente do PC principal Ryzen 9 3900/32 GB/RX 7600 8 GB, ainda não validado.
- Primeira mensagem do usuário levou ~275 s por raciocínio interno do Qwen. Corrigido para `think:false` no Qwen 3.5. Um smoke concorrente aguardou essa fila; não confundir fila/carregamento com geração. Evitar testes concorrentes enquanto o usuário conversa.
- O usuário pediu suporte estável a notebooks; por isso há perfil econômico e Qwen 2B opcional, ainda não baixado/testado. Não prometer aceleração de GPU neste notebook.
- O usuário pediu aviso aos 90% de créditos. Não há indicador confiável de créditos disponível ao agente; informado que serão feitos checkpoints por marcos, com este arquivo atualizado.

## Próximos passos imediatos

1. Concluir recompilação final NSIS com perfis, ícone e fontes atuais.
2. Rodar `scripts/smoke_packaged.py` no backend de `release/win-unpacked` para validar runtime incluído, auth, SQLite e telemetria.
3. Abrir executável empacotado e conferir UI; testar instalação por usuário quando possível.
4. Atualizar este arquivo com resultados/limitações, publicar commit final e release de prévia com instalador/SHA256, preservando visibilidade privada.
5. Próxima etapa funcional: validar no PC Ryzen/RX 7600, depois seguir ROADMAP sem habilitar funções fictícias.

## Retomar no outro PC

Instalar Git, Node LTS e Python 3.12 para desenvolver. Clonar o repositório, seguir README.md. Para apenas usar o app, executar o instalador Windows da release. Não copiar bancos pessoais para Git. Os fontes são a entrega principal; o instalador é um artefato de release.

Use Node 24 LTS, `npm.cmd ci`, crie `.venv`, instale `requirements-lock.txt`, execute `npm.cmd run dev`. `.cmd` evita bloqueio de npm.ps1; script de lançamento remove ELECTRON_RUN_AS_NODE herdado de IDEs. Mudanças no backend/Electron exigem sair e abrir novamente.

## Limitações

Não validado em Windows limpo ou no PC principal. Qwen 2B/9B não testados; driver/aceleração AMD precisa de confirmação real. Histórico SQLite local sem criptografia: não digitar segredos. Instalador sem certificado, atualização segura ainda pendente. Voz, ferramentas Windows, APIs/Codex/Claude, fallback/consentimento de nuvem, memória semântica, custos, game mode e iOS continuam indisponíveis e registrados no ROADMAP. FastAPI/Starlette atual emite aviso de depreciação TestClient/httpx, sem falha nos testes; avaliar atualização futura do lock de testes.
