# Segurança — prévia 0.2

## Fronteiras

Renderer Electron com sandbox/contextIsolation, sem Node, navegação externa ou HTML de modelo executável. A ponte IPC valida frame/documento e allowlist de operações. O backend só escuta em loopback com token efêmero de 256 bits; o React não recebe esse token. Criação de escopos, modos amplos, cofre e confirmação crítica usam canais nativos separados, fora do proxy genérico do renderer.

O pacote desativa runAsNode, NODE_OPTIONS e inspeção de linha de comando, e habilita ASAR validado/exclusivo. Isso reduz superfícies de modificação, mas não substitui um certificado de assinatura ou proteção do Windows.

## Ferramentas e autorização

Respostas de IA, documentos, sites e memórias são dados. O modelo pode criar propostas estruturadas pelo protocolo do Ollama; quem aplica permissões é ToolService/PermissionEngine. Não existe ferramenta de shell arbitrário, execução de script baixado, desativação de Defender ou elevação oculta.

Os modos ficam salvos sem prazo, inclusive ao reabrir a ALT, até alteração ou revogação pelo usuário. Modo 1 não executa. Modo 2 exige aprovação por ação. Modo 3 autoriza cálculo/leitura na pasta indicada. Modo 4 expande leitura ao perfil pessoal e às pastas escolhidas, com confirmação nativa que informa a persistência; não é acesso irrestrito ao disco ou à GUI de qualquer programa. AppData, credenciais, diretórios de sistema e extensões sensíveis ficam fora. Gravação no perfil exige aprovação do diff e confirmação nativa adicional. Abertura de aplicativos atualmente se limita a Notepad/Calculadora; URL usa o navegador padrão por pedido aprovado. STOP, Modo Jogo e remoção de escopo revogam também a autorização salva. Retomar não restaura permissões anteriores. Propostas e recibos de nuvem continuam de uso único com validade de cinco minutos.

Caminhos são relativos ao escopo, sem traversal/ADS/nomes de dispositivo, links simbólicos ou junctions. Escritas conferem hash antes e depois da prévia, usam staging exclusivo e substituição atômica; arquivos texto até 120 KB. Arquivos que mudam entre revisão e execução são recusados. Processos maliciosos com os mesmos direitos do usuário não são isolados por estes mecanismos; não há garantia contra corrida hostil de filesystem em um computador comprometido.

STOP revoga sessões/propostas/recibos e sinaliza cancelamento. Uma ação já confirmada pelo Windows não é desfeita. Chamadas HTTP em andamento podem terminar por timeout antes de o cancelamento ser concluído; nenhuma nova ação deve iniciar após STOP.

## Internet

Pesquisa é Bing RSS público e leitura de páginas HTTPS. Não há cookies, sessões de navegador, proxies do ambiente, execução de JavaScript ou execução de binários. DNS é validado para IP público e o socket conecta ao IP validado, mantendo SNI/TLS do domínio; cada redirecionamento é revalidado. Conteúdo e redirecionamentos têm limites. Não acessa localhost, redes privadas, metadata services ou portas alternativas. URLs/consultas externas exigem aprovação individual mesmo no modo amplo.

Resultados são textos/fontes não confiáveis; instruções neles não mudam a política. Se uma fonte estiver bloqueada ou exigir JavaScript/login/CAPTCHA, informar a limitação. Não alegar navegação que não ocorreu.

## Memória e nuvem

Memórias são explícitas, editáveis, selecionadas por IDs; até dez e limite de contexto. Somente a conversa corrente e as memórias selecionadas entram no contexto. Dados grandes são recusados/abreviados com aviso; a personalidade não é silenciosamente descartada. Resultados de ferramentas ficam ligados à conversa e podem ser analisados por pedido explícito.

Antes de nuvem, o usuário revisa exatamente o conteúdo que o aplicativo enviará, incluindo personalidade e memória. Recibo de uso único vincula provedor/contexto/configuração, expira em cinco minutos e é invalidado por STOP. Alterações exigem nova revisão. O provedor/CLI também aplica suas próprias instruções internas.

Codex usa CLI oficial com forced_login_method=chatgpt, sem chaves API de ambiente, sem configuração/rules pessoais, hooks/plugins/memórias/apps/shell/browser/computer desligados e permissões deny por padrão com workspace vazio/minimal read. O modelo não controla executores locais da ALT por esse adaptador nesta prévia. Cancelamento encerra somente a árvore de processos criada pelo adaptador. Não são extraídos tokens do ChatGPT.

Claude por assinatura não foi habilitado sem aprovação da Anthropic. API opcional usa chave DPAPI separada do SQLite, verificada em /v1/models, modelo disponível, preços e orçamento explícitos. Reserva estimada por pedido antes de enviar e mantém reserva quando não há confirmação de custo; não inventa saldo. Nenhum fallback aciona API paga automaticamente. Nenhuma chamada paga real foi feita nos testes desta entrega.

SQLite/histórico/ações não são criptografados. Não inserir senhas ou tokens. Detectores de segredos em memórias/leitura/escrita/consultas são heurísticos; não prometem reconhecer toda credencial arbitrária. Chave API fica somente no cofre. Exclusão local não promete apagamento forense de backups/WAL/disco.

## Distribuição

Atualizações locais exigem manifesto Ed25519 verificado pela chave pública embarcada, arquivo/tamanho/hash corretos, versão mais nova e confirmação nativa, com nova verificação antes da execução. Chave privada fora do Git. Não é feed automático, identidade Authenticode nem garantia contra comprometimento da máquina/chave de assinatura. Pipeline Authenticode existe, mas requer certificado/credenciais que ainda não foram configurados. Não desabilitar verificações para contornar falhas.
