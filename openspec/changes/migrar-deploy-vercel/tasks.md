# Tasks

## 1. Configuração de produção (`app/config.py`)

- [x] 1.1 Em `_has_ephemeral_disk()`, trocar `RENDER` por `VERCEL` (mantendo `APP_REQUIRE_DATABASE`) e atualizar a docstring; em `tests/test_config.py`, trocar `RENDER` por `VERCEL` no fixture `env`, no `parametrize` e em `test_ephemeral_host_with_firebase_uses_firestore`. Verificar: `pytest tests/test_config.py` passa.
- [x] 1.2 Em `Settings.from_env`, quando `_has_ephemeral_disk()` for verdadeiro e `APP_SECRET_KEY` estiver vazia, levantar `RuntimeError` com mensagem em pt-BR que cite `APP_SECRET_KEY`; adicionar teste "Vercel sem APP_SECRET_KEY recusa iniciar" e confirmar que o teste local sem `APP_SECRET_KEY` continua gerando a chave em `APP_DATA_DIR`. Verificar: `pytest tests/test_config.py` passa.
- [x] 1.3 Adicionar teste em `tests/test_config.py` com `FIREBASE_CREDENTIALS` contendo JSON (começando com `{`) sob `VERCEL`, confirmando `storage == "firestore"`. Verificar: `pytest tests/test_config.py` passa.

## 2. Cliente do Firestore único por instância

- [x] 2.1 Adicionar teste (em `tests/test_api.py` ou arquivo novo `tests/test_hosting.py`) que troca `app.container.create_firestore_client` por uma função que conta chamadas e devolve um `FakeFirestore`, cria o app com `create_app(settings)` usando backend firestore, faz várias requisições (`/api/health`, cadastro, login, listagem de listas) e afirma exatamente 1 chamada. Sem mudar `container.py`. Verificar: o teste passa.

## 3. Frontend servido pela função, com CSP

- [x] 3.1 Adicionar teste que pede `/` e `/sw.js` ao `TestClient` e confirma status 200, `Content-Security-Policy` presente em ambos e `content-type` JavaScript no `sw.js`. Não alterar `sw.js` (nem `SHELL` nem `CACHE`). Verificar: o teste passa nos dois backends.

## 4. Arquivos de deploy da Vercel

- [x] 4.1 Criar `vercel.json` na raiz com `$schema`, `regions: ["gru1"]` e `functions["app/main.py"]` com `maxDuration: 300` e `excludeFiles: "{tests/**,openspec/**,data/**,.claude/**,.agents/**}"`, conforme design.md (decisão 2). Verificar: o arquivo é JSON válido (`python -c "import json;json.load(open('vercel.json'))"`).
- [x] 4.2 Criar `.python-version` com `3.12`. Verificar: o arquivo existe e contém só `3.12`.
- [x] 4.3 Remover `render.yaml`. Verificar: `git status` mostra o arquivo como removido e `grep -rni render app tests` não encontra referências.

## 5. Documentação

- [x] 5.1 `README.md`, seção "Publicar na internet": substituir os passos do Render pelos da Vercel (importar o repositório em vercel.com, cadastrar `FIREBASE_CREDENTIALS` com o conteúdo do JSON e `APP_SECRET_KEY` só no ambiente *Production*, endereço `*.vercel.app`, deploy automático a cada push na `main`); remover o aviso de "dorme após 15 minutos"/UptimeRobot. Verificar: `grep -ni render README.md` não retorna nada.
- [x] 5.2 `README.md`: trocar "Render, Railway ou Fly.io" por opções que incluam a Vercel na seção de HTTPS; na tabela de variáveis, trocar "proibido no Render" por "proibido na Vercel" e marcar `APP_SECRET_KEY` como obrigatória na Vercel; adicionar subseção "Limitações do tempo real" explicando avisos em melhor esforço entre instâncias e a reconexão a cada 5 minutos. Verificar: leitura da seção bate com a spec "Tempo real em melhor esforço".
- [x] 5.3 `AGENTS.md`: seção Deploy passa a dizer "Vercel, automático a cada push na `main`. Sem `FIREBASE_CREDENTIALS` e `APP_SECRET_KEY` o app não sobe em produção."; complementar a linha do `event_broker.py` com o impacto na Vercel (várias instâncias e conexões SSE cortadas em 300 s ⇒ avisos em tempo real são melhor esforço). Verificar: `grep -ni render AGENTS.md` não retorna nada.

## 6. Verificação final

- [x] 6.1 Rodar `pytest` completo (backends json e firestore). Verificar: todos os testes passam.
- [x] 6.2 Rodar `uvicorn app.main:app` localmente e abrir `/`, `/api/health` e `/api/docs` para confirmar que o desenvolvimento local não mudou. Verificar: as três respondem 200 e `storage` é `json`.

## Workflow follow-up

- Commit e push na `main` só com autorização explícita da usuária (push faz deploy em produção).
- Na Vercel: importar o repositório, cadastrar `FIREBASE_CREDENTIALS` e `APP_SECRET_KEY` (pode reaproveitar a do Render) em *Production*, conferir `/api/health`, login, item com foto e instalação do PWA no celular.
- Avisar os participantes do novo endereço e, depois de validado, desligar o serviço no painel do Render.
- Arquivar a mudança com `/opsx:archive` após a validação.
