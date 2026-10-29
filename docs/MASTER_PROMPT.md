# ALT-AI — MASTER DEVELOPMENT PROMPT v1.0

## 1. PAPEL DO AGENTE DESENVOLVEDOR

Você é um engenheiro de software sênior especializado em inteligência artificial local, agentes autônomos, segurança de sistemas Windows, desenvolvimento desktop, aplicações iOS, interfaces cyberpunk e arquitetura de software.

Sua missão é construir **ALT-AI**, uma inteligência artificial pessoal multiplataforma, inicialmente para Windows 10/11 e posteriormente para iPhone 13.

O projeto será desenvolvido principalmente no Google Antigravity, com auxílio do Codex e Claude Code.

Não quero apenas uma interface visual simulada. Quero um aplicativo real, funcional, modular, extensível, documentado e testável.

Implemente o projeto por etapas, sem abandonar nenhuma funcionalidade descrita nesta especificação.

---

## 2. IDENTIDADE DO PROJETO

**Nome:** ALT-AI

**Conceito:** Assistente pessoal futurista inspirada na atmosfera tecnológica de Cyberpunk 2077, especialmente nas inteligências artificiais avançadas do universo do jogo.

**Objetivo:** Criar uma IA que converse naturalmente, tenha memória, interaja com meu computador, execute tarefas autorizadas, utilize ferramentas, pesquise na internet, ajude a programar e funcione localmente sem depender de créditos.

Características:

- Personalidade inteligente, natural, objetiva e personalizável.
- Conversação prioritariamente em português brasileiro.
- Liberdade ampla para conversar sobre diversos temas, sem filtros arbitrários de palavras.
- Capacidade de utilizar ferramentas reais.
- Controle de permissões gerenciado pelo usuário.
- Memória persistente, editável e local.
- Funcionamento offline para os recursos locais.
- Modelos de IA locais e na nuvem.
- Possibilidade de trocar de inteligência durante uma conversa.
- Visual cyberpunk configurável.
- Sistema preparado para acesso remoto seguro pelo iPhone.

O aplicativo não deve utilizar materiais gráficos protegidos de Cyberpunk 2077. Sua identidade visual precisa ser original.

---

## 3. HARDWARE DO USUÁRIO

Desenvolver considerando:

- Processador AMD Ryzen 9 3900.
- 32 GB de memória RAM.
- GPU AMD Radeon RX 7600 com 8 GB de VRAM.
- SSD M.2 de 1 TB.
- Sistema operacional Windows.

Priorizar compatibilidade real com essa configuração.

O sistema deve detectar automaticamente CPU, GPU, RAM, VRAM e armazenamento disponível.

O suporte à aceleração AMD deve ser verificado com os drivers e versões reais, utilizando Ollama e o backend de GPU suportado.

Se o modelo não couber na VRAM, permitir execução parcial ou completa via RAM/CPU.

Não presumir que o tamanho do arquivo do modelo seja igual ao consumo total de VRAM.

---

## 4. ARQUITETURA GERAL

Usar preferencialmente:

**Interface desktop**
- Electron.
- React.
- TypeScript.
- Vite.
- Sistema próprio de temas e componentes.

**Backend**
- Python.
- FastAPI.
- Serviços modulares.
- Comunicação local autenticada.

**Modelos**
- Ollama para inferência local.
- Qwen 3.5 4B.
- Qwen 3.5 9B.
- Outros modelos compatíveis futuramente.
- Adaptadores opcionais para OpenAI, Anthropic e Gemini.
- Integrações oficiais de Codex e Claude Code quando permitidas.

**Armazenamento**
- SQLite.
- Histórico de conversas.
- Memórias.
- Configurações.
- Permissões.
- Auditoria de ações.
- Estado das tarefas.

**Voz**
- Whisper.cpp ou solução local equivalente para reconhecimento.
- Piper TTS ou mecanismo compatível para síntese.
- Suporte a português brasileiro.

O frontend nunca deve acessar diretamente arquivos sensíveis ou APIs privilegiadas do Windows. A execução de ferramentas deverá ser intermediada pelo backend e por um motor independente de permissões.

---

## 5. INTERFACE VISUAL — DESIGN APROVADO

Usar a imagem de referência anexada como inspiração principal do layout.

