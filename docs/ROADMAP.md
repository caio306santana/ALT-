# Roadmap completo

O escopo desta entrega é Fases 1 e 2. Recursos incompletos não são apresentados como disponíveis. A referência visual orienta a organização, sem personagens ou materiais gráficos protegidos.

| Fase | Estado | Entregas |
|---|---|---|
| 1 — Fundação | Implementada e validada na prévia | Repositório; Electron/React/TS/Vite; FastAPI; SQLite; contratos; observação; STOP; janela baseada na referência. |
| 2 — Inteligência local | Implementada; chat real 4B validado | Ollama; descoberta de modelos; streaming; histórico; troca local sem reiniciar; erros e cancelamento; Qwen 2B/4B/9B quando instalados. 2B/9B ainda não testados nesta sessão. |
| 3 — Personalização | Parcial antecipada | Temas Pink/Blue/Red/Green/Minimal/Custom, cor, opacidade, fonte, neon, compacto e animações persistidos. Faltam cores secundárias, escala, opacidade por área, claro/escuro, bordas/sombras, temas salvos, configuração de atalhos e posições predefinidas. Arrastar/redimensionar, bandeja, topo e restaurar posição já existem; detecção de jogos fica na fase 8. |
| 4 — Memória | Planejada | Memórias pessoais e de projetos, preferências, decisões, tarefas, conhecimento autorizado; busca, correção, edição, exportação, exclusão e resumos de continuidade. Histórico local já existe, mas não é memória semântica. Não armazenar credenciais nessa memória. |
| 5 — Multi-IA | Planejada | Roteador; SDK/App Server oficial Codex; Claude Code/Agent SDK; APIs opcionais OpenAI/Anthropic/Gemini; autenticação suportada; capacidades/contexto/limites/custos reais; orçamento por sessão/dia/mês; bloqueio de gasto; contexto com prévia e consentimento antes de nuvem. Fallback manual, assistido e automático previamente autorizado; checkpoint e retomada; distinguir limite, auth, conexão, temporário, incompatibilidade, execução e orçamento. Não inventar saldos/renovação. |
| 6 — Voz | Planejada | Whisper.cpp local, Piper PT-BR, push-to-talk, seleção de voz/microfone, volume/velocidade, escuta/processamento/reprodução, interrupção, texto apenas. Palavra de ativação após testes de privacidade e consumo. |
| 7 — Windows e ferramentas | Planejada | Abrir/fechar apps autorizados; abrir pastas; buscar/criar/editar arquivos; cálculo; URLs; pesquisa com fontes reais; organização/código; lembretes/timers; monitorar tarefas; conectores de apps e rotinas. Ferramentas com esquema validado, resultados estruturados, aprovação e auditoria. Níveis 2–4 com escopo/prazo/revogação e confirmação de operações críticas. Texto do modelo nunca concede autorização. |
| 8 — Desempenho | Parcial antecipada | CPU/RAM/disco e inventário CPU/GPU/driver, VRAM alocada pelo Ollama, tokens/tok/s/latência reais. Faltam coletores confiáveis de uso/temperatura/VRAM total, inferência CPU/GPU detalhada, custos de nuvem, tamanho/contexto consultado por modelo, modo jogo que suspende tarefas, salva estado, descarrega modelos e minimiza/reduz efeitos. Não prometer liberação de memória não confirmada. |
| 9 — Proteção | Base e testes iniciais | Continuar testes de injection, vazamento, path traversal, symlinks/junctions, isolamento, arquivos/downloads, antivírus, autorização, cancelamento e recuperação. Scanner/quarentena isolada para arquivos desconhecidos antes de ferramentas com acesso real. Armazenamento seguro de futuras credenciais. Não desabilitar Defender, acessar cookies ou elevar privilégios ocultamente. |
| 10 — Distribuição | Prévia Windows gerada | Instalador Windows com runtime Python incluído; backend e janela empacotados validados; setup de dependências/modelos com consentimento, logs e documentação. Faltam certificado, atualização assinada, testes em Windows limpo, atualização/migração e cliente iOS. |

## Personalidade e apresentação

Padrão: português brasileiro, calma, natural, direta, inteligente e explicativa; sem alegar ações não executadas. Editor de nome, tom, formalidade e instruções de personalidade fica nas fases 3/4. Segurança permanece independente do prompt. O layout admite um componente de avatar futuro, mas não há avatar nesta entrega.

## Hardware-alvo e iPhone

O alvo solicitado é Ryzen 9 3900, 32 GB RAM, RX 7600 8 GB e SSD 1 TB. Verificar drivers/ROCm/Vulkan e o backend de GPU realmente usado no PC de destino. Não inferir consumo de VRAM pelo tamanho do arquivo. Permitir fallback CPU/RAM pelo Ollama e apresentar o resultado observado.

O iPhone 13 será cliente remoto (React Native/Expo a avaliar), com texto/voz, memória autorizada, modelos, tarefas, status, ações e alertas. Qwen permanece no PC. Usar identidade autenticada, TLS e VPN privada, sem expor Ollama na internet; confirmar operações remotas sensíveis. Build/distribuição iOS exigirão ferramentas Apple compatíveis.
