# Hermes 3 na ALT-AI

A partir da 0.5.1, **Inteligências** oferece dois downloads opcionais da biblioteca oficial Ollama:

| Opção | Tag Ollama | Download aproximado | Uso |
| --- | --- | --- | --- |
| Hermes 3 3B | `hermes3:3b` | 2 GB | Alternativa menor para texto e ferramentas |
| Hermes 3 8B | `hermes3:8b` | 4,7 GB | Mais parâmetros; exige mais RAM/VRAM |

Referências consultadas em 30/10/2026: [Hermes 3 3B](https://ollama.com/library/hermes3:3b), [Hermes 3 8B](https://ollama.com/library/hermes3:8b) e os repositórios [NousResearch 3B](https://huggingface.co/NousResearch/Hermes-3-Llama-3.2-3B) / [8B](https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B).

O dono escolheu **adicionar os dois e baixar depois**. Nenhum peso Hermes foi baixado nesta entrega. A integração foi validada com o contador oficial local e dublês do contrato Ollama; ainda falta avaliar respostas, ferramentas e velocidade do Hermes real no computador de destino. Tamanho em disco não equivale à memória necessária em execução.

## Como usar

1. Instale a versão nova e mantenha o Ollama aberto.
2. Vá a **Inteligências**, escolha a variante e clique em **Baixar**. Confira o pedido antes de confirmar o download.
3. Ao concluir, atualize a lista e selecione o Hermes no seletor do chat. A seleção manual mantém o modelo escolhido. Em **Automático**, o roteador pode escolher entre os modelos locais instalados por tamanho/complexidade e Claude quando disponível, sempre com prévia antes de envio à nuvem.

A personalidade, histórico, memórias e regras continuam sendo da ALT; Hermes é o motor de terceiros. Não há treino de pesos exclusivos nem garantia de ausência de recusas. Chamadas de ferramentas passam pelas mesmas autorizações e verificações. Hermes 3 aqui é texto/ferramentas, não visão: para imagens, escolha um modelo que exponha essa capacidade no Ollama.

Os tokenizers 3B e 8B têm origem, revisão e hash fixados em `assets/tokenizers`, com licença/atribuição. Não dependem de rede durante a conversa. A contagem conserva a reserva de resposta e o perfil Notebook de 4.096 tokens; não amplia RAM silenciosamente.

**Built with Meta Llama 3.** Licença e atribuição acompanham os metadados no instalador; ver [README dos tokenizers](../assets/tokenizers/README.md).
