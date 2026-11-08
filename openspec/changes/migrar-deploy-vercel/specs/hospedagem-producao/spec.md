# Spec Delta

## Purpose

Define como o TáNaLista se comporta quando publicado em hospedagem serverless de produção: o que precisa estar configurado para iniciar, como o frontend é entregue e quais garantias valem para as notificações em tempo real.

## ADDED Requirements

### Requirement: Banco persistente obrigatório em produção
Em hospedagem de produção com disco efêmero (Vercel, identificada pela variável `VERCEL`, ou qualquer ambiente com `APP_REQUIRE_DATABASE`), o app MUST se recusar a iniciar quando `FIREBASE_CREDENTIALS` não estiver definida, em vez de usar o banco JSON local.

#### Scenario: Vercel sem chave do Firebase
- **GIVEN** a variável `VERCEL` está definida e `FIREBASE_CREDENTIALS` está vazia
- **WHEN** o app é carregado
- **THEN** a inicialização falha com erro que menciona `FIREBASE_CREDENTIALS`

#### Scenario: Vercel com chave do Firebase
- **GIVEN** a variável `VERCEL` está definida e `FIREBASE_CREDENTIALS` contém a chave
- **WHEN** o app é carregado
- **THEN** o armazenamento usado é o Firestore e `/api/health` responde `"storage": "firestore"`

#### Scenario: Desenvolvimento local
- **GIVEN** nem `VERCEL` nem `APP_REQUIRE_DATABASE` estão definidas e `FIREBASE_CREDENTIALS` está vazia
- **WHEN** o app é carregado
- **THEN** o app inicia usando o banco JSON local

### Requirement: Chave de assinatura obrigatória em produção
Em hospedagem de produção com disco efêmero, o app MUST se recusar a iniciar quando `APP_SECRET_KEY` não estiver definida, para que logins emitidos por uma instância sejam aceitos por todas as outras e sobrevivam a novos deploys.

#### Scenario: Vercel sem APP_SECRET_KEY
- **GIVEN** a variável `VERCEL` está definida, `FIREBASE_CREDENTIALS` está definida e `APP_SECRET_KEY` está vazia
- **WHEN** o app é carregado
- **THEN** a inicialização falha com erro que menciona `APP_SECRET_KEY`

#### Scenario: Desenvolvimento local sem APP_SECRET_KEY
- **GIVEN** nenhuma variável de produção está definida e `APP_SECRET_KEY` está vazia
- **WHEN** o app é carregado
- **THEN** o app gera e reaproveita uma chave local, como hoje

### Requirement: Chave do Firebase informada como conteúdo
O app SHALL aceitar em `FIREBASE_CREDENTIALS` tanto o conteúdo JSON da chave da conta de serviço quanto o caminho de um arquivo, para funcionar em hospedagens que só oferecem variáveis de ambiente.

#### Scenario: Conteúdo JSON na variável
- **WHEN** `FIREBASE_CREDENTIALS` começa com `{` e contém a chave da conta de serviço
- **THEN** o app conecta ao Firestore sem ler nenhum arquivo do disco

### Requirement: Cliente do banco criado uma vez por instância
O app MUST criar o cliente do Firestore uma única vez por processo, no carregamento do aplicativo, e reaproveitá-lo em todas as requisições atendidas por aquela instância.

#### Scenario: Várias requisições na mesma instância
- **GIVEN** o app foi carregado com `FIREBASE_CREDENTIALS` definida
- **WHEN** a mesma instância atende várias requisições seguidas
- **THEN** o cliente do Firestore foi criado exatamente uma vez

### Requirement: Frontend e API no mesmo endereço
O app SHALL servir o frontend (PWA) e a API pela mesma origem, com o service worker em `/sw.js` controlando o escopo `/`, e os cabeçalhos de segurança (incluindo a CSP estrita) MUST valer também para os arquivos do frontend.

#### Scenario: Página inicial em produção
- **WHEN** o navegador pede `/`
- **THEN** recebe `index.html` com o cabeçalho `Content-Security-Policy` do app

#### Scenario: Service worker
- **WHEN** o navegador pede `/sw.js`
- **THEN** recebe o service worker com status 200, da mesma origem da API, e o app pode registrá-lo com escopo `/`

### Requirement: Tempo real em melhor esforço
As notificações em tempo real (SSE em `/api/events`) SHALL ser entregues apenas a clientes conectados à mesma instância que processou a alteração; perda de notificação MUST NOT causar perda ou inconsistência de dados, que continuam vindo do banco.

#### Scenario: Remetente e destinatário em instâncias diferentes
- **GIVEN** dois participantes da mesma lista atendidos por instâncias diferentes
- **WHEN** um deles adiciona um item
- **THEN** o outro pode não receber o aviso em tempo real, mas vê o item ao recarregar a lista

#### Scenario: Conexão encerrada pelo limite de duração
- **GIVEN** uma conexão SSE aberta há mais que a duração máxima da função
- **WHEN** a hospedagem encerra a conexão
- **THEN** o navegador reconecta automaticamente e volta a receber avisos novos
