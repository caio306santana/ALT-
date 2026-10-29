# ALT-AI

Assistente pessoal Windows com interface Electron/React e inferência local pelo Ollama. Código completo para continuar o desenvolvimento em outro computador.

**Estado: prévia 0.1.0 em validação.** Fases 1 e 2 implementadas; os demais recursos estão em [ROADMAP](docs/ROADMAP.md). Veja o estado exato e próximos passos em [HANDOFF](docs/HANDOFF.md).

## Instalar para usar

1. Baixe `ALT-AI-Setup-0.1.0-x64.exe` em [Releases](https://github.com/caio306santana/ALT-/releases).
2. Execute o instalador no Windows 10/11 x64. O aplicativo inclui Electron e o backend com Python embutido: não exige Python ou Node no computador de destino.
3. Abra **Inteligências**. Se necessário, clique **Instalar Ollama** (usa o winget, após confirmação) ou abra o site oficial. Abra o Ollama após a instalação e atualize a conexão.
4. Autorize o download do `qwen3.5:4b` (vários GB). O 9B é opcional e exige mais memória. Modelos não são incluídos no instalador para evitar vários GB de download obrigatório.
5. Selecione o modelo e converse. Após instalar o modelo, o chat funciona offline.

Nenhuma API paga está habilitada. Codex e Claude Code ainda não são integrações disponíveis nesta versão. O instalador de prévia não possui certificado de assinatura digital.

## Desenvolver no outro PC

Pré-requisitos: Git, Node.js 24 LTS, Python 3.12 x64. Ollama é necessário apenas para chat real. Não é necessário acesso de administrador para o ambiente Python do projeto.

```powershell
git clone https://github.com/caio306santana/ALT-.git
cd ALT-
npm.cmd ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm.cmd run dev
```

Se `python` abrir a Microsoft Store, instale o Python oficial e use o caminho do executável instalado. Se o PowerShell bloquear `npm.ps1`, use `npm.cmd`, sem mudar a política de execução do computador.

O modo de desenvolvimento tem recarga da interface. Mudanças no backend/Electron exigem encerrar a ALT-AI pela opção **Sair** e iniciar de novo.

## Testar e gerar instalador

```powershell
npm.cmd test
npm.cmd run build
npm.cmd start
npm.cmd run dist
```

O último comando gera backend PyInstaller + instalador NSIS em `release/`. Downloads de ferramentas de compilação são necessários na primeira execução. O arquivo `package-lock.json` trava as dependências JavaScript; `requirements-lock.txt` registra o ambiente Python validado. `requirements.txt` contém os intervalos para manutenção.

Teste opcional com modelo real já instalado (não baixa modelos):

```powershell
.\.venv\Scripts\python.exe scripts/smoke_local.py
```

## Uso

- Enter envia; Shift+Enter insere linha; Ctrl+N cria conversa.
- Ctrl+Shift+Espaço abre/oculta a janela globalmente, se o atalho estiver disponível.
- × oculta na bandeja; **Configurações → Comportamento → Sair** encerra interface e backend.
- **STOP ALL ACTIONS** interrompe gerações/downloads em andamento e bloqueia novas ações até **Retomar**.
- O quadrado no campo de mensagem interrompe apenas a resposta atual.
- Trocar modelo preserva o histórico local. Apenas mensagens completas da conversa atual são enviadas ao modelo; respostas parciais ficam visíveis e são excluídas do próximo contexto.
- O temporizador é um controle local da interface; o modelo não o aciona por texto.

## Dados e privacidade

Histórico, preferências e auditoria ficam no perfil do usuário, em `%APPDATA%/ALT-AI/` (desenvolvimento pode usar `alt-ai`). O banco é `data/alt-ai.sqlite3`. Não coloque senhas ou tokens no chat: o histórico é local e não é criptografado nesta prévia. Nenhum arquivo pessoal ou conversa é enviado à nuvem pelo aplicativo.

Para migrar histórico, encerre a ALT-AI nos dois computadores antes de copiar a pasta de dados por um meio privado. Para desenvolver em outro PC, basta clonar o Git: não copie `.venv`, `node_modules`, bancos, credenciais ou logs para o repositório.

## Estrutura

```text
apps/desktop/          React/TypeScript, estilos, Electron e preload
apps/mobile/           contrato e plano do cliente iOS
backend/api.py         rotas FastAPI autenticadas
backend/providers/     adaptador Ollama, streaming e cancelamento
backend/memory/        SQLite e recuperação de respostas parciais
backend/security/      motor independente de permissões
backend/monitoring/    métricas e inventário real do computador
packages/              contratos compartilhados e temas
tests/                 testes críticos com provedor explicitamente de teste
scripts/               execução e validação com Ollama real
docs/                  arquitetura, segurança, roteiro e continuidade
```

Leia [Arquitetura](docs/ARCHITECTURE.md), [Segurança](docs/SECURITY.md) e [Solução de problemas](docs/TROUBLESHOOTING.md).
