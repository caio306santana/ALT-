# ALT-AI 0.2

Assistente pessoal Windows com personalidade própria, memória editável e ferramentas reais. **Qwen é o modelo de terceiros que gera respostas locais; ALT-AI é o aplicativo/agente, a identidade, a memória e o controle das ferramentas. Não treinamos um modelo exclusivo do zero.**

Personalidade padrão aprovada: calma ao falar, provocadora, irônica e desafiadora nas ideias; questiona premissas e contradições com paciência. Ajustável sem reinstalar.

## Instalar e usar

1. Baixe o instalador x64 em [Releases privadas](https://github.com/caio306santana/ALT-/releases). Entre no GitHub com acesso ao repositório.
2. Instale e abra a ALT-AI. Electron, backend FastAPI e runtime Python estão incluídos; Node/Python não são necessários no PC de uso.
3. Em Inteligências, instale/abra Ollama, autorize o download de um modelo e selecione-o. Qwen 4B foi validado; 2B é opção mais leve e 9B opcional. Não são baixados sem confirmação.
4. Converse normalmente. Depois de baixar o modelo, o chat local funciona offline; pesquisa e provedores de nuvem precisam de internet.

O instalador desta prévia não tem certificado Authenticode. Há verificação Ed25519 de atualizações do projeto, que é uma proteção diferente e não remove alertas do Windows.

## O que funciona

- Chat Ollama com streaming, cancelamento, histórico SQLite, modelos locais e recuperação de respostas interrompidas.
- Perfil clicável no círculo inferior, nome/apelido opcional, personalidade editável e identidade consistente entre modelos.
- Temas, cores, neon, opacidade, fonte, escala, claro/escuro, efeitos, bordas, atalhos, janela e temas pessoais salvos.
- Memórias criadas/editadas/excluídas pelo usuário, busca e exportação JSON. Selecione até dez para o próximo envio. Nenhuma extração automática de lembranças ou credenciais.
- Ferramentas pelo chat Qwen: cálculos, listar/ler/criar/editar texto, abrir pasta, Bloco de Notas/Calculadora, URLs HTTPS, pesquisa pública e leitura de páginas com fontes.
- Cartões de proposta, aprovação e resultado confirmado no chat. Resultados persistem e podem ser analisados pela ALT. Conteúdo externo não concede permissões.
- Codex via CLI oficial com login ChatGPT, testado com prompt sintético e prévia de consentimento. Credenciais não são extraídas. Nesta prévia é conversa/código; os executores ALT pelo chat estão no Ollama/Qwen.
- API Anthropic opcional: chave protegida no cofre Windows DPAPI, verificação de autenticação/modelos, preços informados pelo usuário, limites por pedido/sessão/dia/mês, reserva conservadora e confirmação de cada envio. Desligada por padrão; não foi testada com chave real nesta sessão.
- CPU/RAM/disco/inventário GPU/driver e alocação de modelos quando disponíveis; perfis Notebook/Desktop e Game Mode.
- Atualização por manifesto e instalador locais com assinatura Ed25519, hash, tamanho e bloqueio de versões antigas. Não é um feed automático de atualização.

Claude por assinatura ainda não está integrado: a documentação oficial exige aprovação Anthropic para oferecer login/limites claude.ai em produtos terceiros. A alternativa disponível para configurar é a API paga, separada da assinatura. [Fonte oficial](https://code.claude.com/docs/en/agent-sdk/overview).

## Modos de autorização

| Modo | Alcance real |
|---|---|
| Observação | Conversa e propostas; não executa ferramentas. |
| Assistido | Sem prazo, até alterar ou revogar; aprovação individual de cada ação. |
| Leitura autorizada | Sem prazo; cálculo e leitura/listagem na pasta escolhida podem executar automaticamente. Gravação e internet continuam supervisionadas. |
| Controle amplo Windows | Sem prazo; perfil pessoal e pastas escolhidas. Credenciais, AppData, sistema, shell arbitrário e elevação de privilégios excluídos. Gravações no perfil têm confirmação adicional. |

Modos permanecem salvos ao reabrir a ALT, até você alterar ou revogar. Modos 3/4 exigem confirmação nativa com escopo e persistência explícitos. Isso não é controle irrestrito de mouse/teclado ou de todos os programas do Windows. Ferramentas adicionais de GUI e mais aplicativos ficam no roadmap. STOP ALL ACTIONS e Modo Jogo revogam a autorização, cancelam propostas e invalidam consentimentos de nuvem; retomar não restaura o acesso anterior.

## Pesquisa e navegação

Peça, por exemplo, “Pesquise na internet a documentação oficial do Ollama”. A ALT cria uma proposta. Ative uma sessão no painel Ferramentas, confira a consulta e aprove. O resultado recuperado inclui URLs; use “Pedir à ALT para analisar este resultado”. Para navegar entre fontes, peça a leitura de uma URL pública.

A pesquisa usa Bing RSS público; a leitura faz GET HTTPS sem cookies, sessão pessoal ou JavaScript. DNS é validado e a conexão é fixada em IP público; redirecionamentos são revalidados. Não acessa rede local, não executa downloads e não resolve páginas com login/CAPTCHA/JavaScript obrigatório. Indisponibilidade é informada; não são inventadas fontes. Abrir uma URL no navegador padrão é outra ação, aprovada separadamente.

## Desenvolver no outro PC

Pré-requisitos: Git, Node 24 LTS e Python 3.12 x64. Ollama para chat local. Fontes, contratos, locks, testes e documentação estão no Git.

```powershell
git clone https://github.com/caio306santana/ALT-.git
cd ALT-
npm.cmd ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm.cmd run dev
```

Use npm.cmd se o PowerShell bloquear npm.ps1; não precisa mudar políticas do computador. Mudanças no backend/Electron exigem Sair e iniciar novamente. npm.cmd start abre o frontend já compilado. O launcher remove ELECTRON_RUN_AS_NODE herdado de IDEs.

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run dist
```

O instalador fica em release/. O build comum não exige certificado ou chave privada de atualização. Para assinar o manifesto de release: `npm.cmd run release:manifest`.

**Continuidade da assinatura:** a chave pública é versionada em assets/update-public-key.pem. A chave privada original está somente em .local/update-private-key.pem ou no ambiente ALT_UPDATE_PRIVATE_KEY. Faça backup privado para assinar versões futuras no outro PC. Nunca envie essa chave ao Git. O script recusa substituir a identidade pública automaticamente. Para Authenticode, configure CSC_LINK/CSC_KEY_PASSWORD e rode `npm.cmd run dist:signed`; sem certificado o processo falha explicitamente. Nenhum certificado é comprado automaticamente.

O workflow GitHub Actions é manual e tem opções separadas para Authenticode e manifesto, dependendo de secrets que o proprietário configurar. Nenhum secret foi enviado nesta sessão.

## Dados e limites

Dados pessoais ficam em `%APPDATA%/ALT-AI/data/` (desenvolvimento pode usar alt-ai): histórico, memórias, configurações, ações e auditoria. O banco não é criptografado; a chave de API usa DPAPI separadamente. Não digite senhas ou tokens no chat. Detectores de segredos em memória são heurísticos, não garantia.

Encerre a ALT nos dois PCs antes de migrar os dados por um meio privado. Não envie bancos, logs, .env, chaves ou credenciais ao repositório. Para continuar programando, basta clonar o Git; .venv/node_modules são reconstruídos.

Esta é uma prévia. PC Ryzen/RX 7600 e Windows limpo ainda precisam de validação física. Notebook CPU pode levar dezenas de segundos no primeiro pedido com personalidade/ferramentas; pedidos longos continuam mais lentos. Qwen 2B/9B, API Anthropic real, assinatura Authenticode, navegador interativo, controle GUI amplo, voz e iOS não foram validados/entregues como completos.

Consulte [HANDOFF](docs/HANDOFF.md), [PROGRESS-0.2](docs/PROGRESS-0.2.md), [ROADMAP](docs/ROADMAP.md) e [Segurança](docs/SECURITY.md).
