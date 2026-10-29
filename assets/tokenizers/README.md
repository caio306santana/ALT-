# Tokenizer Qwen 3.5

`qwen3.5.json` é o arquivo de tokenização publicado por Qwen para Qwen3.5-4B. Não contém os pesos do modelo. A revisão, URL, tamanho e SHA256 constam em `provenance.json`; a licença Apache 2.0 acompanha o arquivo em `LICENSE-Qwen.txt`.

Uso local, sem consulta ao Hugging Face em tempo de execução. A ALT valida o SHA256 antes de carregar o tokenizer. `.gitattributes` fixa LF para preservar o hash em clones Windows. O instalador coloca estes arquivos em `resources/backend/tokenizers`, fora do ASAR.

A contagem BPE é usada para os modelos Qwen 3.5 e a variante Huihui Qwen 3.5; são reservadas margens separadas para o formato da conversa/ferramentas e para a resposta. Outros modelos usam a estimativa conservadora anterior. O relatório sintético `docs/chat-context-smoke.json` compara a estimativa com a contagem real informada pelo Ollama.