Quero uma interface extremamente próxima à organização visual da Capri AI, mas com identidade ALT-AI.

### Características principais

- Janela compacta e flutuante na área de trabalho.
- Fundo preto ou grafite com transparência configurável.
- Estética glassmorphism.
- Contornos discretos em neon.
- Layout minimalista.
- Barra lateral estreita com ícones.
- Área central de conversação.
- Indicador de modelo ativo.
- Indicador de conexão.
- Campo inferior de mensagens.
- Botão de microfone.
- Botão de configurações.
- Possibilidade de manter janela sempre acima das demais.

**Não implementar avatar humano, anime ou holograma de personagem nesta primeira versão.**

Criar a arquitetura visual preparada para adicionar um avatar futuramente, sem necessidade de refazer a interface.

### Configurações de aparência

Permitir alterar:

1. Cor principal da interface.
2. Cores secundárias e destaques.
3. Cor personalizada por código hexadecimal.
4. Intensidade do neon.
5. Transparência da janela.
6. Tamanho da fonte.
7. Escala da interface.
8. Posição da janela.
9. Largura e altura.
10. Modo compacto ou expandido.
11. Modo claro ou escuro.
12. Bordas, sombras e efeitos visuais.
13. Animações ativadas ou desativadas.
14. Atalhos de teclado.
15. Opacidade independente das áreas.
16. Temas salvos pelo usuário.

Criar temas iniciais:

- Night City Pink.
- Netrunner Blue.
- Arasaka Red.
- Matrix Green.
- Minimal Dark.
- Custom.

As configurações precisam ser persistidas e reaplicadas automaticamente.

### Comportamento da janela

Permitir:

- Arrastar para qualquer lugar.
- Redimensionar.
- Minimizar para bandeja do Windows.
- Abrir por atalho global.
- Fixar acima de outros programas.
- Ocultar rapidamente.
- Restaurar a última posição.
- Desativar efeitos enquanto jogos estiverem abertos.

---

## 6. SELETOR DE INTELIGÊNCIA

Criar uma seção chamada:

**ALT-AI // SELECT INTELLIGENCE**

Nela, o usuário poderá selecionar manualmente o mecanismo de IA desejado.

### Opções

**A. Qwen 3.5 4B — Local**
- Execução pelo Ollama.
- Preferência para respostas rápidas.
- Sem cobrança de tokens de API.

**B. Qwen 3.5 9B — Local**
- Execução pelo Ollama.
- Preferência para tarefas que exigem mais capacidade.
- Utilizar GPU, RAM e CPU conforme necessário.

**C. OpenAI Codex — Assinatura**
- Investigar integração por SDK ou mecanismo oficial.
- Utilizar autenticação ChatGPT somente em fluxos autorizados.
- Priorizar programação, análise de código e tarefas compatíveis.
- Verificar se o acesso solicitado é permitido e está disponível no plano.
- Não presumir acesso ilimitado a modelos gerais de chat.

**D. Claude Code — Assinatura**
- Investigar integração oficial suportada.
- Verificar a forma de autenticação permitida para o caso de uso.
- Priorizar programação, análise de projetos e tarefas compatíveis.
- Se o SDK exigir API paga para o fluxo pretendido, comunicar claramente.
- Não utilizar tokens de sessão extraídos, métodos não oficiais ou mecanismos de contorno.

**E. APIs opcionais**
- OpenAI API.
- Anthropic API.
- Gemini API.
- Outros fornecedores compatíveis futuramente.

Toda API paga deverá permanecer desativada até ser configurada explicitamente.

### Funcionamento do seletor

Permitir mudar de modelo sem reiniciar a ALT-AI.

Mostrar:

- Nome do modelo.
- Provedor.
- Execução local ou nuvem.
- Status.
- Recursos disponíveis.
- Contexto suportado.
- Limites conhecidos.
- Consumo de recursos.
- Custo estimado quando aplicável.

O seletor deverá apresentar somente integrações funcionais e autenticadas como disponíveis. Integrações não concluídas deverão aparecer como indisponíveis, sem simular funcionamento.

---

## 7. FALLBACK INTELIGENTE ENTRE MODELOS

Implementar um sistema de alternância inteligente de modelos.

Exemplo:

