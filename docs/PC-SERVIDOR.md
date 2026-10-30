# PC principal como servidor da ALT (sem custo)

Com isso, a ALT roda no **PC principal**, que tem placa de vídeo, e você conversa com ela pelo **notebook** e pelo **iPhone**, de qualquer lugar. Não há mensalidade: o Tailscale é gratuito para uso pessoal.

## Como funciona
- **No PC principal:** o modelo, a memória, as ferramentas e as ações. O PC precisa ficar ligado.
- **No notebook e no celular:** a ALT abre como uma página (PWA). A conexão passa por uma rede privada do Tailscale, só entre os seus aparelhos, criptografada. Nenhuma porta é aberta no roteador.
- **As ações acontecem no PC principal.** "Abre o Chrome", pedido pelo notebook, abre o Chrome **no PC principal**. Arquivos baixados ficam na pasta Downloads **do PC principal**.
- **Pelo aparelho remoto, nada roda sozinho:** toda ação vira um cartão para você aprovar. Comandos do PowerShell e gravações críticas só podem ser aprovados no próprio PC.

## Passo a passo no PC principal
1. **Reinicie o PC** se não reiniciou desde o problema do driver de vídeo de 29/10.
2. **Instale a versão mais nova da ALT** pela release no GitHub (ou pelo aviso de atualização do app) e abra-a uma vez.
3. **Confira se a placa está sendo usada:**
   1. abra o PowerShell;
   2. mande uma mensagem na ALT e, enquanto ela responde, rode `ollama ps`;
   3. a coluna **PROCESSOR** deve mostrar **100% GPU**.

   Se aparecer `CPU` ou uma divisão como `40%/60% CPU/GPU`, a placa não está sendo usada inteira. Me mande o que apareceu.
4. **Instale o Tailscale** (tailscale.com/download) e entre com a **mesma conta** usada no notebook e no iPhone.
5. **No painel do Tailscale** (login.tailscale.com) → **DNS**, ligue **MagicDNS** e **HTTPS Certificates**.
6. **Na ALT do PC principal:** **Controle e regras** → **Celular e outro computador** → **Ligar acesso pelo celular**. Ela mostra um endereço `https://<nome-do-pc>.<sua-rede>.ts.net`.

## Parear o notebook
1. No notebook, com o Tailscale ligado, abra esse endereço no navegador (Edge ou Chrome).
2. No PC principal, clique em **Parear um aparelho** (Controle e regras → Celular e outro computador): aparece um código que vale 2 minutos e uma vez só.
3. Digite o código no notebook. Pronto: o navegador fica pareado por 30 dias e se renova enquanto você usa.
4. Opcional: no Edge, Menu → **Aplicativos** → **Instalar este site como aplicativo**, para ter um ícone de app.

**No notebook, deixe a ALT local e o Ollama fechados** quando usar o PC principal. Assim os ~3 GB do modelo ficam livres na RAM do notebook, que hoje anda sem memória.

## Parear o iPhone
Siga o mesmo caminho em [IPHONE.md](IPHONE.md): QR code de pareamento → Safari → **Adicionar à Tela de Início**.

## Se algo não abrir
- **O endereço não carrega:** o Tailscale precisa estar ligado nos dois aparelhos, com a mesma conta.
- **"Origem não autorizada":** abra pelo endereço `https://…ts.net` mostrado na ALT, não pelo IP.
- **Para desligar:** Controle e regras → Celular e outro computador → Desligar acesso pelo celular. Os aparelhos pareados podem ser removidos ali.
