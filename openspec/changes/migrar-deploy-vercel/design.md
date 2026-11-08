# Design

## Context

Estado atual (observado no código):

- `app/main.py` faz `app = create_app()` no carregamento do módulo. `create_app` (`app/factory.py`) monta a API, um middleware HTTP de cabeçalhos de segurança (CSP etc.) e, por último, `app.mount("/", StaticFiles(directory=app/presentation/web, html=True))`.
- `build_container` (`app/container.py`) cria o cliente do Firestore via `create_firestore_client`, que já aceita JSON ou caminho e reaproveita o `firebase_admin` app pelo nome. Como isso roda em `create_app()`, o cliente já nasce no escopo do módulo, uma vez por processo.
- `app/config.py` trata `RENDER` (ou `APP_REQUIRE_DATABASE`) como "disco efêmero" e exige `FIREBASE_CREDENTIALS`. Sem `APP_SECRET_KEY`, gera uma chave em `data/.secret_key`.
- `render.yaml` roda `uvicorn` com `--proxy-headers`, health check em `/api/health`, Python 3.12.7, `APP_SECRET_KEY` gerada pelo Render e a chave do Firebase como Secret File.
- `InMemoryEventBroker` guarda as filas SSE no processo; `/api/events` mantém a conexão aberta com ping a cada 20 s e `retry: 5000`.

Documentação da Vercel consultada (nov/2026): *Deploy a FastAPI app on Vercel*, *Python runtime*, *Functions limits*.

- Entrypoints detectados: `app.py`, `index.py`, `server.py`, `main.py`, `wsgi.py`, `asgi.py`, na raiz ou em `src/`/`app/`, com variável `app`. `app/main.py` se encaixa.
- Python 3.12 (padrão), 3.13, 3.14; versão via `pyproject.toml`, `.python-version` ou `Pipfile.lock`. Dependências via `requirements.txt` são aceitas.
- `StaticFiles` montado é promovido à CDN no build, **exceto** quando há middleware no app principal: aí os arquivos ficam na função. `public/` é servido pela CDN com cabeçalhos padrão.
- Fluid compute por padrão; duração máxima 300 s no Hobby (até 800 s no Pro), incluindo respostas em streaming. Região padrão `iad1`. Corpo de requisição/resposta até 4,5 MB. Disco somente leitura (exceto `/tmp`). A variável `VERCEL` é definida no build e em execução.

## Goals / Non-Goals

**Goals:**
- Deploy na Vercel com zero mudança em `domain/`, `application/`, rotas e frontend.
- Comportamento de produção descrito em `specs/hospedagem-producao/spec.md`.
- Impacto do tempo real documentado para quem mantém o projeto.

**Non-Goals:**
- Tornar o SSE confiável entre instâncias (Redis, Firestore listeners, Pub/Sub etc.).
- Migrar dados, trocar o banco ou mover a pasta do frontend.
- Domínio próprio, previews com banco separado, CI além do deploy automático da Vercel.

## Decisions

### 1. Entrypoint: `app/main.py` sem configuração extra
A Vercel já detecta `app/main.py` com a variável `app`. Não criamos `api/index.py`, `pyproject.toml` nem `[tool.vercel] entrypoint`.
- *Alternativa*: `pyproject.toml` com `tool.vercel.entrypoint = "app.main:app"`. Rejeitada: adiciona um arquivo de projeto novo sem ganho, e a detecção padrão já cobre o caso.

