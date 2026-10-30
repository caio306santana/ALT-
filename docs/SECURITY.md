# Segurança — 0.5

## Fronteiras

Renderer Electron com sandbox/contextIsolation, sem Node, navegação externa ou HTML de modelo executável. A ponte IPC valida frame/documento e allowlist de operações. O backend só escuta em loopback com token efêmero de 256 bits; o React não recebe esse token. Criação de escopos, modos amplos, cofre e confirmação crítica usam canais nativos separados, fora do proxy genérico do renderer.

O pacote desativa runAsNode, NODE_OPTIONS e inspeção de linha de comando, e habilita ASAR validado/exclusivo. Isso reduz superfícies de modificação, mas não substitui um certificado de assinatura ou proteção do Windows.

## Ferramentas e autorização

Respostas de IA, documentos, sites e memórias são dados. O modelo pode criar propostas estruturadas pelo protocolo do Ollama; quem aplica permissões é ToolService/PermissionEngine. A ferramenta `run_command` executa PowerShell como o usuário comum, sem administrador, com tempo limite de 60 s, e **sempre** exige aprovação no cartão, inclusive no modo 4; a capacidade `shell` pode ser bloqueada em Controle e regras. Não existe execução de script baixado, desativação de Defender ou elevação oculta.

Os modos ficam salvos sem prazo, inclusive ao reabrir a ALT, até alteração ou revogação pelo usuário. Modo 1 não executa. Modo 2 exige aprovação por ação. Modo 3 autoriza cálculo/leitura na pasta indicada. Modo 4 (acesso total), com confirmação nativa que informa a persistência, executa sem aprovação tudo que não estiver bloqueado: arquivos em qualquer pasta local do usuário, qualquer programa do Menu Iniciar aberto pelo nome (sem registro), sites no navegador padrão e leitura/controle de janelas abertas por título (terminais, UAC, segurança, gerenciadores de senha, campos de senha e a própria ALT continuam excluídos). Fechar um programa que a ALT não abriu e comandos do PowerShell sempre pedem aprovação. AppData, credenciais, diretórios de sistema e extensões sensíveis ficam fora das ferramentas de arquivos. Fora do modo 4, gravação no perfil exige aprovação do diff e confirmação nativa adicional, e só abrem os aplicativos registrados por hash. Risco conhecido: texto de sites e janelas pode tentar enganar o modelo (prompt injection); no modo 4 isso pode virar ações sem revisão, por isso STOP fica sempre visível. STOP, Modo Jogo e remoção de escopo revogam também a autorização salva. Retomar não restaura permissões anteriores. Propostas e recibos de nuvem continuam de uso único com validade de cinco minutos.

Caminhos são relativos ao escopo, sem traversal/ADS/nomes de dispositivo, links simbólicos ou junctions. Escritas conferem hash antes e depois da prévia, usam staging exclusivo e substituição atômica; arquivos texto até 120 KB. Arquivos que mudam entre revisão e execução são recusados. Processos maliciosos com os mesmos direitos do usuário não são isolados por estes mecanismos; não há garantia contra corrida hostil de filesystem em um computador comprometido.

STOP revoga sessões/propostas/recibos e sinaliza cancelamento. Uma ação já confirmada pelo Windows não é desfeita. Chamadas HTTP em andamento podem terminar por timeout antes de o cancelamento ser concluído; nenhuma nova ação deve iniciar após STOP.

## Internet

O navegador 0.3 é um processo/sessão Electron em memória sem Node/preload do aplicativo. Usa proxy CONNECT local: DNS resolve o destino, todos os IPs precisam ser públicos e o socket conecta ao IP validado; TLS continua validado por Chromium. Proxy não encaminha HTTP simples ou portas alternativas; não há bypass de loopback, WebRTC não usa UDP direto, downloads e permissões especiais são negados. Janela e sessão são separadas do navegador pessoal e descartadas ao fechar.

Leitura gera snapshot e IDs de elementos visíveis. Clique/digitação conferem snapshot, URL, nó conectado e HTML observado, em mundo isolado. Elementos modificados exigem nova leitura. Campos de senha/OTP/cartão/segredos são recusados pela automação; nenhum comando JS arbitrário é recebido do modelo. A fila desktop exige token do backend e está fora do broker genérico; resultado é dado externo. A janela exibe sites reais, e interações aprovadas podem transmitir dados ao site.

