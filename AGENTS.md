# AGENTS.md

## Projeto
TáNaLista: listas de compras compartilhadas, mobile-first. Backend FastAPI servindo PWA sem build (ES modules, JS puro). 

## Comandos
- Rodar: `uvicorn app.main:app --reload` (Swagger em `/api/docs`)
- Testar: `pytest` (um backend só: `pytest "tests/test_api.py::nome[json]"`)
- Não há linter, formatador nem build de frontend.

## Arquitetura
Clean architecture (`domain` ← `application` ← `infrastructure`/`presentation`). Só `container.py` conhece classes concretas.

- Erros: levante erros de domínio nos serviços, nunca `HTTPException`. O mapeamento para HTTP fica em `presentation/api/errors.py`.
- Privacidade: não membro recebe 404, não 403. Pedidos de entrada pendentes só o dono vê.
- Persistência dupla (Firestore em produção, JSON local). Todo comportamento novo de persistência deve funcionar nos dois e no `tests/fake_firestore.py`.
- Campo novo em entidade: atualize `entities.py`, `mappers.py`, `dto.py`, `schemas.py`, rotas e views JS.
- `event_broker.py` é em memória: só funciona com um processo.

## Frontend
- Texto do usuário só entra no DOM via `textContent` (helper `h()` em `js/dom.js`). CSP estrita: sem script ou estilo inline.
- Preços ficam só no `localStorage`; marcações de comprado offline entram em fila e sincronizam depois.
- Ao criar ou renomear arquivo do frontend, atualize `SHELL` em `sw.js`; ao mudar assets do shell, incremente `CACHE` (`compras-vN`).

## Deploy
Render, automático a cada push na `main`. Sem `FIREBASE_CREDENTIALS` o app não sobe em produção.

## Regras de trabalho
- Tarefa pronta só quando `pytest` passa (roda os dois backends).
- Nunca faça commit nem push sem eu pedir. Push na `main` faz deploy em produção.
- Não adicione linter, formatador, build de frontend ou dependências sem eu pedir.
- Pedido ambíguo: pergunte antes de implementar.