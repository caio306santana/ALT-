# Continuidade — ALT-AI

Última atualização: 29/10/2026. Entrega em desenvolvimento, ainda não validada.

## Escopo autorizado

Implementar Fases 1 e 2 do MASTER PROMPT: Electron/React/TypeScript, FastAPI, SQLite, permissões básicas e chat Ollama com streaming. Gerar instalador Windows e publicar código completo em https://github.com/caio306santana/ALT-.git. Instalação de dependências do projeto, Python e Ollama autorizada pelo usuário. Nenhuma API paga habilitada. Downloads de modelos precisam de confirmação explícita na interface.

## Checkpoint atual

- Arquitetura modular e backend escritos, ainda pendentes de testes.
- Ponte Electron limitada e backend autenticado em loopback.
- Banco SQLite com conversas, mensagens, configurações e auditoria.
- Streaming com cancelamento, checkpoints parciais e STOP persistente durante a sessão.
- Empacotamento previsto: PyInstaller + electron-builder/NSIS. Não exige Python no PC de destino.
- Node e Git existentes; Python instalado no usuário; dependências e Ollama em preparação.

## Próximos passos imediatos

1. Concluir interface React, configurações e setup de modelo.
2. Testar autorização, persistência, isolamento de conversas, falhas e cancelamento com provedor controlado de teste.
3. Validar chat real apenas se houver modelo instalado/autorizado.
4. Gerar backend e instalador; executar aplicativo empacotado para conferir inicialização.
5. Atualizar este arquivo com resultados e limitações, publicar Git e anexar instalador a uma release.

## Retomar no outro PC

Instalar Git, Node LTS e Python 3.12 para desenvolver. Clonar o repositório, seguir README.md. Para apenas usar o app, executar o instalador Windows da release. Não copiar bancos pessoais para Git. Os fontes são a entrega principal; o instalador é um artefato de release.
