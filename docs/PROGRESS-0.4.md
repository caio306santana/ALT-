# ALT-AI 0.4 — progresso na branch `work/advanced-0.4`

Atualizado em 29/10/2026. Esta branch parte da correção 0.3.1 de `main`. O instalador 0.4.0 foi gerado para teste local; sem assinatura digital, o Controle Inteligente de Aplicativos do Windows pode bloqueá-lo (ver [STATUS.md](STATUS.md)).

## O que foi integrado nesta rodada

| Etapa | Integrado | Evidência |
| --- | --- | --- |
| 2 — Tarefas com várias ações | Painel **Tarefas**: objetivo → plano do modelo local (em segundo plano, JSON restrito às ferramentas disponíveis) → revisão/edição → execução com conferência de cada resultado → pausa/retomada. A retomada reaproveita ação já concluída ou proposta ainda pendente; não repete ações. Ferramentas de arquivo ficam presas à pasta escolhida para a tarefa. Replanejamento opcional (até 2 vezes) preserva as etapas já verificadas. | `tests/test_agent_stages.py` e smoke real (abaixo). |
| 3 — Memória semântica, documentos e projetos | Projetos; importação nativa de PDF/DOCX/TXT/MD; indexação com EmbeddingGemma (vetores locais por hash do conteúdo, nunca usa vetor desatualizado); busca semântica no painel Memória; modo **Recuperação semântica** em Controle e regras, que injeta memórias e trechos de documentos no chat e volta para busca por termos se o EmbeddingGemma faltar; conversa vinculada a projeto busca só nele; resumos de conversa por projeto sempre como rascunho revisado (opção de gerar automaticamente a cada 12 mensagens). | `tests/test_agent_stages.py` e smoke real. |
| 5 — Confiabilidade e personalidade | Conferência determinística de cada resposta do chat: recalcula contas escritas (notação brasileira, arredondamento, “12,5% de 840 = 105”) e marca links que não vieram de pesquisa/leitura confirmada nem do usuário. O resultado aparece abaixo da resposta. Laboratório ganhou casos de situação real (pedido prático, desabafo, fontes sem internet, contas no texto) com verificações automáticas explícitas; notas humanas continuam suas. Tarefas reconferem cálculos de forma independente. | `tests/test_agent_stages.py` e smoke real. |
| Acesso total (modo 4) | Pedido do usuário: o modo 4 virou **Acesso total**. Tudo que não estiver bloqueado em Controle e regras executa sem aprovação: internet, **download de arquivos** (nova ferramenta, HTTPS público, até 1 GB, nunca executa o arquivo), leitura/gravação em qualquer pasta local por caminho completo, apps, navegador e tarefas. Arquivos sobrescritos ganham cópia em `file-history`. Continuam fora: arquivos de credenciais/AppData, compartilhamentos de rede, shell, privilégios de administrador. STOP revoga na hora. | `tests/test_agent_web.py`, `tests/test_agent_stages.py`. |
| Aviso de nova versão | O app consulta a última release do GitHub ao abrir e a cada 6 h, mostra nome e **notas da release**, baixa instalador e manifesto, confere assinatura Ed25519 e SHA-256 e só então libera “instalar e reiniciar”. Botão “Procurar nova versão” em Sobre. | `tests/update-feed.test.cjs`. **Limite:** o repositório é privado; sem login o app não enxerga as releases (ver STATUS). |

| Design | Barra lateral estilo Claude (ícone + nome, conversas recentes, recolhível), cabeçalho único gerado por um mapa de telas, camada `refresh.css` com superfícies calmas, raio configurável em todos os controles, textos legíveis e ícones nos modos de execução. | Smoke visual com capturas de chat, tarefas, memória, ferramentas, barra recolhida e tema claro. |

Correções vindas do smoke real: documentos agora são divididos por seção (uma consulta de viagem caía numa receita); vetores usam os prompts do EmbeddingGemma; o planejador recebe só as ferramentas que o objetivo pede (o Qwen inventava um passo de navegador) e corrige plano incompleto antes da revisão; replanejar cobre só o que falta; mensagens de momento difícil recebem instrução de acolhimento (o modelo foi irônico com quem perdeu o emprego).

Também: `pypdf`, `python-docx` e `lxml` entraram em `requirements.txt`/`requirements-lock.txt` (antes estavam só no ambiente local e faltariam no pacote).

## O que ainda falta

- **2:** testar tarefas longas com navegador ALT e janelas reais; interface de edição de plano é JSON simples.
- **3:** validar com documentos reais maiores (PDF longo, DOCX com tabelas) e medir tempo de indexação no PC principal. PDFs digitalizados precisam de OCR, não incluído.
- **4:** integrada na 0.4.1 (seletor nativo, painel em Ferramentas, chat e tarefas). Falta validar com mais aplicativos reais.
- **5:** as verificações automáticas são heurísticas; a avaliação humana da personalidade em uso real continua com o usuário.
- **6:** backup/restauração integrados na 0.4.1 (Sistema → Backup e restauração). Falta certificado de assinatura do Windows.
