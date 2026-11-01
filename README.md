# TáNaLista

Listas de compras compartilhadas, pensadas para o celular.

>Quem divide a casa conhece a confusão: um anota a lista no papel, outro manda itens pelo WhatsApp e, na hora de comprar, ninguém sabe o que já foi pego. O resultado é item esquecido, compra repetida e a pergunta de sempre: “quem vai passar no mercado?”. O TáNaLista resolve isso com uma lista de compras compartilhada, que funciona no celular: o café acabou, você adiciona à lista e quem participa dela é avisado na hora. Cada lista tem um dono, que decide quem pode entrar, e os itens aparecem separados por categoria (padaria, hortifrúti, limpeza...), com quantidade e marca. No mercado, mesmo sem sinal, você marca o que já pegou e anota os preços para ver quanto gastou, e tudo é atualizado para o grupo quando a internet volta.


## Funcionalidades

- **Conta:** cadastro e login com usuário e senha.
- **Listas (grupos):** cada lista tem um dono e participantes.
- **Convite por link:** compartilhe pelo WhatsApp, Instagram ou onde quiser
  (botão nativo "Compartilhar" do celular, atalho do WhatsApp e "Copiar link").
- **Aprovação de entrada:** quem abre o link, ou encontra a lista na busca,
  **pede para entrar**, e o dono **aceita ou recusa**.
- **Busca:** encontre listas marcadas como "Aparecer na busca" e peça para entrar.
  Listas privadas só podem ser acessadas pelo link.
- **Itens:** adicionar com quantidade e medida (un, kg, g, L, ml, pacote, caixa, dúzia),
  marca (opcional) e categoria (Hortifrúti, Açougue, Frios e laticínios, Padaria, Mantimentos,
  Bebidas, Congelados, Limpeza, Higiene, Outros). A lista aparece separada por categoria.
  Qualquer participante pode editar, remover, marcar como comprado e limpar os comprados.
  O app impede que um item pendente seja adicionado duas vezes.
- **No mercado (funciona sem internet):** marque o que pegou e anote o valor pago; o total
  é somado na hora. Os preços ficam só no aparelho. As marcações feitas sem internet
  aparecem na hora e são enviadas à lista compartilhada quando a conexão volta. A última
  versão das listas fica salva para abrir mesmo offline.
- **Avisos em tempo real:** quando alguém adiciona um item, os outros participantes
  recebem um aviso na tela (ou uma notificação do sistema, se o app estiver em segundo plano).
- **Gestão:** remover participantes, gerar um novo link (o antigo deixa de valer),
  editar, excluir ou sair da lista.

## Publicar na internet (acesso de qualquer lugar)

O app roda no **Render**, que é grátis e já vem com HTTPS e um endereço público. Os dados
ficam no **Firestore** (Firebase), no plano gratuito Spark: 1 GB e dezenas de milhares de
leituras/gravações por dia, o suficiente para uso familiar. Nenhum dos dois pede cartão.

1. **Banco (Firebase):**
   1. Em <https://console.firebase.google.com>, crie um projeto (o Google Analytics é opcional).
   2. Em **Build → Firestore Database**, clique em **Criar banco de dados**, escolha o local
      `southamerica-east1 (São Paulo)` e o **modo de produção**. Esse modo bloqueia o acesso
      direto pelo navegador; só o servidor (com a chave abaixo) lê e grava.
   3. Em **⚙ Configurações do projeto → Contas de serviço**, clique em
      **Gerar nova chave privada**. Isso baixa um arquivo `.json`. **Guarde com cuidado e
      nunca envie para o GitHub**: quem tem essa chave tem acesso total ao banco.
2. **Servidor (Render):** crie uma conta em <https://render.com> entrando com o GitHub. Clique
   em **New → Blueprint** e escolha este repositório. O Render lê o arquivo `render.yaml`.
3. No serviço criado, abra **Environment → Secret Files → Add Secret File**, use o nome
   `firebase.json` e cole o conteúdo do arquivo baixado no passo 1.3. Salve (o Render
   reinicia o app). A variável `FIREBASE_CREDENTIALS` já aponta para esse arquivo.
   **Sem a chave o app não inicia**, porque o disco do Render é apagado a cada reinício e as
   listas sumiriam. Para conferir, abra `/api/health`: deve mostrar `"storage": "firestore"`.
4. Em poucos minutos o app fica disponível em `https://lista-de-compras-XXXX.onrender.com`.
   Abra esse endereço no celular e use **"Adicionar à tela inicial"** para instalar como app.

A cada `git push` na branch `main`, o Render publica a nova versão automaticamente.

> No plano grátis, o servidor "dorme" depois de 15 minutos sem uso, e o primeiro acesso
> seguinte leva cerca de 1 minuto. Para evitar isso, um monitor gratuito (ex.: UptimeRobot)
> pode acessar `/api/health` a cada 10 minutos.

## Rodar no computador (desenvolvimento)

Requer Python 3.12 ou mais recente.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- App: <http://localhost:8000>
- Documentação da API (Swagger): <http://localhost:8000/api/docs>
- Testes: `pytest`

### Abrir no celular

