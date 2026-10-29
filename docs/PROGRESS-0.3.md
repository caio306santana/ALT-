# ALT 0.3 — checkpoint de desenvolvimento

Pedido: implementar painel de controle/regras, comparar modelos locais, navegador interativo/ferramentas Windows e memória de continuidade. Usuário autorizou explicitamente download/comparação Huihui Qwen 3.5 4B nesta rodada. Download concluído (3.315.333.475 bytes; digest 9acbd90c2645120ea1e4a5fe7ec9c4fe000e547ccebc8a24f950315d582003e6).

Implementado:
- Política persistente com regras de conversa, recuperação manual/automática de memória e decisões bloquear/perguntar/permitir por capacidade. Escrita via confirmação nativa fora do broker genérico. Regras/modelo/Windows/serviços e prompt efetivo visíveis.
- Navegador Electron isolado em sessão temporária, HTTPS público via proxy CONNECT que valida DNS e fixa conexão no IP público; sem bypass de TLS/proxy loopback, downloads/permissões negados. Ler DOM, clicar, digitar com snapshot/IDs observados; rejeita elementos alterados e campos protegidos. Fila autenticada DesktopBridge consumida somente por Electron main.
- Apps .exe registrados por seletor nativo, hash conferido, sem argumentos arbitrários; fechamento normal de processos rastreados, sem encerramento forçado. Busca recursiva em pastas com limite/cancelamento e exclusão de caminhos sensíveis.
- Rascunho de continuidade gerado por modelo local e revisado antes de salvar; fingerprint rejeita conversa modificada. Importação JSON com validação atômica e deduplicação. Recuperação por termos, opt-in, ajustada ao contexto e visível; sem busca semântica.
- Laboratório local: prompts iguais, respostas/métricas persistidas e notas humanas. Modelos de nuvem não aceitos. Resultado completo em .local/model-comparison-0.3.json (somente prompts sintéticos).
- UI de Controle, Navegador, comparação em Inteligências e continuidade em Memória. Versão 0.3.0 no package/lock/health/rodapé.

Validação atual:
- 74 testes Python passaram; um symlink ignorado por privilégio Windows. Três testes Node passaram (URLs/IPs, DNS misto/privado, assinatura).
- Smoke real Electron oculto do próprio navegador passou: HTTPS docs.ollama.com via proxy, DOM leitura/clique/digitação em fixture sintética, snapshot antigo e senha recusados. Não é revisão visual da UI nem automação de conta do usuário.
- Build TS/Vite mais recente em sessão 68782, conferir término.
- Comparação real inicial completou 6 respostas em Notebook/CPU, mas ambas discussões chegaram ao limite 128 tokens. Qwen errou 17×19 (respondeu 642); Huihui respondeu 323. Não alegar vencedor geral ou ausência de recusas.
- Repetição somente da discussão com 256 tokens em sessão 50861; vai salvar .local/model-comparison-0.3-discussion.json.

Ainda falta antes da entrega:
1. Conferir repetição da discussão, gerar relatório versionado com prompts/respostas/limites/tempos e fontes dos modelos; não inventar notas humanas.
2. Teste real de resumo local com dados sintéticos, validar estado antes/depois de revisão.
3. Acabamentos finais, validação TS, testes apropriados às últimas alterações. Não repetir downloads ou chamadas de nuvem.
4. Atualizar README/SECURITY/ARCHITECTURE/ROADMAP/HANDOFF/RELEASE_NOTES e scripts smoke_packaged para 0.3. Recompilar frontend/backend, NSIS, smoke empacotado, Ed25519/SHA256 e publicar prévia privada 0.3.0.
5. Conferência visual da interface depende de Computer Use (pipe nativo esteve indisponível na rodada anterior). Não afirmar que foi concluída. Windows limpo e PC principal continuam pendentes.

Chave privada .local/update-private-key.pem permanece fora do Git. Não habilitar API paga nem alterar visibilidade do repositório. Todo o escopo 2/3/4/5 continua ativo até a entrega.
