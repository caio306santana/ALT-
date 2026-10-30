# Checkpoint da ALT 0.5

Branch: `work/0.5`. Pasta de trabalho neste PC: `C:\Users\caios\Downloads\ALT--main\ALT-current`. A pasta irmã `ALT--main` é uma cópia antiga sem Git, e `C:\Users\caios\ALT-` ficou num commit antigo; não usar nenhuma das duas.

Plano completo: [PLAN-0.5.md](PLAN-0.5.md). Referências estudadas, só como leitura, sem copiar código: OpenJarvis (Stanford) e Mark-LVI.

## O que a 0.5 entrega (todas as etapas do plano)

| Etapa | O que faz |
| --- | --- |
| 0 — fechar o aberto | Anexos (imagem, PDF com OCR, Word, texto), voz pelo Whisper, atalhos de teclado nas janelas, Claude com ferramentas, Game Mode pela CPU, rodada de correção de ferramenta. |
| 0.5 — velocidade | Diagnóstico em [LATENCY-0.5.md](LATENCY-0.5.md); velocidade de referência por modelo com aviso; placa ocupada leva ao modo leve; instrução de sistema fixa e contexto do turno no fim; ferramentas fixas (cache reaproveitado, 16/16 no smoke); pré-carga, 30 min carregado, embeddings na CPU, resumo só com o chat parado, até 1024 tokens; interface em lotes de 50 ms. |
| 1 — confiabilidade | Resultado com estado (feito, não confirmado, falhou, pergunta); abrir traz para a frente o que já está aberto e confirma o processo; fechar pontua, pergunta em empate e nunca mira a ALT nem o Ollama; conteúdo de fora entre marcadores neutralizados; `/no_think` ignorado; trava contra loop. |
| 2 — permissões | "Sempre permitir" para programas, sites e pastas; conversa protegida depois de ler segredo, CPF, cartão ou tokens de chat; desfazer gravação e download; cartões críticos expiram em 90 s; exemplos aprendidos (desligado). |
| 3 — ferramentas | Ver a tela e responder sobre ela; volume, brilho e música com leitura antes e depois; lembretes pelo Agendador do Windows (testado de verdade). |
| 4 — voz JARVIS | Segurar Ctrl+Espaço de qualquer lugar; "Hey Jarvis" (ONNX direto, 0,999 contra 0,0 no teste); "Ei ALT" experimental; voz Dora pt-BR local, frase a frase, com corte; microfone fechado enquanto ela fala; painel Voz. |
| 5 — memória | Sugestões de fatos para revisar (nada entra sozinho); `memory_recall`; leituras voltam ao modelo e ele responde na mesma mensagem (até 4 rodadas). |
| 6 — proativa | Resumo da manhã (clima Open-Meteo, lembretes, "da última vez", tópicos, só fatos); rotinas; puxar conversa com regras; tópicos; alertas do PC; aba Rotinas. |
| 7 — modelo automático | Opção "Automático": simples no 4B, médio no 9B, complexo no Claude com prévia (ou 9B); Game Mode e placa ocupada forçam o 4B; aprende por faixa. |
| 8 — iPhone | Gateway em 127.0.0.1:47823 publicado pelo `tailscale serve`; QR code de uso único; PWA com chat, voz, foto, cartões e notificações; nada roda sozinho a partir do celular. [IPHONE.md](IPHONE.md). |

## Evidência de teste

- Python: suíte completa passando (ver o commit final); Node 5/5; build TypeScript/Vite.
- Real, neste PC:
  - Calculadora aberta e fechada com confirmação; Spotify já aberto trazido para a frente em 0,2 s;
  - Ctrl+N no Bloco de Notas;
  - lembrete criado, listado e cancelado no Agendador do Windows;
  - notificação do Windows exibida;
  - voz Dora tocada no alto-falante, e a fala dela transcrita certinho pelo Whisper;
  - "Hey Jarvis" detectado em áudio sintético;
  - clima do Open-Meteo;
  - gateway do celular servindo a PWA e recusando acesso sem pareamento.
- Smoke real de ferramentas, Qwen 3.5 4B com ferramentas fixas: **16/16** (`docs/full-access-smoke-stable.json`). As 14 ações foram certas, e as 2 conversas ficaram curtas e sem chamar ferramenta. Para chegar lá, entraram três reparos:
  - ferramenta chamada pelo próprio nome;
  - "abre o youtube" quando o modelo abre só o navegador;
  - lista de janelas só quando uma ferramenta de janela é provável.

  Cerca de 10 s por ação por causa da GPU degradada (veja abaixo).

## Achados e pendências que dependem do usuário

- **GPU lenta desde 29/10 às 21:08:** travamento do driver de vídeo (LiveKernelEvent). O 4B caiu de 57 para cerca de 4,5 tok/s. Recomendado reiniciar o PC e medir de novo com `scripts/benchmark_latency.py --cases long`.
- **Microfone:** o único microfone do Windows é o "WO Mic Device", que só funciona com o app WO Mic conectado. A voz precisa de um microfone de verdade ou do WO Mic ligado.
- **Chave de atualização:** a chave privada (`.local/update-private-key.pem`) não está neste PC; provavelmente está no notebook onde as releases 0.1 a 0.3 foram geradas. Sem ela, o manifesto da 0.5 não é assinado. O script se recusa, de propósito, a trocar a identidade sozinho.
- **Assinatura de código (Authenticode):** não dá para fazer daqui. Opções: Azure Trusted Signing (assinatura mensal) ou um certificado OV de uma autoridade certificadora.
- **iPhone:** o Tailscale ainda não está instalado neste PC; o passo a passo está em IPHONE.md.
- Interface: os fluxos foram testados por API e testes. Falta uma passada manual na janela (clicar em tudo) com o app rodando.

## Cuidados para retomar

- Nunca publicar `.local`, bancos, logs, modelos, áudio, documentos de Downloads ou chaves.
- Fechar só processos abertos pelo agente, pelo PID, conferindo o horário de início. Nunca `taskkill /IM`.
- Editar código com Edit ou com scripts em arquivo; o heredoc do bash desta máquina come barras invertidas.