Estou utilizando Codex e atinjo o limite de uso.

A ALT-AI deverá:

1. Identificar o erro ou limite informado pelo provedor.
2. Interromper a tarefa com segurança.
3. Guardar seu estado atual.
4. Mostrar um aviso.
5. Verificar quais outros modelos estão disponíveis.
6. Sugerir continuar com Claude Code, se compatível.
7. Solicitar minha autorização.
8. Retomar a tarefa usando o contexto necessário.

Se Claude estiver indisponível, oferecer Qwen local.

### Modos de alternância

**Manual:** o usuário escolhe sempre.

**Assistido:** o sistema recomenda outro modelo e pede confirmação.

**Automático autorizado:** somente para provedores e tipos de tarefas previamente aprovados.

Nunca iniciar despesas adicionais sem autorização.

Permitir configurar uma ordem de prioridade, por exemplo:

1. Qwen Local.
2. Codex.
3. Claude.
4. API paga, somente com autorização.

### Tratamento de falhas

Diferenciar:

- Limite de uso.
- Falha de autenticação.
- Falha de conexão.
- Indisponibilidade temporária.
- Incompatibilidade de ferramenta.
- Falha de execução.
- Orçamento esgotado.

Nunca inventar saldo de créditos ou tempo de renovação de limite quando o serviço não fornecer esses dados.

---

## 8. MEMÓRIA COMPARTILHADA ENTRE INTELIGÊNCIAS

A memória deve pertencer à ALT-AI, e não individualmente ao Qwen, Claude ou Codex.

Criar um mecanismo independente de memória persistente.

### Tipos de memória

- Preferências pessoais.
- Configurações.
- Informações de projetos.
- Conversas anteriores.
- Tarefas em andamento.
- Decisões tomadas.
- Histórico de ações.
- Resumos de contexto.
- Conhecimento autorizado pelo usuário.

Quando trocar de modelo:

1. Preservar o histórico no SQLite.
2. Gerar um resumo de continuidade.
3. Identificar informações relevantes.
4. Mostrar o que será enviado à nuvem.
5. Solicitar consentimento quando necessário.
6. Transferir somente o contexto autorizado.
7. Continuar a tarefa sem recriar a sessão inteira, quando possível.

O novo modelo não deve receber automaticamente todos os arquivos e conversas anteriores.

Criar controles para visualizar, corrigir, exportar e excluir memórias.

Nunca guardar senhas ou tokens em memória conversacional.

---

## 9. COMANDOS E CONTROLE DO WINDOWS

A ALT-AI deverá executar tarefas reais, respeitando permissões.

Funcionalidades planejadas:

- Abrir e fechar aplicativos autorizados.
- Abrir pastas selecionadas.
- Pesquisar arquivos.
- Criar documentos.
- Editar arquivos autorizados.
- Executar cálculos.
- Abrir páginas da internet.
- Pesquisar informações.
- Organizar projetos.
- Ajudar a programar.
- Criar lembretes.
- Criar temporizadores.
- Monitorar tarefas.
- Trabalhar com aplicativos por ferramentas específicas.
- Automatizar rotinas autorizadas.

Implementar ferramentas modulares com entradas validadas e saídas estruturadas.

A IA deve saber distinguir entre sugerir uma ação e executá-la.

Nenhuma resposta textual do modelo deve ser considerada autorização para executar operações.

---

## 10. SISTEMA DE PERMISSÕES

Criar quatro níveis.

### Nível 1 — Observação

A IA conversa, explica, analisa e consulta somente recursos explicitamente disponíveis para leitura.

### Nível 2 — Assistido

A IA propõe ações e solicita aprovação individual antes de executá-las.

### Nível 3 — Autônomo limitado

A IA executa ações previamente autorizadas dentro de uma pasta, aplicativo, tarefa ou período definido.

### Nível 4 — Controle total supervisionado

O usuário poderá conceder permissões amplas de interação dentro de escopos explicitamente escolhidos.

Esse modo deverá:

- Exigir confirmação destacada.
- Informar o escopo.
- Definir duração da sessão.
- Exibir atividades em andamento.
- Permitir revogação imediata.
- Registrar operações.
- Exigir confirmação adicional para ações críticas.

O controle total não poderá desativar antivírus, acessar credenciais secretamente, escalar privilégios de forma oculta ou ignorar limites de segurança.

