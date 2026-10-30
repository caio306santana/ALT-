# ALT no iPhone (PWA)

Página leve, sem build, servida pelo gateway do backend (`backend/remote.py`, `127.0.0.1:47823`). O Tailscale a publica só dentro da tailnet do dono, com HTTPS real. O passo a passo para o usuário está em `docs/IPHONE.md`.

- `index.html` e `app.js`: chat, microfone (PCM de 16 kHz para o Whisper do PC), foto (JPEG de até 1344 px), cartões de aprovação, voz da Dora tocada no celular e notificações.
- `sw.js`: guarda só a casca do app; o `/api` sempre vai ao PC. Mostra as notificações.
- Nada roda sozinho a partir do celular. Comandos do PowerShell e gravações críticas só são aprovados no PC.
