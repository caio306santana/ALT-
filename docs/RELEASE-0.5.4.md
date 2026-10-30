# Entrega 0.5.4 — 30/10/2026

[Release publicada como prévia](https://github.com/caio306santana/ALT-/releases/tag/v0.5.4), tag `v0.5.4` no commit `8708860`. Traz os ajustes de velocidade do notebook descritos em [LATENCY-0.5.md](LATENCY-0.5.md):
- um só modelo de conversa carregado;
- aviso de RAM baixa;
- modelo mantido carregado por 15 min.

Também inclui tudo da 0.5.3.

| Artefato | Verificado |
| --- | --- |
| Instalador | `ALT-AI-Setup-0.5.4-x64.exe`, 219.548.652 bytes |
| SHA256 | `9d487e0fa09e8c1d033bad7931888eaf730093835b20827eb05212c5d7085faf`, igual ao digest do GitHub |
| Atualização | manifesto Ed25519 original; a cópia baixada da release foi validada contra o instalador local |
| Feed real | oferece a 0.5.4 para quem está na 0.5.3; não oferece nada para a própria 0.5.4 |
| Backend empacotado | `scripts/smoke_packaged.py` passou: versão 0.5.4 e perfil Notebook. O Controle Inteligente de Aplicativos foi desligado pelo dono. Metadados reais do Ollama conferidos pelo pacote. |
| ASAR | sem `.local`, chave privada, banco ou `.env` |

Testes: 256 Python passaram (1 ignorado) e 5 Node passaram. Authenticode continua ausente.