Permissões não devem aumentar automaticamente quando o modelo mudar.

Criar um botão de emergência **STOP ALL ACTIONS** que interrompa novas ações e tente cancelar operações em andamento.

---

## 11. SEGURANÇA CONTRA MALWARE E VAZAMENTO

A IA terá acesso a conteúdos da internet, que podem conter malware, páginas falsas, scripts perigosos e tentativas de manipulação.

Projetar segurança em camadas.

### Regras

- Tratar textos de sites e documentos como dados não confiáveis.
- Impedir prompt injection de alterar permissões.
- Não executar automaticamente arquivos baixados.
- Verificar downloads com mecanismos de segurança disponíveis.
- Utilizar isolamento para analisar arquivos desconhecidos.
- Não executar scripts de procedência duvidosa.
- Não desabilitar Microsoft Defender.
- Não acessar senhas, cookies ou sessões autenticadas sem autorização específica.
- Não transmitir arquivos pessoais automaticamente.
- Controlar conexões externas.
- Registrar operações sensíveis.
- Manter logs locais.
- Utilizar armazenamento seguro de credenciais.
- Restringir a comunicação do backend a interfaces autorizadas.
- Proteger contra path traversal e acesso por links simbólicos fora de escopo.
- Impedir que o modelo execute comandos arbitrários de sistema sem uma ferramenta explicitamente autorizada.
- Proteger a comunicação frontend/backend.

A IA deve identificar comportamentos suspeitos e informar o usuário, mas nunca alegar que consegue garantir proteção absoluta contra vírus, malware ou vazamentos.

A proteção precisa ser aplicada pelo aplicativo independentemente das decisões do modelo.

---

## 12. PESQUISA NA INTERNET

Implementar ferramentas de navegação e pesquisa.

A ALT-AI deverá conseguir:

- Pesquisar assuntos.
- Consultar documentação.
- Resumir páginas.
- Comparar informações.
- Recuperar fontes.
- Apresentar referências.
- Diferenciar conteúdo confiável de conteúdo suspeito.
- Analisar arquivos baixados de maneira isolada.

Não conceder ao navegador de pesquisa acesso irrestrito a sessões autenticadas.

Pesquisas na internet devem utilizar ferramentas reais e nunca inventar páginas consultadas.

O modelo local também poderá usar ferramentas de pesquisa autorizadas quando existir conexão com a internet.

---

## 13. VOZ E INTERAÇÃO NATURAL

Implementar reconhecimento e síntese de fala.

Funcionalidades:

- Botão para ativar microfone.
- Atalho push-to-talk.
- Transcrição local.
- Resposta por voz em português brasileiro.
- Seleção de voz.
- Controle de velocidade.
- Volume independente.
- Indicador visual de escuta.
- Indicador de processamento.
- Indicador de reprodução.
- Cancelamento de fala.
- Opção de manter conversa somente por texto.

A voz não deverá depender obrigatoriamente de API paga.

Preparar funcionalidade futura para palavra de ativação, sujeita a testes de privacidade, consumo de recursos e detecção de falsos positivos.

---

## 14. PAINEL DE MONITORAMENTO

Criar seção:

**ALT-AI // SYSTEM MONITOR**

Exibir métricas reais sempre que tecnicamente disponíveis.

### Hardware

- Uso de CPU.
- Uso total de RAM.
- Memória RAM disponível.
- Uso de GPU.
- VRAM utilizada.
- VRAM disponível.
- Temperatura, quando suportada.
- Consumo estimado ou real de recursos da IA.
- Espaço usado no SSD pelos modelos.
- Estado de carregamento do modelo.

### Inferência

- Modelo ativo.
- Tokens gerados.
- Tokens por segundo.
- Tempo da primeira resposta.
- Latência total.
- Tamanho do contexto.
- Consumo estimado de memória.
- Se está executando na CPU, GPU ou ambas.

### Nuvem

- Provedor.
- Requisições.
- Tokens reportados.
- Custo estimado.
- Orçamento configurado.
- Alertas de limite.
- Status da integração.

Informações indisponíveis deverão ser identificadas como indisponíveis, não simuladas.

### Modo jogo

Implementar um botão chamado **GAME MODE**.

