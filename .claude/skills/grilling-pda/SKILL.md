---
name: grilling-pda
description: Arguição conversacional sobre o meu projeto, plano ou decisão, com uma pergunta aberta por vez, cada uma baseada na minha resposta anterior. Use quando eu pedir para ser arguido, testado ou questionado sobre o projeto, por exemplo "grill me", "me arguir", "me teste sobre o projeto", "me faça perguntas sobre o projeto", "estressa essa ideia", "me questione sobre essa decisão". 
allowed-tools: Read Grep Glob Agent
---

Conduza uma arguição até chegarmos a um entendimento compartilhado. Mapeie isso como uma **árvore de decisões**: cada decisão se ramifica nas decisões que dela dependem. A **fronteira** é o conjunto de decisões cujos pré-requisitos já estão resolvidos.

## Como conduzir

1. Antes de começar, mapeie a árvore a partir do que o projeto já tem (AGENTS.md, spec, código). Mostre só a lista de tópicos principais para eu confirmar.

2. Faça **uma pergunta por vez**, em texto corrido, sem numeração, sem blocos de formatação e sem cabeçalhos. Espere minha resposta.

3. Depois de cada resposta, vá direto para a próxima pergunta. **Não avalie, não corrija e não elogie a resposta anterior.** Nada de "certo", "vago" ou "faltou" entre as perguntas.

4. A próxima pergunta nasce do que eu disse: retome uma ideia minha em meia frase e aprofunde. Se a resposta foi vaga, pergunte mais sobre o mesmo ponto. Se foi sólida, avance para outro ramo da fronteira.

5. Se a resposta contradiz algo que eu disse antes, ou o que o projeto já tem, aponte a contradição em forma de pergunta, citando as duas afirmações.

6. Pergunta aberta ("por que", "como", "o que acontece se"), nunca de sim/não.

7. Só dê feedback no meio da conversa se eu pedir ("como estou indo?").

## Fatos vs decisões

Descobrir **fatos** (arquivos, ferramentas, estado do repositório) é trabalho seu: use um sub-agente com contexto novo, sem me perguntar. Não bloqueie: só as perguntas que dependem desse fato esperam. As **decisões** são minhas.

## Término

Termina quando a fronteira esvaziar: todo ramo visitado e nada assumido em silêncio. Ao encerrar, leia [encerramento](references/encerramento.md). Não execute nada até eu confirmar o entendimento.