Com o celular na **mesma rede Wi-Fi**, acesse `http://IP-DO-COMPUTADOR:8000`.
Para descobrir o IP, use `ipconfig` e procure o "Endereço IPv4".

Para **instalar como app** ("Adicionar à tela inicial") e receber **notificações do
sistema**, o navegador exige **HTTPS**. Algumas opções:

- publicar em um serviço como Render, Railway ou Fly.io;
- criar um túnel temporário com `cloudflared tunnel --url http://localhost:8000` ou `ngrok http 8000`.

Sem HTTPS, o app funciona normalmente no navegador, com os avisos aparecendo dentro da tela.

### Configuração (variáveis de ambiente)

| Variável             | Padrão             | Descrição                                                        |
| -------------------- | ------------------ | ---------------------------------------------------------------- |
| `FIREBASE_CREDENTIALS` | (vazio)          | Chave da conta de serviço do Firebase (caminho do `.json` ou o conteúdo). Usa o Firestore |
|                      |                    | Vazio = banco JSON local (proibido no Render ou com `APP_REQUIRE_DATABASE=1`) |
| `APP_DATA_DIR`       | `./data`           | Pasta do banco `db.json`                                         |
| `APP_SECRET_KEY`     | gerada em `data/`  | Chave que assina os tokens de login. **Defina em produção.**     |
| `APP_TOKEN_TTL_DAYS` | `30`               | Por quantos dias o login continua válido                         |

## Arquitetura

O projeto segue **arquitetura limpa**: as dependências apontam sempre para dentro,
e as regras de negócio não conhecem banco, HTTP ou framework.

```
app/
├── domain/                 # Regras de negócio puras (sem dependências externas)
│   ├── entities.py         #   User, Group (agregado), ShoppingItem
│   └── errors.py           #   Erros de domínio
├── application/            # Casos de uso
│   ├── ports.py            #   Interfaces: repositórios, hash, token, eventos
│   ├── dto.py              #   Modelos de leitura devolvidos à apresentação
│   ├── auth_service.py
│   ├── group_service.py
│   └── item_service.py
├── infrastructure/         # Implementações concretas das portas
│   ├── persistence/        #   Repositórios: Firestore e JSON local
│   ├── security.py         #   scrypt (senhas) e JWT (tokens)
│   └── event_broker.py     #   Notificações em tempo real (SSE)
├── presentation/
│   ├── api/                # FastAPI: rotas, schemas, erros → HTTP
│   └── web/                # Frontend PWA (HTML/CSS/JS, sem build)
├── container.py            # Raiz de composição (injeção de dependências)
├── factory.py              # Monta a aplicação FastAPI
└── main.py                 # Ponto de entrada (uvicorn)
tests/                      # Testes de domínio, serviços e API
```

**Decisões principais**

- **O `Group` é um agregado.** Pedidos de entrada, aprovação, remoção e saída passam por
  métodos dele, que garantem as regras (ex.: só o dono aprova, e o dono não pode sair).
- **Portas e adaptadores.** Os casos de uso dependem de `Protocol`s, e há dois adaptadores
  de banco: **Firestore** (produção) e **JSON local** (padrão no computador). O `container.py`
  escolhe o adaptador por `FIREBASE_CREDENTIALS`. Nada no domínio ou nos casos de uso muda, e
  os testes rodam os mesmos cenários nos dois bancos (o Firestore com um falso em memória).
- **Banco JSON.** Mantido em memória, com gravação atômica (arquivo temporário +
  `os.replace`), rollback se uma transação falhar e lock entre threads. É adequado para uso
  familiar ou de poucos usuários.
- **Privacidade.** Quem não participa da lista recebe "não encontrada" (404), e não
  "proibido" (403), para não revelar que a lista existe. Os pedidos pendentes só aparecem
  para o dono.
- **Segurança.** Senhas com scrypt e salt, tokens JWT com validade, cabeçalhos de segurança
  (CSP, nosniff etc.) e todo texto do usuário inserido via `textContent` (sem XSS).

**Acessibilidade (frontend)**

- HTML semântico, rótulos em todos os campos, áreas de toque de 48px e foco visível.
- Avisos anunciados por leitores de tela (`aria-live`), e o foco vai para o título a cada troca de tela.
- Tema claro e escuro automáticos, contraste AA e respeito a "reduzir movimento".
- Campo de adicionar item fixo no rodapé, ao alcance do polegar.

## Limitações conhecidas e próximos passos

- **Notificação com o app fechado:** hoje os avisos chegam enquanto o app está aberto,
  mesmo que em segundo plano. Para receber com o app totalmente fechado, o próximo passo
  é implementar **Web Push** (chaves VAPID + `pywebpush`), salvando a inscrição de cada aparelho.
- **Escala:** o distribuidor de eventos fica em memória e funciona com **um único processo**
  do servidor (que é o caso do plano grátis). Para várias instâncias, use Redis para os eventos.
- **Esquema do banco:** as tabelas são criadas automaticamente. Para mudar o esquema com
  dados já em produção, o próximo passo é adotar migrações com Alembic.
- **Login:** ainda não há recuperação de senha nem limite de tentativas de login.
- O token do canal de eventos vai na URL (limitação do `EventSource`). Em produção, prefira
  um token curto e específico para esse canal.