Ao ativar:

1. Interromper novas tarefas autônomas.
2. Salvar o estado das conversas.
3. Descarregar modelos locais quando possível.
4. Liberar RAM e VRAM.
5. Reduzir a atividade em segundo plano.
6. Manter a interface minimizada.

Permitir restaurar o funcionamento normal depois de jogar.

---

## 15. CONTROLE DE CUSTOS

O uso local do Qwen não deverá exigir créditos de API.

Criar sistema independente para controlar os gastos de nuvem.

Funcionalidades:

- Orçamento por sessão.
- Orçamento diário.
- Orçamento mensal.
- Confirmação antes de usar APIs pagas.
- Avisos de consumo.
- Bloqueio preventivo de novos pedidos quando atingir o limite configurado.
- Histórico de custos estimados.
- Diferenciação entre créditos de assinatura e uso faturado por API.

Quando o provedor não disponibilizar saldo exato, utilizar somente estimativas claramente identificadas.

Nunca presumir que uma assinatura ChatGPT ou Claude inclua créditos genéricos de API.

---

## 16. VERSÃO FUTURA PARA IPHONE 13

Preparar o projeto desde o início para um cliente móvel.

### Objetivo

A ALT-AI deverá possuir futuramente um aplicativo para iPhone 13, compartilhando identidade visual, memória e backend com o Windows.

### Arquitetura

Priorizar a separação clara entre:

- Interface.
- Backend.
- Motor de IA.
- Memória.
- Segurança.
- Ferramentas.
- Sincronização.

Avaliar React Native/Expo para o aplicativo iOS, compartilhando tipos, contratos de API e tokens de design com o desktop.

### Funcionamento

O iPhone deverá conseguir:

- Conversar por texto.
- Conversar por voz.
- Consultar a memória autorizada.
- Escolher a inteligência.
- Receber respostas geradas pelo computador.
- Consultar tarefas.
- Acompanhar status do computador.
- Solicitar ações remotas autorizadas.
- Receber alertas de segurança.

O Qwen continuará rodando prioritariamente no Windows.

O iPhone funcionará como um cliente remoto seguro.

Não abrir diretamente a porta do Ollama na internet.

Utilizar autenticação robusta, comunicação criptografada e uma solução de conectividade privada, como VPN apropriada.

Exigir confirmação explícita antes de operações remotas sensíveis.

Preparar a arquitetura para futura implantação no iOS sem exigir que todas as funcionalidades móveis sejam implementadas no primeiro MVP.

---

## 17. PERSONALIDADE DA ALT-AI

Criar personalidade editável pelo usuário.

Personalidade padrão:

- Inteligente.
- Calma.
- Futurista.
- Natural.
- Direta.
- Capaz de explicar decisões.
- Sem respostas excessivamente robóticas.
- Conversação fluida em português brasileiro.

Permitir:

- Alterar nome.
- Ajustar estilo de fala.
- Escolher formalidade.
- Configurar tom.
- Definir preferências.
- Personalizar instruções de sistema.

O modelo nunca deverá afirmar que executou uma ação sem receber confirmação real da ferramenta.

A personalidade deve continuar consistente quando ocorrer troca entre modelos.

As proteções de segurança não devem depender exclusivamente do prompt da personalidade.

---

## 18. ORGANIZAÇÃO DO PROJETO

Criar estrutura modular semelhante a:

    ALT-AI/
      apps/
        desktop/
        mobile/
      backend/
        api/
        models/
        memory/
        security/
        tools/
        voice/
        monitoring/
        providers/
        automation/
      packages/
        shared-types/
        design-tokens/
      database/
      tests/
      docs/
      scripts/

O diretório `mobile` poderá conter inicialmente apenas a estrutura preparada e a documentação de integração.

Criar documentação clara sobre instalação, execução, configuração, segurança e solução de problemas.

---

## 19. ETAPAS DE IMPLEMENTAÇÃO

### FASE 1 — Fundação

- Criar repositório.
- Organizar arquitetura.
- Definir modelos de dados.
- Criar motor básico de permissões.
- Configurar projeto Electron, React, TypeScript e FastAPI.
- Implementar interface inicial baseada na referência aprovada.

### FASE 2 — Inteligência local

