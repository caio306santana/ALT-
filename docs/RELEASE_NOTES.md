# ALT-AI 0.1.0 — prévia Windows

Primeira versão executável das Fases 1 e 2: chat local real com Ollama, streaming, histórico SQLite, modelos locais, aparência configurável, temporizador de foco, métricas disponíveis e STOP.

O instalador inclui interface Electron e backend com runtime Python. Não exige Node/Python no PC de destino. Ollama e modelos são detectados/configurados no aplicativo, com confirmação para downloads. Qwen 2B/4B/9B ficam disponíveis quando instalados. Nenhuma API paga habilitada.

Perfil Automático adapta contexto/saída/threads ao hardware. Notebook econômico e Desktop podem ser escolhidos manualmente em Configurações → Comportamento. O raciocínio interno do Qwen 3.5 fica desativado no chat para reduzir longas esperas.

Validação: 14 testes críticos passaram; build TS/Vite, backend PyInstaller e NSIS concluídos; backend empacotado validou autenticação, SQLite e telemetria; janela empacotada aberta e inspecionada; chat real Qwen 4B e persistência confirmados. Desempenho depende de carregamento, fila e hardware.

Limites desta prévia: instalador não assinado; instalação em Windows limpo e aceleração no PC Ryzen/RX 7600 ainda precisam de validação. Voz, automação de Windows, memória semântica, nuvem/Codex/Claude, fallback e iOS ainda não estão disponíveis. Histórico local não é criptografado; não inserir segredos.

Baixe o `.exe` abaixo. `SHA256SUMS.txt` permite conferir o arquivo. Código completo, instruções para desenvolver e próximos passos ficam no repositório em `README.md`, `docs/HANDOFF.md` e `docs/ROADMAP.md`.
