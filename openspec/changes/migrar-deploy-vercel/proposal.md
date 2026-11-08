# Proposal

## Why

O TáNaLista hoje é publicado no Render (`render.yaml`), cujo plano gratuito "dorme" após 15 minutos sem uso e leva ~1 minuto para acordar. A Vercel tem suporte nativo a FastAPI (detecção automática de `app/main.py`, sem `vercel.json` obrigatório) e deploy automático pelo GitHub, o que permite trocar só a hospedagem mantendo FastAPI, Firestore e todo o código de domínio/aplicação.

## What Changes

- Publicar o app na Vercel como uma única Vercel Function, usando `app/main.py` (entrypoint suportado de forma nativa) e um `vercel.json` mínimo com região próxima do Firestore (São Paulo), duração máxima da função e exclusão de arquivos que não vão para produção.
- Continuar servindo o frontend/PWA pelo próprio FastAPI (`StaticFiles` em `/`), sem mover arquivos para `public/`; `sw.js` continua no mesmo endereço e escopo, com os mesmos cabeçalhos de segurança (CSP).
- Fixar a versão do Python (3.12) para o build da Vercel.
- A detecção de "hospedagem com disco efêmero" passa a reconhecer a Vercel (variável `VERCEL`) no lugar do Render. Nesse ambiente o app se recusa a iniciar sem `FIREBASE_CREDENTIALS` e também sem `APP_SECRET_KEY` (o disco da Vercel é somente leitura e as instâncias não compartilham a chave gerada localmente).
- A chave do Firebase passa a ser informada como conteúdo JSON na variável de ambiente `FIREBASE_CREDENTIALS` (a Vercel não tem "Secret Files"); o código já aceita esse formato.
- Garantir (e cobrir com teste) que o cliente do Firestore é criado uma vez por processo, no carregamento do módulo, e reaproveitado entre requisições.
- Documentar o impacto do `event_broker` em memória no tempo real (SSE) com várias instâncias e com o limite de duração da função, sem resolver agora.
- **BREAKING (operacional)**: remover `render.yaml` e as menções ao Render no `AGENTS.md` e no `README.md`; o endereço público muda de `*.onrender.com` para `*.vercel.app`. Usuários precisam abrir o novo endereço e reinstalar o PWA (dados não se perdem: ficam no Firestore).

## Capabilities

### New Capabilities

- `hospedagem-producao`: como o app se comporta no ambiente de produção (hospedagem serverless): pré-condições para iniciar, entrega do frontend/PWA pelo mesmo endereço da API, reuso do cliente do banco e garantias (e limites) das notificações em tempo real.

### Modified Capabilities

(nenhuma — não há specs existentes em `openspec/specs/`)

## Impact

- **Novos arquivos**: `vercel.json`, `.python-version`.
- **Removido**: `render.yaml`.
- **Código de infraestrutura**: `app/config.py` (detecção da Vercel e exigência de `APP_SECRET_KEY`). Nenhuma mudança em `domain/`, `application/`, rotas ou frontend.
- **Testes**: `tests/test_config.py` (trocar `RENDER` por `VERCEL`, novos casos para `APP_SECRET_KEY`); novo teste de criação única do cliente do Firestore.
- **Documentação**: `AGENTS.md` (seção Deploy e nota sobre `event_broker`), `README.md` (passo a passo de publicação, tabela de variáveis, limitações do tempo real).
- **Dependências**: nenhuma nova (`uvicorn` continua para desenvolvimento local).
- **Operação**: projeto novo na Vercel ligado ao GitHub; variáveis `FIREBASE_CREDENTIALS` e `APP_SECRET_KEY` cadastradas no painel; serviço do Render desligado manualmente após a validação.
