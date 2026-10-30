# ALT no iPhone, sem App Store

A ALT continua rodando no seu PC: o modelo, a voz e as ferramentas ficam lá. O iPhone vira um controle remoto. Ele aparece como um app na Tela de Início e conversa com o PC por uma rede privada, só entre os seus aparelhos.

## O que você precisa

- **Tailscale (grátis)** no PC e no iPhone, logado com a **mesma conta**: tailscale.com/download (no iPhone, pela App Store; é só o Tailscale).
- **No painel do Tailscale** (login.tailscale.com), em DNS, deixe ligados o **MagicDNS** e os **HTTPS Certificates**. Sem HTTPS o Safari bloqueia o microfone e as notificações.
- iOS 16.4 ou mais novo, para receber notificações.

## Ligar e parear

1. No PC, abra a ALT → **Controle e regras** → **Celular** → **Ligar acesso pelo celular**.
   - A ALT roda `tailscale serve` e publica um endereço como `https://seu-pc.tailXXXX.ts.net`.
   - Esse endereço só abre em aparelhos da sua conta Tailscale. Nunca é usado o `funnel`, que deixaria a ALT pública.
2. Clique em **Parear um iPhone**. Aparece um QR code que vale **2 minutos e uma vez só**.
3. No iPhone, com o Tailscale ligado, aponte a câmera para o QR code e abra o link. Se preferir, entre no endereço e digite o código.
4. No Safari: **Compartilhar → Adicionar à Tela de Início**. Agora a ALT abre como app.
5. Toque no 🔈 para ouvir as respostas na voz da Dora. Isso também pede permissão para as notificações (resumo da manhã, rotinas, avisos).

## O que dá para fazer pelo celular

- Conversar por texto ou voz: segure 🎤 para falar. A transcrição acontece no Whisper do PC.
- Mandar uma foto (📷) para a ALT olhar.
- Ver as ações que ela propõe e aprovar ou recusar cada uma.
- Receber o resumo da manhã, as rotinas e os avisos como notificação.

## Segurança

- **Nada roda sozinho a partir do celular**, nem no Acesso total. Toda ação vira um cartão para você aprovar.
- **Comandos do PowerShell e gravações críticas só podem ser aprovados no PC.**
- A ALT continua escutando só em `127.0.0.1`. Quem leva o tráfego até ela é o Tailscale, criptografado entre os seus aparelhos. Nenhuma porta é aberta no roteador e nada muda no firewall do Windows.
- **Pareamento:**
  - cada aparelho recebe um token próprio, guardado no PC só como hash;
  - no celular, ele fica num cookie que o JavaScript não lê;
  - o token vale 30 dias e se renova enquanto você usa;
  - 5 códigos errados travam o pareamento por 10 minutos.
- O código de pareamento vai depois do `#` do link, então nunca chega a nenhum servidor nem fica em log.
- Para cortar o acesso de um aparelho: **Controle e regras → Celular → Revogar**. Para desligar tudo: **Desligar acesso pelo celular**.
- Quando o modelo escolhido no PC é o Claude, as mensagens do celular são respondidas pelo modelo local. A prévia de envio à nuvem só existe no PC.

## Se algo não funcionar

| Problema | O que fazer |
| --- | --- |
| "Instale o Tailscale" | Instale nos dois aparelhos e entre com a mesma conta. |
| "O Tailscale recusou publicar a ALT" | Ligue os HTTPS Certificates no painel do Tailscale (DNS). |
| O link não abre no iPhone | Confira se o Tailscale está ligado no iPhone e se o PC está ligado e com a ALT aberta. |
| Microfone não funciona | Use o endereço `https://…ts.net`, não o IP: o Safari só libera o microfone com HTTPS. |
| Sem notificações | É preciso adicionar à Tela de Início e permitir as notificações. |
