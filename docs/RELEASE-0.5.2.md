# Entrega 0.5.2 — 30/10/2026

[Release publicada como prévia](https://github.com/caio306santana/ALT-/releases/tag/v0.5.2), tag `v0.5.2` no commit `2b7d3dd`. O conteúdo está descrito em [CHECKPOINT-0.5.2.md](CHECKPOINT-0.5.2.md):
- etapa 1 do [plano Drael](PLANO-ACAO-DRAEL.md): capacidades reais dos modelos;
- streaming e interrupção no gateway do celular.

| Artefato | Verificado |
| --- | --- |
| Instalador | `ALT-AI-Setup-0.5.2-x64.exe`, 219.533.280 bytes |
| SHA256 | `8dbb261109a10819c9e5c66c580d708426e4ce1966e4093bc7ec15454eca0ca6`, igual ao digest do asset no GitHub |
| Atualização | `ALT-AI-0.5.2-update.json` assinado com a chave Ed25519 original. O manifesto baixado da release foi validado contra o instalador local. |
| Feed real | Oferece a 0.5.2 para quem está na 0.5.1 e não oferece nada para a própria 0.5.2 |
| ASAR | 4.712 arquivos, sem `.local`, chave privada, banco, `.env` ou `.venv`. Só a chave pública de atualização. |

Relatório estruturado: [release-0.5.2-verification.json](release-0.5.2-verification.json).

## Verificação
- **Suíte:** 242 testes Python passaram, 1 ignorado; 5 testes Node passaram. Build TypeScript/Vite ok.
- **Pacote do commit limpo:** o build foi gerado a partir da árvore limpa do commit da tag. As edições das etapas 2 e 3, que começaram durante o build, ficaram guardadas fora do pacote. Prova disso: a rota nova `/tools/artifact` respondeu 404 no backend empacotado.
- **Backend empacotado:** `scripts/smoke_packaged.py` passou com banco temporário, cobrindo versão, autenticação, armazenamento, regras e estimativas Qwen/Hermes.
- **Ollama real pelo pacote**, sem inferência:

  | Modelo | Imagem | Ferramentas | Raciocínio | Contexto ativo |
  | --- | --- | --- | --- | --- |
  | Qwen 3.5 4B | sim | sim | sim | 4096 |
  | Huihui 4B | sim | sim | sim | 4096 |
  | Hermes 3B | não | sim | não | 4096 |

## Não validado
- **Abertura real do Bloco de Notas e da Calculadora:** não executada. O Bloco de Notas do dono estava aberto com texto não salvo e a Calculadora já rodava. O teste traria a janela do dono para a frente. Repetir com esses programas fechados.
- **Instalação sobre o app aberto:** o dono faz isso em Sobre → Sair, depois executa o instalador.
- **Fora deste notebook:** PC principal, microfone e iPhone.
- **Authenticode:** ausente.
