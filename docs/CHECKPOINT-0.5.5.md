# Checkpoint 0.5.5 — ALT mais autônoma ("como o JARVIS", continuando a ser a ALT)

30/10/2026. **Release:** [v0.5.5](https://github.com/caio306santana/ALT-/releases/tag/v0.5.5), prévia, tag no commit `5e74682`.

O dono pediu que a ALT ficasse mais parecida com os assistentes de referência (Mark-LVI e OpenJarvis): que faça sozinha, de ponta a ponta, sem parar no meio nem dizer que fez sem ter feito. Ela continua sendo a ALT; não foi criada outra IA.

Erros relatados pelo dono:
- diz que fez e não fez;
- não faz várias etapas;
- abre coisa errada.

Decisões do dono:
- só ele usa;
- PC principal como servidor sem custo;
- executáveis pedem aprovação.

## Implementado
- **`find_download`** (`research.find_download_candidates` + ferramenta):
  - pesquisa no site pedido, lê até 3 páginas, pontua os links de arquivo e baixa o vencedor claro, sem abrir nem executar;
  - várias opções parecidas → "ask";
  - executáveis viram um cartão de `download_file`. O `can_auto` recusa executável mesmo no Acesso total.
- **Ações diretas, sem modelo:**
  - "baixa X do site Y";
  - "abre o YouTube/Google e pesquisa X";
  - "pesquisa X no YouTube/Google".
- **Várias etapas:** com marcador de sequência, cada ação confirmada volta ao modelo com o pedido original e a ordem de chamar a próxima parte. Uma falha para a sequência e diz o que faltou.
- **Aviso de "fiz" falso:**
  - quando não houve nenhuma ação (`claimed_action`);
  - quando a ação ficou sem confirmação;
  - quando o tipo de ação dito não rodou (`unbacked_claim`).
- **PC principal como servidor:**
  - [PC-SERVIDOR.md](PC-SERVIDOR.md);
  - a PWA ganhou uma coluna centralizada no navegador do computador;
  - o painel passou a se chamar "Celular e outro computador".

## Evidência
- 270 testes Python e 5 Node passaram; o renderer sintético passou.
- **[Smoke real em simulação](jarvis-0.5.5-smoke.json)**, com Qwen 3.5 4B no Notebook: **7/8**, contra 5/8 antes das correções desta rodada.
  - A falha que resta, "abre o bloco de notas e digita", é uma limitação da simulação: o validador de janelas recusa uma leitura simulada. Precisa de teste real.
  - No primeiro resultado, o 4B escreveu "executei a pesquisa" depois de só abrir o YouTube. Isso motivou o `unbacked_claim` e o atalho direto.
- **Backend empacotado** testado (`smoke_packaged.py`).
- **Instalador:** 219.561.420 bytes, SHA256 `f4a184e3…7b51`, igual ao digest do GitHub.
- **Manifesto** público validado.
- **Feed:** a 0.5.4 recebe a oferta da 0.5.5, e a 0.5.5 não recebe nada.

## Pendente
- Teste real de "abre e digita" numa janela aberta pelo teste.
- Downloads reais em sites variados (a pontuação de links foi testada com páginas simuladas).
- No PC principal, feito pelo dono: Tailscale, pareamento e `ollama ps` com 100% GPU.
- Authenticode.

## 0.5.6 — abrir e digitar com segurança

[Release v0.5.6](https://github.com/caio306santana/ALT-/releases/tag/v0.5.6): prévia, tag no commit `895bbaf`. Instalador de 219.561.802 bytes, SHA256 `099abaeb…1146`, igual ao do GitHub.

**Conferido:** manifesto público, feed (a 0.5.5 recebe a oferta da 0.5.6) e smoke empacotado. 277 testes Python passaram.

**O que mudou:**
- **"Abre o bloco de notas e digita X"** é ação direta: abre um documento novo e digita.
- **`windows_type`** funciona sem leitura prévia: escolhe o campo de texto principal.
- **Correção de risco:** antes, o `SetValue` substituía o documento inteiro, o que podia apagar uma nota não salva. Agora um documento que já tem texto nunca é sobrescrito; a ALT só acrescenta no final quando o dono pede.

**Pendente:** o teste real com o Bloco de Notas. Não foi feito porque o Bloco de Notas do dono estava aberto com texto não salvo.
