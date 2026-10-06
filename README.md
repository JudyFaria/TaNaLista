# Lista de Compras online

Listas de compras compartilhadas, pensadas para o celular.

> **A ideia:** o café acabou, eu abro a aplicação, adiciono o café à lista e
> minha mãe, que participa da mesma lista, recebe um aviso na hora.

## Funcionalidades

- **Conta:** cadastro e login com usuário e senha.
- **Listas (grupos):** cada lista tem um dono e participantes.
- **Convite por link:** compartilhe pelo WhatsApp, Instagram ou onde quiser
  (botão nativo "Compartilhar" do celular, atalho do WhatsApp e "Copiar link").
- **Aprovação de entrada:** quem abre o link, ou encontra a lista na busca,
  **pede para entrar**, e o dono **aceita ou recusa**.
- **Busca:** encontre listas marcadas como "Aparecer na busca" e peça para entrar.
  Listas privadas só podem ser acessadas pelo link.
- **Itens:** adicionar (com quantidade), marcar como comprado, remover e limpar os comprados.
  O app impede que um item pendente seja adicionado duas vezes.
- **Avisos em tempo real:** quando alguém adiciona um item, os outros participantes
  recebem um aviso na tela (ou uma notificação do sistema, se o app estiver em segundo plano).
- **Gestão:** remover participantes, gerar um novo link (o antigo deixa de valer),
  editar, excluir ou sair da lista.

## Publicar na internet (acesso de qualquer lugar)

O app roda no **Render**, que é grátis e já vem com HTTPS e um endereço público. Os dados
ficam no **Neon**, um PostgreSQL grátis. Nenhum dos dois pede cartão.

1. **Banco (Neon):** crie uma conta em <https://neon.tech>, crie um projeto e copie a
   *connection string* (começa com `postgresql://`).
2. **Servidor (Render):** crie uma conta em <https://render.com> entrando com o GitHub. Clique
   em **New → Blueprint** e escolha este repositório. O Render lê o arquivo `render.yaml`.
3. Quando o Render pedir `DATABASE_URL`, cole a connection string do Neon e confirme.
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
| `DATABASE_URL`       | (vazio)            | PostgreSQL/SQLite via SQLAlchemy. Vazio = banco JSON local       |
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
│   ├── persistence/        #   Repositórios: JSON local e SQLAlchemy (PostgreSQL)
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
  de banco: **JSON local** (padrão no computador) e **SQLAlchemy** (PostgreSQL em produção).
  O `container.py` escolhe o adaptador pela `DATABASE_URL`. Nada no domínio ou nos casos de
  uso muda, e os testes rodam os mesmos cenários nos dois bancos.
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
