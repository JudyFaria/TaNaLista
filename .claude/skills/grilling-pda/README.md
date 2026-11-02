# grilling-pda

Skill de arguição: conduz uma conversa de pergunta e resposta sobre o projeto, fazendo uma pergunta por vez, cada uma baseada na resposta anterior, até chegar a um entendimento compartilhado. O balanço do que ficou sólido e frágil só vem no encerramento.

Adaptada da skill `grilling` de Matt Pocock. A mudança central: em vez de rodadas de perguntas numeradas com recomendação, é uma conversa de uma pergunta por vez, sem avaliação entre as respostas.

## Como usar

Copie esta pasta para `.claude/skills/` de outro projeto e reinicie o Claude Code. Dispare com "grill me", "me arguir sobre o projeto" ou "me faça perguntas sobre o projeto". Também funciona chamando `/grilling-pda`.

## Estrutura (Progressive Disclosure)

```
grilling-pda/
├── SKILL.md                    # fluxo da arguição (carregado ao disparar)
├── README.md
└── references/
    └── encerramento.md         # balanço final (lido só quando a arguição termina)
```

O `SKILL.md` traz só o fluxo. O formato do balanço fica em `references/encerramento.md`, que só entra no contexto no fim da conversa.

`allowed-tools: Read Grep Glob Agent`: a skill só lê o projeto e lança um sub-agente para levantar fatos. Não edita nem executa nada.

