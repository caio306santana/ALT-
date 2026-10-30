# Tokenizers Qwen 3.5 e Hermes 3

`qwen3.5.json` é o arquivo de tokenização publicado por Qwen para Qwen3.5-4B. Não contém os pesos do modelo. A revisão, URL, tamanho e SHA256 constam em `provenance.json`; a licença Apache 2.0 acompanha o arquivo em `LICENSE-Qwen.txt`.

Uso local, sem consulta ao Hugging Face em tempo de execução. A ALT valida o SHA256 antes de carregar o tokenizer. `.gitattributes` fixa LF para preservar o hash em clones Windows. O instalador coloca estes arquivos em `resources/backend/tokenizers`, fora do ASAR.

A contagem BPE é usada para os modelos Qwen 3.5 e a variante Huihui Qwen 3.5; são reservadas margens separadas para o formato da conversa/ferramentas e para a resposta. Outros modelos usam a estimativa conservadora anterior. O relatório sintético `docs/chat-context-smoke.json` compara a estimativa com a contagem real informada pelo Ollama.

`hermes3-3b.json` e `hermes3-8b.json` vêm dos repositórios oficiais NousResearch/Hermes-3-Llama-3.2-3B e NousResearch/Hermes-3-Llama-3.1-8B. Os arquivos `hermes3-*-provenance.json` fixam revisão, URL, tamanho e SHA256, conferidos antes de carregar. As variantes têm arquivos diferentes, portanto não reutilizamos o tokenizer Qwen nem presumimos igualdade entre elas. `hermes3:latest` corresponde ao 8B na biblioteca Ollama consultada em 30/10/2026. Tags/quantizações personalizadas continuam na estimativa conservadora.

**Built with Meta Llama 3.** A licença publicada para Hermes 3 na biblioteca Ollama acompanha estes metadados em `LICENSE-Hermes3-Llama3.txt`, com atribuição em `NOTICE-Hermes3.txt`. Fonte da licença: blob `sha256:475211637354ce4c14b9c3dacccbefbaba735fe1b0db97d6c4fd11cd1356819f` do registry. Não redistribuímos pesos Hermes: o dono decide se/quando baixá-los pelo Ollama. Suporte à integração não equivale a uma avaliação de qualidade/latência do modelo no PC de destino.
