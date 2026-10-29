# Roadmap completo

A prévia 0.3 amplia as Fases 1 e 2 com os blocos solicitados de personalização, memória, provedores, ferramentas e proteção. O roteiro completo continua abaixo; capacidades parciais não significam que a fase inteira está concluída. Identidade visual original, sem personagens ou materiais gráficos protegidos.

| Fase | Estado | Entregas |
|---|---|---|
| 1 — Fundação | Implementada e validada na prévia | Repositório; Electron/React/TS/Vite; FastAPI; SQLite; contratos; observação; STOP; janela baseada na referência. |
| 2 — Inteligência local | Implementada; chat real 4B validado | Ollama; descoberta de modelos; streaming; histórico; troca local sem reiniciar; erros e cancelamento; Qwen 2B/4B/9B quando instalados. 2B/9B ainda não testados nesta sessão. |
| 3 — Personalização | Expandida na 0.2 | Personalidade editável comum aos motores; perfil clicável e nome opcional; temas/cor principal/secundária/neon/opacidade/fonte/escala/claro-escuro/efeitos/bordas/compacto/animações; temas pessoais; atalho global configurável; tamanho/posição e topo persistentes. Faltam refinamento de temas completos, opacidade granular de todas as áreas e detecção automática de jogos. |
| 4 — Memória | Continuidade revisada na 0.3 | CRUD, busca, exportação/importação JSON atômica, rascunho de resumo local revisado e procedência; recuperação por termos opt-in ajustada ao contexto. Faltam busca semântica, importação de documentos e tarefas/resumos automáticos por projeto. |
| 5 — Multi-IA | Codex real e API opcional | Qwen e Codex CLI oficial autenticado ChatGPT com prévia/recibo de contexto e troca manual; Anthropic API opcional com DPAPI, autenticação/modelos, preços/orçamentos e reservas, ainda sem teste pago real. Claude por assinatura depende de aprovação Anthropic. Faltam APIs OpenAI/Gemini, descoberta mais detalhada de capacidades/contextos, fallback assistido/automático autorizado, checkpoints de tarefas de engenharia e medição ampliada de custos. Não inventar saldos/renovação nem gastos automáticos. |
| 6 — Voz | Planejada | Whisper.cpp local, Piper PT-BR, push-to-talk, seleção de voz/microfone, volume/velocidade, escuta/processamento/reprodução, interrupção, texto apenas. Palavra de ativação após testes de privacidade e consumo. |
| 7 — Windows e ferramentas | Navegador e controle ampliados na 0.3 | Política por capacidade persistente com prompt/limites visíveis; arquivos e busca recursiva; executáveis registrados por hash e fechamento normal rastreado; navegador isolado HTTPS com DOM, clique/digitação por snapshot e proxy público. Faltam GUI Windows genérica, várias abas e tarefas longas de navegador, rotinas/conectores e rastreamento de apps que transferem janela a outro processo. |
| 8 — Desempenho | Monitor e Game Mode funcionais | CPU/RAM/disco/inventário GPU/driver, VRAM do Ollama, métricas de inferência e perfis de notebook/desktop; Game Mode revoga/suspende ações, tenta descarregar modelo e oculta janela. Faltam coletores confiáveis de temperatura/VRAM total/GPU, detecção automática de jogos, contexto máximo por modelo e medição mais detalhada. Não prometer liberação de memória sem confirmação. |
| 9 — Proteção | Testes ampliados na 0.2 | Auth, contexto/consentimento/replay, orçamento, cofre DPAPI, scopes/traversal/ADS/devices/concorrência, STOP, pesquisa/DNS/SSRF e assinaturas de atualização. Teste de symlink ignorado nesta máquina por falta de privilégio de criação; continuar testes reais de junctions e ambiente hostil. Faltam scanner/quarentena para downloads e análise isolada; nenhum binário é executado pela pesquisa. Não desabilitar Defender nem acessar credenciais ocultamente. |
| 10 — Distribuição | Prévia com atualizações verificadas | NSIS/runtime incluído, fuses/ASAR, setup de dependências/modelos, manifesto Ed25519/hash/anti-rollback e confirmação local de atualização, pipeline Authenticode opcional. Faltam certificado real configurado, feed automático autenticado, Windows limpo/PC principal, migrações mais completas e iOS. A assinatura de manifesto não é certificado Windows. |

## Personalidade e apresentação

Padrão aprovado: português brasileiro; calma na forma de falar, provocadora, irônica e desafiadora nas ideias, com paciência. Editor de nome/tom/ironia/desafio/proximidade/formalidade/instruções implementado. Personalidade não altera permissões nem inventa execução/memórias. O glifo de perfil é abstrato; não há avatar humano nesta entrega.

## Hardware-alvo e iPhone

O alvo solicitado é Ryzen 9 3900, 32 GB RAM, RX 7600 8 GB e SSD 1 TB. Verificar drivers/ROCm/Vulkan e o backend de GPU realmente usado no PC de destino. Não inferir consumo de VRAM pelo tamanho do arquivo. Permitir fallback CPU/RAM pelo Ollama e apresentar o resultado observado.

O iPhone 13 será cliente remoto (React Native/Expo a avaliar), com texto/voz, memória autorizada, modelos, tarefas, status, ações e alertas. Qwen permanece no PC. Usar identidade autenticada, TLS e VPN privada, sem expor Ollama na internet; confirmar operações remotas sensíveis. Build/distribuição iOS exigirão ferramentas Apple compatíveis.
