# Plano de pendências — foco local

Atualizado em **30/10/2026**. Decisão mais recente do dono: **manter a ALT local no PC por enquanto; servidor próprio e iPhone independente ficam para depois**. Continuar em `main`, sem contratar serviços, provisionar servidor ou baixar modelos por causa deste plano.

## Estado que não deve ser confundido

| Item | Estado |
| --- | --- |
| Release instalável publicada | **0.5.2** (prévia, [RELEASE-0.5.2.md](RELEASE-0.5.2.md)); 0.5.1 preservada. Instalar/atualizar no destino ainda precisa de confirmação. |
| Código desta rodada | **0.5.2 em desenvolvimento**, com capacidades reais dos modelos e melhorias do gateway/PWA. Código compilado/testado, ainda sem instalador/release 0.5.2. |
| Etapa 1 do plano Drael | Implementada no código: metadados, contexto declarado/ativo, atualização de cache e aplicação das capacidades ao envio. Testes de API/UI e metadados reais registrados. Validação do pacote final/instalação permanece aberta. |
| Hermes | Hermes 3B foi encontrado instalado nesta rodada; **não foi baixado por este trabalho**. Metadados reais conferidos. Isso não substitui uma avaliação de suas respostas/velocidade. |
| iPhone atual | Existe cliente web remoto (PWA) dependente do PC. Gateway aprimorado e testado em simulação; não é app nativo nem IA executando no iPhone. |
| Tailscale | Instalação/conexão no notebook e conexão do iPhone foram verificadas. Publicação HTTPS/pareamento da ALT não concluídos nem validados; nenhuma rota Serve estava publicada na conferência final. |
| Servidor próprio | Adiado. Nenhum servidor contratado ou provisionado, nenhuma migração de dados e nenhuma API paga chamada nesta rodada. |

Evidências desta rodada: [CHECKPOINT-0.5.2.md](CHECKPOINT-0.5.2.md) e [metadados reais dos modelos](model-capabilities-0.5.2-smoke.json). O plano Drael completo continua em [PLANO-ACAO-DRAEL.md](PLANO-ACAO-DRAEL.md).

## Prioridade 1 — entregar e validar a base local

- [x] Gerar o **instalador final 0.5.2**, testar o backend empacotado, conferir os metadados/tokenizers incluídos, assinar o manifesto original, publicar e verificar o feed. Não distribuir o instalador 0.5.1 como se contivesse as mudanças novas. **Feito em 30/10:** ver [RELEASE-0.5.2.md](RELEASE-0.5.2.md).
- [ ] Atualizar o PC de destino, conferir versão em Sobre e verificar histórico/memórias/configurações e backup preservados. A chave privada da atualização continua fora do Git e precisa de backup privado.
- [ ] Confirmar a abertura real de Bloco de Notas/Calculadora (30/10: adiado no notebook porque o Bloco de Notas do dono estava aberto com texto não salvo; repetir com ambos fechados). Depois testar mais aplicativos/janelas e uma tarefa com alvo/texto corretos, pausa, cancelamento e resultado observado. O caminho direto anterior passou em execução simulada; essa evidência não fecha o teste real.
- [ ] Conferir capacidades no chat/seletor e trocar modelos/perfis. Validar mensagem de imagem incompatível, metadados indisponíveis e limites menores que o perfil. Aumento do contexto só por escolha explícita; sem usar automaticamente o máximo declarado pelo modelo.
- [ ] Medir novamente notebook e PC principal separadamente: primeiro texto/ação, carregamento, leitura do contexto, geração, total e memória disponível. No principal, conferir a GPU após o problema do driver registrado no checkpoint anterior e repetir o benchmark em condições comparáveis.
- [ ] Avaliar Qwen/Huihui e o Hermes 3B já instalado em português, debate, personalidade, fontes e chamadas de ferramentas. Não baixar Hermes 8B nesta retomada sem nova decisão do dono.

**Concluída quando:** o pacote novo estiver publicado e instalado/conferido, os casos reais obrigatórios tiverem evidência e a lentidão estiver medida. Dependências de outro PC ou modelo permanecem nomeadas; não marcar a prioridade inteira feita por ter compilado.

## Prioridade 2 — clareza e continuidade do chat

