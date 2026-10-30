# Checkpoint da ALT 0.5

Branch: `work/0.5`. Base recebida do usuário: `5123031`.
Checkout desta sessão: `C:\Users\caios\Downloads\ALT--main\ALT-current`.
Não usar a pasta irmã `ALT--main` como base: ela é uma cópia antiga sem Git.

## O que terminou nesta rodada

- Recuperado o trabalho publicado de voz, anexos, atalhos, correção de ferramentas, Claude e Game Mode.
- Personalidade não promete executar quando não há ferramenta; confirmações dependem de resultado confirmado.
- Métricas de preparação, carga, leitura, geração e primeiro texto na mensagem, com painel Desempenho. Provedores que não informam uma etapa deixam o campo desconhecido.
- Corrigida a sobreposição do botão Acesso total; build recarregado e conferido visualmente na janela de desenvolvimento, com conversa preservada.
- PDFs digitalizados agora têm OCR local nas páginas sem texto; PDF com texto mantém extração normal. O OCR usa o componente do Windows e PDFium, sem envio de documentos à nuvem.
- TXT/PDF/DOCX exibem aviso de leitura e quantidade de texto extraído; OCR é identificado como sujeito a erros.
- Validação de JPEG pelo decoder e correção do orçamento dos trechos de documentos. Anexos sem espaço não são omitidos silenciosamente.
- Perguntas sobre capacidades recebem os dados reais do provedor, inclusive visão. O Qwen 3.5 4B informou `vision`; geração de imagens continua sem integração.
- Dependências e especificação PyInstaller atualizadas para PDFium, Pillow e o helper OCR.

## Evidência de teste

- **127 testes Python passaram; um ignorado por privilégio de symlink. Cinco testes Node passaram; TypeScript/Vite passou.**
- `scripts/smoke_document_chat.py`: **10/10** casos reais pelo Ollama, nos modelos 4B e 9B, cobrindo TXT, PDF com texto, Word com tabela, PDF digitalizado e JPEG. Dados exclusivamente sintéticos; relatório em `docs/document-chat-smoke.json`.
- Documentos reais de Downloads, com autorização do usuário, lidos localmente: PDF com texto (814 caracteres), catálogo de 32 páginas digitalizadas (10.369 caracteres por OCR em 14,407 s) e Word (17.425 caracteres). Conteúdos não publicados no Git.
- No app aberto, o 4B respondeu “Conexão confirmada”; o cartão também informou a abertura do Google durante o teste do usuário.
- Whisper small baixado com autorização para `.local/ui-test-profile/data/voice/`. Transcrição real de áudio sintético da Maria respondeu HTTP 200; reconheceu parte da frase e cometeu erros. Microfone e conversa falada completa ainda não validados.
- Medição inicial de inferência em `docs/latency-initial.json`; método e limites em `docs/VALIDATION-0.5-STAGE0.md`. A meta de velocidade e a etapa 0.5 não estão concluídas.

## Próximo passo imediato

1. **Reiniciar somente o app de desenvolvimento isolado para carregar o backend com OCR e capacidades corrigidas.** O controle de janela foi interrompido por Escape antes dessa atualização; recarregar só a interface não troca os módulos Python. Não declarar que o app instalado foi atualizado.
2. Conferir um PDF digitalizado pelo clipe na janela aberta, testar a resposta sobre visão/geração e o layout em janela menor. Usar dados sintéticos ou arquivos de Downloads autorizados; não enviar esses conteúdos à nuvem.
3. Concluir a etapa de velocidade do plano: casos longos/memória/anexos, prefixo fixo, comparação de ferramentas estáveis, aquecimento, keep-alive, embedding na CPU e resumos ociosos. Os dados iniciais mostram que gerar argumentos de ferramenta também é um gargalo; não presumir que só o prompt explique a lentidão.

## O restante do plano está pendente

| Etapa de `PLAN-0.5.md` | O que ainda falta |
| --- | --- |
| 0 — validação | Microfone real, voz completa no app, atalhos em janela própria, Game Mode real na CPU e Claude pago configurado/autorizado. |
| 0.5 — velocidade | Implementação e comparação completa antes/depois; metas ainda sem comprovação. |
| 1 — confiabilidade | Contrato de resultado, abrir/focar e fechar verificados, fronteira de dados externos, loop guard e autoconhecimento ampliado. |
| 2 — permissões/desfazer | Sempre permitir por alvo, contaminação da sessão, desfazer e revisão das confirmações. |
| 3 — ferramentas | Tela, volume/brilho/mídia, lembretes persistentes. |
| 4 — JARVIS | Captura no backend, Ctrl+Espaço, wake word, Dora, fala incremental, seleção/teste de dispositivos e STOP completo. |
| 5 — memória | Sugestões revisadas, orçamento de lembranças e “da última vez”. |
| 6 — proatividade | Agendador, resumo da manhã, silêncio, limites e alertas. |
| 7 — modelo automático | **Usuário escolheu híbrido:** local no simples, nuvem no complexo com prévia e aprovação. Ainda não habilitado; não ativar API paga sozinho. |
| 8 — iPhone | Gateway separado, Tailscale, pareamento, PWA e notificações. |
| 9 — entrega | Testes completos, runtime empacotado, instalador, manifesto, documentação, merge e validação de atualização. |

Pendência explícita do usuário: **tela Sobre e seus três botões de atualização precisam funcionar no aplicativo instalado**. Atualizar o texto antigo sobre voz/GUI e validar releases, procura de atualização e manifesto local; não basta exibir botões.

## Cuidados para retomar

- O app instalado informado pelo usuário segue na 0.4.1. Metadados do checkout ainda são 0.4.2; só mudar para 0.5.0 ao preparar a entrega completa.
- Perfil isolado: `.local/ui-test-profile`. Não sobrescrever dados do usuário em AppData.
- Helper Electron iniciado nesta sessão: PID 17508, caminho `ALT-current/node_modules/electron/dist/electron.exe`, início 29/10/2026 23:36:18. Conferir identidade/horário antes de encerrar; PIDs podem ser reutilizados. Nunca matar processos por nome.
- O Ollama foi iniciado nesta sessão e usado nos testes locais. Não encerrar instâncias arbitrárias nem alterar sua configuração de GPU sem medição e consentimento.
- OCR foi validado em desenvolvimento neste Windows, com reconhecimento pt-BR instalado. **Ainda testar o helper e a DLL no pacote PyInstaller.** Limite explícito de 50 páginas que precisam de OCR; nenhuma página é descartada silenciosamente.
- Dora, wake word e recursos do Tailscale ainda podem exigir downloads/configuração do usuário. A autorização dada até agora foi para o Whisper small.
- Nunca publicar `.local`, bancos, logs, modelos, áudio, documentos de Downloads ou chaves. A chave privada original de atualização não foi configurada neste checkout.
- Há um stash local preservando os diagnósticos anteriores à importação de `5123031`; as mudanças úteis já foram integradas. Não reaplicar o stash sobre este código.
- O agente não tem acesso confiável ao percentual de créditos/contexto. Não inventar aviso automático de 2%; manter checkpoints verificáveis.
