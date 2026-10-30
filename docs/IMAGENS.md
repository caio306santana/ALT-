# Gerar imagens com a ALT (0.5.7)

Em **Configurações → Imagens**, escolha como gerar. Depois, peça no chat: "gera uma imagem de …".

| Opção | Onde roda | Custo | Velocidade |
| --- | --- | --- | --- |
| 1. Neste PC, placa de vídeo | ComfyUI local, só em 127.0.0.1:8189 | grátis | segundos (placa AMD, NVIDIA ou Intel Arc) |
| 2. Neste PC, processador | o mesmo ComfyUI, com `--cpu` | grátis | minutos por imagem |
| 3. API paga da OpenAI | servidores da OpenAI | cobrado por imagem | rápido |

## Instalação local
**Instalar gerador local** pede confirmação e depois:
1. Detecta a placa pelo Windows. AMD, NVIDIA ou Intel Arc usam a placa; vídeo integrado usa o processador.
2. Baixa o pacote portátil oficial do ComfyUI da release mais recente no GitHub (`comfyanonymous/ComfyUI`). Confere o SHA256 publicado pelo GitHub e extrai com o `tar` do Windows em `<dados da ALT>\images\comfyui`.
3. Baixa o **SD-Turbo** (`stabilityai/sd-turbo`, 5,2 GB) e confere o SHA256 `3f067a1b…6549`. É de uso pessoal, pela licença da Stability AI.
4. Ocupa cerca de 18 GB. O gerador liga sozinho no primeiro pedido e para quando a ALT fecha. A ALT só encerra o processo que ela mesma iniciou.

**AMD (RX 7600):** a AMD recomenda o driver com suporte ROCm 7.1.1 (preview) para o ComfyUI. A instalação do driver é feita pelo dono.

## API paga
- A chave (`sk-…`) fica no cofre DPAPI do Windows e é salva depois de uma confirmação nativa.
- Modelo padrão: `gpt-image-2`, ajustável. Confira o preço oficial em platform.openai.com/pricing.
- Fora do Acesso total, cada imagem paga pede aprovação.

## Estado
- **Testado com simulações:** detecção da placa, download com hash, extração, fluxo do ComfyUI, API e ferramenta no chat. A detecção foi conferida no pacote real: Iris Xe → processador.
- **Não testado de verdade:** a instalação completa (~7 GB), a geração na RX 7600 e uma chamada real à API.