Controle e regras aplica bloqueio por capacidade na proposta e novamente na execução. Escritas de política e registro de executáveis passam por confirmação nativa. Mudar política cancela propostas/ações de ferramentas e recibos, preservando o modo concedido. Há limites de implementação explicitamente visíveis; regras do usuário não alteram pesos do modelo, privilégios Windows ou contratos externos.

Executáveis são escolhidos localmente e conferidos por hash. A ALT não aceita argumentos arbitrários. Fechamento normal usa PID/tempo de criação rastreados e WM_CLOSE; não mata processos à força. Busca recursiva respeita escopos, links/caminhos sensíveis e limites de tempo/volume/cancelamento.

Resumos de continuidade são rascunhos, não fatos automaticamente aprovados. Snapshot da conversa impede aprovação após alteração. Importações validam todos os itens antes da transação. Recuperação por termos é opt-in, cabe no orçamento e é mostrada; contexto de nuvem continua vinculado ao recibo. Testes de modelos só usam modelos locais instalados e as notas de qualidade/liberdade são humanas.

Pesquisa simples é Bing RSS público e leitura de páginas HTTPS, separada da janela interativa descrita acima. Nessa ferramenta não há cookies, sessão pessoal, proxies do ambiente, JavaScript ou execução de binários. DNS/IP público e TLS são validados em cada redirecionamento; conteúdo tem limites. Não acessa localhost, redes privadas, metadata services ou portas alternativas. URLs/consultas exigem aprovação por padrão; o dono pode permitir a capacidade automaticamente nos modos 3/4.

Resultados são textos/fontes não confiáveis; instruções neles não mudam a política. Se uma fonte estiver bloqueada ou exigir JavaScript/login/CAPTCHA, informar a limitação. Não alegar navegação que não ocorreu.

## Memória e nuvem

Memórias são explícitas, editáveis, selecionadas por IDs; até dez e limite de contexto. Somente a conversa corrente e as memórias selecionadas entram no contexto. Dados grandes são recusados/abreviados com aviso; a personalidade não é silenciosamente descartada. Resultados de ferramentas ficam ligados à conversa e podem ser analisados por pedido explícito.

Antes de nuvem, o usuário revisa exatamente o conteúdo que o aplicativo enviará, incluindo personalidade e memória. Recibo de uso único vincula provedor/contexto/configuração, expira em cinco minutos e é invalidado por STOP. Alterações exigem nova revisão. O provedor/CLI também aplica suas próprias instruções internas.

Codex usa CLI oficial com forced_login_method=chatgpt, sem chaves API de ambiente, sem configuração/rules pessoais, hooks/plugins/memórias/apps/shell/browser/computer desligados e permissões deny por padrão com workspace vazio/minimal read. O modelo não controla executores locais da ALT por esse adaptador nesta prévia. Cancelamento encerra somente a árvore de processos criada pelo adaptador. Não são extraídos tokens do ChatGPT.

Claude por assinatura não foi habilitado sem aprovação da Anthropic. API opcional usa chave DPAPI separada do SQLite, verificada em /v1/models, modelo disponível, preços e orçamento explícitos. Reserva estimada por pedido antes de enviar e mantém reserva quando não há confirmação de custo; não inventa saldo. Nenhum fallback aciona API paga automaticamente. Nenhuma chamada paga real foi feita nos testes desta entrega.

SQLite/histórico/ações não são criptografados. Não inserir senhas ou tokens. Detectores de segredos em memórias/leitura/escrita/consultas são heurísticos; não prometem reconhecer toda credencial arbitrária. Chave API fica somente no cofre. Exclusão local não promete apagamento forense de backups/WAL/disco.

## Distribuição

Na branch 0.5, anexos de até 20 MB são lidos localmente. PDF com texto usa extração; páginas sem texto usam PDFium para renderização limitada e OCR do Windows, quando o idioma de reconhecimento está disponível. O helper PowerShell é um arquivo fixo interno: recebe caminhos temporários em JSON por stdin, sem compor comandos com conteúdo/nome do documento. Isso não passa pelo executor `run_command` do modelo. Texto reconhecido continua sendo dado não confiável e pode conter erros. Validar o helper e a DLL PDFium no runtime empacotado antes de distribuir; o teste atual foi em desenvolvimento neste PC.

