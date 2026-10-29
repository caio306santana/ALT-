# Checkpoint 0.2 — 29/10/2026

Estado atual e continuidade: [HANDOFF.md](HANDOFF.md). Escopo: personalização, memória explícita, Codex oficial/Anthropic API opcional, ferramentas com permissões, pesquisa pública, Game Mode e distribuição verificável. As fases maiores continuam parciais no [ROADMAP.md](ROADMAP.md).

Último pedido: remover limite de minutos. Modos 2/3/4 persistem no SQLite até alterar/revogar, inclusive após reiniciar. STOP/Modo Jogo revogam o estado salvo. Propostas/recibos de nuvem mantêm cinco minutos e uso único.

59 testes Python passaram, um ignorado por privilégio de symlink; um teste Node de assinatura passou; TypeScript/Vite compilou. Testes reais confirmaram Codex sintético, personalidade Qwen, proposta estruturada sem execução implícita e pesquisa/leitura públicas com fontes.

Prints recebidos cobrem ferramentas, modelos, histórico, personalidade, memória e sistema. Controle visual interrompido por Esc; não afirmar revisão interativa completa do pacote final.

Build/publicação final em andamento. Não publicar stub intermediário NSIS. scripts/build-windows.cjs preserva ambiente no gerador de uninstaller electron-builder 26.18, evitando spawn UNKNOWN. release:manifest recusa arquivo pequeno incompleto.

Sem certificado Authenticode, chave Anthropic real, execução paga ou teste Ryzen/RX 7600. Chave privada .local/update-private-key.pem fora do Git: manter backup privado. Nunca publicar bancos/cofre/chaves/logs.

Pausa solicitada pelo usuário antes do limite de uso. Compilação NSIS interrompida; v0.2 não publicada. Fontes e decisões salvos. Próxima rodada: seguir a seção final de HANDOFF.md para concluir pacote, smoke empacotado, manifesto/hash e release privada. Não tratar artefatos intermediários como entrega final.