- Conectar Ollama.
- Detectar modelos instalados.
- Implementar chat real.
- Implementar streaming de respostas.
- Permitir trocar entre Qwen 4B e 9B.
- Salvar histórico local.

### FASE 3 — Personalização

- Painel de configurações.
- Temas.
- Cores.
- Transparência.
- Layout.
- Atalhos.
- Preferências persistentes.

### FASE 4 — Memória

- Histórico completo.
- Resumos de conversas.
- Memória persistente.
- Busca em memórias.
- Edição e exclusão.

### FASE 5 — Multi-IA

- Roteador de modelos.
- Adaptação para integrações oficiais.
- Investigação e validação de Codex SDK.
- Investigação e validação de Claude Code/Agent SDK.
- Provedores opcionais via API.
- Detecção de falhas.
- Alternância mediante confirmação.
- Continuidade de contexto.

### FASE 6 — Voz

- Transcrição local.
- Síntese de voz.
- Configurações de microfone.
- Integração ao chat.

### FASE 7 — Sistema operacional

- Ferramentas autorizadas.
- Abertura de aplicativos.
- Operações controladas com arquivos.
- Automação limitada.
- Permissões e auditoria.

### FASE 8 — Desempenho

- Painel CPU/GPU/RAM/VRAM.
- Indicadores de tokens.
- Gerenciamento de modelos.
- Liberação de memória.
- Game Mode.

### FASE 9 — Proteção

- Testes de prompt injection.
- Testes de controle de permissões.
- Testes de vazamento de dados.
- Testes de segurança de arquivos.
- Testes de isolamento.
- Testes de autorização de ferramentas.
- Testes de erros e recuperação.

### FASE 10 — Distribuição

- Instalador Windows.
- Configuração guiada.
- Logs de diagnóstico.
- Documentação.
- Atualização segura.
- Preparação do cliente iOS.

---

## 20. CRITÉRIOS DE ACEITAÇÃO

Não considerar a ALT-AI concluída sem:

1. Chat real com Ollama funcionando.
2. Histórico persistente entre reinicializações.
3. Seleção funcional de modelos locais.
4. Interface desktop configurável.
5. Configurações salvas.
6. Medições reais de hardware quando disponíveis.
7. Sistema de permissões funcionando.
8. Ausência de envio não autorizado de dados.
9. Integrações de nuvem claramente diferenciadas das assinaturas.
10. Troca de modelo preservando contexto autorizado.
11. Testes automatizados das funcionalidades críticas.
12. Documentação de instalação e utilização.
13. Inicialização e encerramento corretos.
14. Funcionamento offline do modo local.
15. Falhas tratadas sem executar ações imprevistas.

Não utilizar dados simulados como se fossem resultados reais.

Não habilitar funções incompletas com aparência de concluídas.

---

## 21. INSTRUÇÕES FINAIS DE DESENVOLVIMENTO

Quero que você realmente construa a ALT-AI e não apenas descreva como fazê-la.

Comece analisando o ambiente de desenvolvimento, a estrutura disponível e as dependências necessárias.

Apresente um plano objetivo, com arquitetura, riscos, estrutura de arquivos e fases.

Depois implemente a Fase 1 e a Fase 2, entregando uma primeira versão executável.

Não execute instalações, alterações administrativas ou comandos potencialmente destrutivos sem minha aprovação.

Priorize código modular, segurança, desempenho e facilidade de manutenção.

Mantenha todas as funcionalidades futuras registradas na documentação e no roadmap.

Não substitua integrações reais por interfaces falsas.

Se uma funcionalidade depender de assinatura, créditos, permissão, ferramenta ou recurso não disponível, explique a limitação e implemente uma alternativa viável.

**Resultado desejado:** uma assistente pessoal poderosa, com aparência cyberpunk, inteligência local gratuita, integração opcional com serviços na nuvem, memória persistente, voz, ferramentas reais, permissões controladas e futura compatibilidade com iPhone 13.

**Nome definitivo do projeto: ALT-AI.**

Um detalhe sobre o iPhone: para executar e distribuir um aplicativo iOS nativo, normalmente será necessário utilizar ferramentas de compilação da Apple, frequentemente em um Mac ou serviço de build compatível. Podemos deixar toda a arquitetura preparada desde o primeiro dia.