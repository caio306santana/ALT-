# Voz local em desenvolvimento na 0.5

O renderer captura áudio mono PCM a 16 kHz; `/voice/transcribe` usa faster-whisper small no processador, localmente. O modelo só é baixado depois da confirmação do usuário. Respostas por voz usam a síntese local do Windows disponível no Electron.

Pipeline validado neste PC com áudio sintético da Microsoft Maria: HTTP 200, áudio de 7 s, transcrição de 4,2 s e total de 8,75 s incluindo carga. Houve erros de reconhecimento; isso não valida a qualidade do microfone nem a conversa por voz de ponta a ponta.

Ainda pendentes: captura no backend, Ctrl+Espaço global, palavra de ativação, Dora, fala frase a frase, medidor e seleção de microfone. Seguir `docs/PLAN-0.5.md`; não apresentar essas partes como prontas.
