# Velocidade na 0.5: diagnóstico e o que mudou

## A lentidão de 29-30/10 não era da ALT

Log do Ollama (`%LOCALAPPDATA%\Ollama\server-1.log`), com o mesmo Ollama 0.40.13, os mesmos modelos e a mesma linha de comando do `llama-server`, sempre 100% na GPU (33/33 camadas, ROCm, RX 7600):

| Quando | Origem | Leitura do prompt | Geração |
| --- | --- | --- | --- |
| 29/10 20:38 | smoke | ~1.550 tok/s | **57 tok/s** (4B), 15,5 (9B) |
| 29/10 22:37 e 22:45 | conversas do usuário | ~770 tok/s | **3,5–4,1 tok/s** |
| 30/10 00:2x | GPU sem nenhum outro processo | — | **4,5 tok/s** (4B), 7,5 (9B) |

O que foi descartado, com medição:
- **Placa disputada agora:** com a GPU livre, nenhum processo passava de 1%.
- **Processador:** 5% de uso total; o `llama-server` usava 29% de um núcleo durante a geração.
- **O Ollama iniciado pelo Codex:** o Ollama normal, aberto pelo Explorer, deu o mesmo número.
- **O modelo:** os digests e as datas são os mesmos de antes da execução rápida.
- **O reset do driver** (Win+Ctrl+Shift+B) e o recarregamento do modelo do zero também não resolveram.

Durante a geração, a GPU ficou em ~95% de uso. Ela trabalha no limite e rende cerca de 12 vezes menos.

**Causa encontrada:** em 29/10 às 21:08, o log de Aplicativos do Windows registra dezenas de `LiveKernelEvent` (141, 1b0, a1000001, a2000002, 193). São travamentos e recuperações do driver de vídeo, entre a execução rápida e a lenta. Recomendação ao usuário: reiniciar o PC. Medir de novo depois com `scripts/benchmark_latency.py --cases long` (a medição com a placa degradada está em `docs/latency-degraded-gpu.json`).

## O que a 0.5 faz a respeito

- **Velocidade de referência por modelo** (`backend/monitoring/gpu.py`, `SpeedReference`):
  - guarda a melhor velocidade vista neste PC e só decai 0,5% por resposta;
  - abaixo de 30% dessa referência, a resposta traz o aviso "a placa de vídeo está ocupada ou presa num estado lento".
- **Placa ocupada por outro programa** (`GpuWatch`):
  - contadores `GPU Engine` lidos por PDH, em menos de 1 ms por leitura;
  - um programa que não é da ALT nem do Ollama acima de 40% em 3 leituras deixa a resposta curta (256 tokens) e mostra o aviso;
  - com "Placa ocupada: usar o processador" ligado, responde pela CPU.
- **Prompt reaproveitável:**
  - o sistema fica igual entre turnos;
  - escopos, programas, janelas, orientação, memórias lembradas e capacidades vão para o fim da mensagem do usuário (`[CONTEXTO DESTE TURNO]`).
- **Ferramentas fixas** (`tool_routing='stable'`, padrão):
  - 14 ferramentas principais em todo turno, mais as roteadas fora da lista;
  - as de janela só entram no Acesso total ou com janela autorizada;
  - o turno indica as "ferramentas mais prováveis".
  - Smoke real no 4B: **10/10 em ambos os modos** (`docs/full-access-smoke.json`, `docs/full-access-smoke-stable.json`).
  - `scripts/bench_prompt_cache.py`: com as fixas, a leitura de 1.281 a 1.321 tokens caiu para 0,44–0,66 s, contra 1,43–1,49 s para 902–910 tokens no modo filtrado. É o cache sendo reaproveitado. O Ollama informa o total de tokens do prompt mesmo quando reaproveita o cache.
- **Modelo carregado:**
  - pré-carga ao abrir o app e ao trocar de modelo, com o mesmo `num_ctx`;
  - `keep_alive` de 30 min no desktop e 5 min no notebook.
- **Recarregamentos evitados:**
  - Game Mode passado a todos os chamadores (`num_ctx` igual);
  - embeddings com `num_gpu: 0`;
  - o resumo de projeto espera 60 s sem geração ativa.
- **Respostas:** no desktop, até 1024 tokens (eram 4096).
- **Interface:** o texto é atualizado em lotes de 50 ms, em vez de redesenhar o markdown a cada token.
- **Não alterado:** `OLLAMA_FLASH_ATTENTION`. O `llama-server` já recebe `--flash-attn auto`.

A meta (primeira palavra em menos de 1,5 s no 4B e menos de 3 s no 9B) só pode ser confirmada depois da reinicialização. O primeiro texto de uma resposta simples com o modelo quente já ficou entre 0,45 e 0,9 s.
