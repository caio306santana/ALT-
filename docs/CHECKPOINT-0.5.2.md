# Checkpoint 0.5.2 — código, sem nova release

30/10/2026. O dono pediu etapa 1 e acesso iPhone, esclareceu que deseja uso com o PC desligado e, após comparar execução no aparelho/servidor, decidiu **manter local por enquanto e deixar servidor para depois**. Pediu plano das pendências e envio de todo o código ao Git. Próxima leitura: [PENDENCIAS-LOCAL.md](PENDENCIAS-LOCAL.md).

## Implementado nesta rodada

- Metadados do Ollama normalizados para texto, imagem, ferramentas, recurso de raciocínio, controles/default quando informados e contexto máximo declarado. Campos ausentes ficam desconhecidos; não há tabela que invente capacidades pela tag do modelo.
- Cache curto, invalidação por digest/alteração do modelo, atualização forçada no botão da lista e invalidação após download. Seleção/perfil/Modo Jogo atualizam a conferência; pré-carga respeita limite declarado e ignora o pseudo-modelo Automático.
- Seletor/chat mostram capacidades, contexto ativo versus declarado, composição e reserva da resposta. Declarar 131K/262K não amplia silenciosamente o Notebook além de 4K. Se o modelo declarar limite menor, o payload respeita esse limite.
- Modelo que declara não aceitar ferramentas não recebe o catálogo; imagem continua passando pela conferência de suporte. Ações locais diretas usam o serviço de permissões e não dependem do suporte do motor a ferramentas.
- Gateway do celular ganhou streaming sem agregar a resposta inteira, cancelamento, metadados autenticados, mensagem clara quando não há modelo local e caminho direto sem modelo. Origem telefone é imposta pelo gateway; nenhuma ação se autoaprova a partir dele.
- Cliente PWA apresenta texto progressivo, botão de interromper, recuperação de propostas ao abrir a conversa, preservação do rascunho em falha antes da aceitação e estados de resultado sem converter falha/não confirmação em “feito”.
- Configuração Tailscale recusa substituir outra publicação HTTPS ou Funnel na porta em uso; falha ao publicar encerra o gateway recém-iniciado. Nada dessa preparação cria app nativo ou servidor de IA autônomo.

## Validação

- A suíte final passou: **242 testes Python, 1 ignorado por privilégio de symlink, e 5 Node**. Inclui streaming incremental e preservação de publicação Tailscale. Depois de limitar também a reserva de saída para modelos que declarem contexto muito pequeno, os **5 testes de metadados/orçamento foram repetidos e passaram**; o Notebook normal não teve o contexto ampliado.
- TypeScript/Vite compilou; renderer sintético passou, incluindo capacidades Qwen conhecidas, metadados desconhecidos, limites declarado/ativo distintos, ação direta e catálogo Hermes. Captura sintética foi inspecionada. Não equivale à revisão da janela instalada do dono.
- Smoke em banco temporário consultou o **Ollama real**, sem inferência, download, ações Windows ou chamadas pagas: Qwen 4B e Huihui 4B declararam texto/imagem/ferramentas/raciocínio e máximo 262.144; Hermes 3B já instalado declarou texto/ferramentas, sem visão/recurso separado de raciocínio e máximo 131.072. Todos permaneceram em 4.096 ativos no Notebook. Controles ausentes do Hermes não foram inventados. [Relatório](model-capabilities-0.5.2-smoke.json).
- O teste de streaming observa o primeiro trecho antes de liberar a conclusão do provedor simulado, comprovando que o gateway não aguarda toda a resposta para encaminhar. Autenticação, origem telefone, aprovação e ausência de modelos têm regressões próprias.
- Tailscale foi encontrado instalado/conectado e o iPhone apareceu conectado; tentativa de Serve indicou ativação necessária na conta. O dono informou ativação, mas publicação/pareamento não foram concluídos/validados antes da decisão de adiar. Conferência final de Serve retornou configuração vazia, sem gateway na porta 47823. Host/IPs, códigos e tokens não foram incluídos no Git.

## Não concluído / não alegar

- **Sem build do backend congelado, instalador, manifesto ou release 0.5.2.** O instalador publicado continua sendo o da 0.5.1 e permanece inalterado. O número 0.5.2 identifica o código em desenvolvimento, não um app já instalado.
- Sem instalação/atualização do aplicativo aberto, abertura real do Bloco de Notas, teste de voz com pesos reais, validação de documentos longos ou nova medição do PC principal nesta rodada.
- Hermes 3B foi encontrado instalado externamente; não foi baixado nesta rodada e suas respostas/desempenho não foram avaliados pelo smoke de metadados. Hermes 8B não foi baixado.
- Sem pareamento real do iPhone, validação Safari de áudio/fotos/notificações, app nativo iOS, execução de modelo no iPhone, servidor próprio ou sincronização entre aparelhos.
- Nenhuma infraestrutura foi contratada/provisionada, nenhuma proteção Windows foi alterada e nenhuma API paga foi chamada.

Fontes técnicas conferidas: [Ollama model details](https://docs.ollama.com/api-reference/show-model-details), [controles de raciocínio](https://docs.ollama.com/capabilities/thinking) e [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve). Os testes de metadados confirmam o comportamento local; documentação externa não substitui a validação dos nossos fluxos.