### 2. `vercel.json` mínimo
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "regions": ["gru1"],
  "functions": {
    "app/main.py": {
      "maxDuration": 300,
      "excludeFiles": "{tests/**,openspec/**,data/**,.claude/**,.agents/**}"
    }
  }
}
```
- `regions: gru1` (São Paulo): o Firestore está em `southamerica-east1`; na região padrão (`iad1`, EUA) cada consulta cruzaria o continente.
- `maxDuration: 300`: máximo do Hobby; deixa explícito o teto que corta conexões SSE (ver Riscos). No Pro pode subir até 800.
- `excludeFiles`: tira do pacote o que não roda em produção. `data/` já é ignorado pelo git, mas fica como proteção para `vercel deploy` feito da máquina local (evita publicar `db.json` e `.secret_key`).
- *Alternativa*: sem `vercel.json`. Rejeitada pela latência da região padrão.

### 3. Frontend continua em `StaticFiles` (não usar `public/`)
Mantemos `app.mount("/", StaticFiles(...))`. Como o app tem middleware no nível principal (cabeçalhos de segurança), a Vercel **não** promove esses arquivos para a CDN: eles passam pela função e recebem a CSP e os demais cabeçalhos, como hoje. `sw.js` continua em `/sw.js`, mesma origem, escopo `/`; `SHELL` não muda e `CACHE` não precisa ser incrementado (nenhum asset do shell muda). A mudança de domínio já faz o navegador instalar o service worker do zero.
- *Alternativa*: mover `app/presentation/web` para `public/` (CDN). Rejeitada: reorganiza pastas (fora do escopo), quebra o `uvicorn` local e os testes, e os arquivos sairiam sem a CSP a menos que duplicássemos os cabeçalhos em `vercel.json` (duas fontes da mesma política).
- *Alternativa*: `cdn = true` em `[tool.vercel.fastapi.static]`. Rejeitada pelo mesmo motivo: a CDN ignora o middleware e os arquivos perderiam a CSP.
- *Custo aceito*: cada arquivo estático é uma invocação da função. Para uso familiar, e com o service worker servindo o shell do cache, é irrelevante.

### 4. Cliente do Firestore no escopo do módulo: manter como está e cobrir com teste
O fluxo `app/main.py` → `create_app()` → `build_container()` → `create_firestore_client()` já roda uma vez por processo, no import; com Fluid compute a instância é reaproveitada entre requisições. Não mexemos em `container.py`. Acrescentamos um teste que substitui `create_firestore_client` por um contador (com o `tests/fake_firestore.py`), cria o app, faz várias requisições e confirma uma única criação.
- *Alternativa*: mover a criação para um `lifespan`. Rejeitada: a Vercel suporta lifespan, mas o import já cumpre o papel e evita mexer na composição.

### 5. Detecção da hospedagem: `VERCEL` no lugar de `RENDER`, e `APP_SECRET_KEY` obrigatória
Em `app/config.py`, `_has_ephemeral_disk()` passa a olhar `VERCEL` ou `APP_REQUIRE_DATABASE` (o nome `RENDER` sai). Nesse modo, `from_env` também falha sem `APP_SECRET_KEY`: o `_local_secret` tentaria gravar em `data/` (somente leitura na Vercel) e, mesmo em `/tmp`, cada instância teria uma chave diferente, derrubando logins aleatoriamente.
- *Alternativa*: manter `RENDER` junto com `VERCEL`. Rejeitada: o pedido é remover o Render; `APP_REQUIRE_DATABASE` continua servindo para qualquer outro provedor.

### 6. Chave do Firebase como conteúdo em variável de ambiente
A Vercel não tem Secret Files. `FIREBASE_CREDENTIALS` recebe o JSON inteiro da conta de serviço (cadastrado como *Sensitive*, só no ambiente *Production*). O código já trata `raw.startswith("{")`; nenhuma mudança.

### 7. Python 3.12 via `.python-version`
Arquivo `.python-version` com `3.12`, igual ao Render e ao mínimo do README. Evita criar `pyproject.toml`. `requirements.txt` continua sendo a fonte das dependências.

### 8. O que sai junto com o Render
- `--proxy-headers`/`--forwarded-allow-ips`: não se aplicam (a Vercel não roda `uvicorn` com essas flags) e o app não usa IP do cliente nem gera URLs absolutas.
- `healthCheckPath`: a Vercel não tem health check equivalente; `/api/health` continua existindo para conferência manual.
- Aviso de "dorme após 15 minutos" e sugestão de UptimeRobot: removidos do README.

## Risks / Trade-offs

- **[SSE entre instâncias]** O `InMemoryEventBroker` só entrega a quem está conectado na mesma instância que processou a escrita. Com Fluid compute a Vercel pode abrir várias instâncias (e reciclá-las a qualquer momento), então avisos em tempo real viram melhor esforço: alguns participantes não recebem o toast/notificação. → Os dados continuam corretos (vêm do Firestore); documentar em `AGENTS.md` e `README.md`. Solução definitiva fica para outra mudança.
- **[SSE e duração máxima]** Cada conexão `/api/events` dura no máximo 300 s (Hobby); a Vercel encerra com timeout e o `EventSource` reconecta (`retry: 5000`). Avisos emitidos nos ~5 s de reconexão se perdem. → Aceito e documentado.
- **[Custo de conexões abertas]** Cada aba aberta mantém uma invocação viva até 300 s, contando tempo de memória provisionada. → Para uso familiar fica dentro do plano gratuito; acompanhar o uso no painel da Vercel.
- **[Cold start]** Primeira requisição de uma instância nova importa `firebase_admin` e cria o cliente. → Bem menor que o "acordar" de ~1 min do Render; aceito.
- **[Previews usando o banco de produção]** Se `FIREBASE_CREDENTIALS` for cadastrada também para *Preview*, deploys de branches gravariam no Firestore real. → Cadastrar só em *Production*; previews então falham ao iniciar (comportamento desejado pela spec).
- **[Mudança de endereço]** Usuários com o PWA instalado do `onrender.com` continuam abrindo o endereço antigo. → Avisar e pedir para abrir o novo endereço e reinstalar; desligar o Render só depois.
- **[Limite de 4,5 MB por requisição]** → Fotos já são reduzidas no celular para ≤ 350 KB (limite do servidor 400 KB); sem impacto.

## Migration Plan

1. Implementar as tarefas e rodar `pytest` (os dois backends).
2. Criar o projeto na Vercel importando o repositório do GitHub; cadastrar `FIREBASE_CREDENTIALS` (conteúdo JSON) e `APP_SECRET_KEY` (pode ser o mesmo valor do Render, para os logins atuais continuarem válidos) no ambiente *Production*.
3. Com a autorização da usuária, fazer push na `main`; a Vercel publica. Conferir `/api/health` (`"storage": "firestore"`), login, criação de item, foto e instalação do PWA.
4. Avisar os participantes do novo endereço; depois desligar/excluir o serviço no painel do Render.

**Rollback**: o serviço do Render continua no ar até o passo 4. Se algo falhar, basta seguir usando o endereço do Render e reverter o commit (`git revert`), que traz de volta o `render.yaml`. Os dois apontam para o mesmo Firestore, então não há dado a migrar em nenhum sentido.

## Open Questions

- Plano da Vercel (Hobby ou Pro): só muda o `maxDuration` possível (300 vs. até 800 s); o plano assume Hobby e pode ser ajustado depois sem mudar specs ou tarefas.