- [x] **Etapa 2 Drael** (30/10, [CHECKPOINT-0.5.3.md](CHECKPOINT-0.5.3.md); falta revisão na janela instalada): melhorar cartões de pesquisa/ações/arquivos, abrir/exportar artefatos pelo fluxo autorizado e distinguir sucesso, falha, resultado não confirmado e ausência de fontes. Revisar o selo “CONFIRMADO” em cartões não compactos.
- [x] **Etapa 3 Drael** (30/10, `fit_round` em todas as chamadas): recalcular contexto após cada retorno de ferramenta/captura, não apenas no envio inicial; preservar resultados completos fora do prompt.
- [x] Implementar compactação/resumo de continuidade (30/10: `summaries.py`; falta medir perda de cache) com origem e acesso ao original, preservando regras, mensagem e memórias escolhidas. Não transformar um resumo em nova autorização ou lembrança factual inventada.
- [ ] Validar PDFs longos/digitalizados, DOCX (30/10: PDF nativo e DOCX sintéticos validados com cobertura informada; PDF digitalizado/OCR longo e arquivos reais ainda pendentes) e recuperação de documentos reais, com indicação do que foi usado e do que ficou fora do contexto.

**Concluída quando:** testes de UI e de sequência de ferramentas passarem, os originais estiverem preservados e os casos reais de pesquisa/documento não produzirem confirmações falsas nem falhas de contexto sem orientação útil.

## Prioridade 3 — desempenho e experiência local

- [ ] **Etapa 4 Drael:** modos rápido/aprofundado por pedido, somente com controles aceitos pelo modelo e orçamento adequado ao PC. O reconhecimento do recurso foi adicionado; o seletor desses modos ainda não existe.
- [ ] **Etapa 5 Drael:** comparar catálogo estável com grupos menores; medir qualidade, latência e cache. Manter a referência se a alternativa não demonstrar melhora.
- [ ] Impedir repetição cega de escrita/clique/envio com resultado desconhecido; manter STOP, aprovações e regras do dono.
- [ ] Validar voz local com microfone funcional: captura, transcrição, Dora/voz disponível, interrupção e ausência de escuta indevida durante a resposta. Pesos reais de voz neste pacote ainda precisam de teste.
- [ ] Revisar interface em uso prolongado e personalidade escolhida: calma no tom, provocadora/irônica/desafiadora nas ideias conforme ajustes do dono, sem desviar pedidos práticos para debate.

**Concluída quando:** ganhos e qualidade forem demonstrados em medições comparáveis e fluxos reais, com cancelamento e histórico íntegros. Um botão novo não comprova ganho de desempenho.

## Prioridade 4 — opcionais locais de maior escopo

- [ ] **Etapa 6 Drael:** estudar e implementar execução isolada de código para análise de dados e artefatos. Depende de runtime compatível, limites e testes de isolamento; PowerShell/venv não serão apresentados como sandbox.
- [ ] **Etapa 7 Drael:** projetar cofre opcional para conversas/documentos/índices/backups, com migração e recuperação entre PCs. O cofre DPAPI de credenciais existente não cifra todo o histórico.
- [ ] Resolver **Authenticode** quando escolhido/necessário no destino. O manifesto Ed25519 já utilizado verifica a atualização do projeto e não substitui o certificado Windows.

Cada item é entrega independente, com suas dependências e validações. Nenhuma compra, instalação de infraestrutura ou mudança de proteção Windows foi feita por este plano.

## Adiado — iPhone e servidor

1. **PWA remota atual:** para retomar, conferir Serve/HTTPS, ligar o gateway da ALT, parear com código de uso único e testar no iPhone real. PC precisa ficar ligado. Testar texto, cancelamento, fotos, microfone, áudio, cartões, restauração da sessão e revogação. Não substituir outra publicação Tailscale nem ativar Funnel público.
2. **Servidor próprio:** escolher infraestrutura e consumo/custo, autenticação, backup, armazenamento e sincronização antes de migrar. No PC, preservar a opção local e acrescentar servidor próprio somente quando estiver funcional. O servidor permitirá conversar com o PC desligado, mas não controlar o Windows desligado ou ler arquivos que só estejam nele.
3. **App nativo iOS:** projeto e distribuição próprios. Pode usar o servidor; instalação nativa não significa processamento no aparelho. Para rodar também offline, precisará de runtime/modelo compatível, avaliação da memória/bateria e testes no iPhone real.
4. **Sincronização:** definir o que será compartilhado, com escolha do dono e tratamento de conflitos. Personalidade pode ser equivalente, mas trocar motor não garante respostas iguais. Nenhuma sincronização de conversas/memórias foi implementada nesta rodada.

## Regra para continuidade

Para cada item, registrar **implementado / testado / pendente**, commit, evidência e próximo passo. Preservar fontes, locks, documentação e testes no Git; bancos, credenciais, documentos pessoais, áudio, modelos, dados da rede e chaves privadas permanecem fora dele. Não declarar atualização instalada ou teste real concluído a partir de uma simulação.