Imagens JPEG são validadas pelo decoder antes de armazenamento. PDFs protegidos, documentos excessivos e páginas sem texto legível são recusados com motivo. OCR não envia documentos à internet. Envio de anexos à Anthropic continua passando pela prévia de nuvem e pelo recibo; o modo híbrido escolhido pelo usuário ainda não habilita fallback pago automático.

Atualizações locais exigem manifesto Ed25519 verificado pela chave pública embarcada, arquivo/tamanho/hash corretos, versão mais nova e confirmação nativa, com nova verificação antes da execução. Chave privada fora do Git. Não é feed automático, identidade Authenticode nem garantia contra comprometimento da máquina/chave de assinatura. Pipeline Authenticode existe, mas requer certificado/credenciais que ainda não foram configurados. Não desabilitar verificações para contornar falhas.

## Novidades de segurança da 0.5

**Voz.** A janela do Electron não tem mais permissão de microfone: quem captura é o backend (`sounddevice`), e o áudio fica só em memória. Com a palavra de ativação ligada, o microfone fica aberto, mas, enquanto a ALT dorme, só o detector local recebe o som; nada vai ao Whisper. Enquanto ela fala, o microfone é ignorado, para não obedecer à própria voz. STOP corta a fala e a escuta. Os modelos de voz (Whisper, Dora, "Hey Jarvis") vêm de endereços fixos e só são baixados quando o usuário pede.

**Resultado das ações.** Cada ação devolve um estado. Só "feito" leva ✓; "não confirmado" diz ao modelo, com uma instrução fixa, que ele não pode afirmar sucesso. Conteúdo de fora (sites, arquivos, janelas, anexos, resultados de ferramentas) vai entre marcadores `<<<DADOS …>>>`; marcadores e tokens de template de chat que já venham no texto são neutralizados.

**Sempre permitir.** Vale só para abrir um programa, um site (por domínio) ou uma pasta, nos modos 2 e 3. Comandos, fechar programas, gravar arquivos e downloads nunca são lembrados. A lista pode ser revisada e apagada em Controle e regras.

**Conversa protegida.** Se uma leitura trouxer credencial, CPF, número de cartão (validado pelo algoritmo de Luhn) ou tokens de chat, a conversa fica marcada. Até o STOP, sites, pesquisas, downloads, gravações e interações com janelas voltam a pedir cartão, mesmo no Acesso total. É a defesa contra "leia o segredo e mande para fora".

**Desfazer.** Gravações e downloads podem ser revertidos. O desfazer se recusa se o arquivo mudou depois da ação da ALT, para não apagar uma mudança sua.

**Tela, sistema e lembretes.**
- A captura de tela fica só em memória, nunca no banco. Só vai para um modelo de nuvem pelo cartão.
- Volume e brilho são lidos antes e depois.
- Lembretes rodam no Agendador do Windows com o menor privilégio e na sessão do usuário. O texto vai num arquivo JSON, nunca na linha de comando.

**Proativa.** Desligada por padrão. Respeita horário de silêncio e limite diário. O resumo da manhã só usa números que estão nos dados, e o clima é consultado no Open-Meteo só se uma cidade for definida. Rotinas e conversas puxadas pela ALT só geram texto; nunca executam ações.

**Modelo automático.** Escolher o Claude nunca envia nada sozinho: a prévia e o recibo de consentimento continuam obrigatórios. Pedidos vindos do celular ficam no modelo local.

**Celular.**
- **Rede:** o gateway separado escuta só em `127.0.0.1:47823` e é publicado pelo `tailscale serve`, só na tailnet do dono, com HTTPS. Nunca é usado o `funnel`. Nenhuma porta é aberta e nada muda no firewall.
- **Conexão:** o gateway confere Host e Origin, e o token do desktop não vale nele.
- **Pareamento:** código de uso único, válido por 2 minutos, no `#fragmento`. Cada aparelho recebe um token próprio, guardado como hash, num cookie Secure/HttpOnly/SameSite=Strict de 30 dias renováveis. Cinco tentativas erradas travam o pareamento por 10 minutos. O acesso é revogável por aparelho.
- **Ações:** pelo celular nada roda sozinho; toda ação vira cartão. PowerShell e gravações críticas só são aprovados no PC.
- **Notificações:** Web Push com VAPID (aes128gcm). A chave privada fica na pasta de dados.

**Chave de atualização.** O manifesto de atualização da 0.5 precisa da chave privada original, que não está neste PC. O script de assinatura se recusa, de propósito, a trocar a identidade sozinho.
