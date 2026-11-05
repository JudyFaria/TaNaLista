# meu-mcp-server

MCP server do TáNaLista (`tanalista-mcp`). Uma tool só: `listar_itens_da_lista`, que lê os
itens de uma lista de compras (nome, quantidade com unidade, se já foi comprado) pela API
do TáNaLista. Somente leitura.

- Escopo e limites: [`DECISAO-ESCOPO.md`](DECISAO-ESCOPO.md)
- Ataques, mitigação e antes/depois: [`LOG-INJECTION-TEMPLATE.md`](LOG-INJECTION-TEMPLATE.md)

## Como rodar

Com a API do TáNaLista rodando em `http://127.0.0.1:8000`:

```powershell
# dentro de meu-mcp-server/
npm install
npm test

# na raiz do TáNaLista (escopo local: o token fica fora do git)
claude mcp add --transport stdio --scope local tanalista-mcp -e TANALISTA_URL=http://127.0.0.1:8000 -e TANALISTA_TOKEN=<token> -- node "$PWD\meu-mcp-server\espiao.mjs"
claude                                                 # depois /mcp
```

O nome do server (`tanalista-mcp`) vem antes dos `-e`; senão o `-e` engole o nome.

O token é o `access_token` do login (`POST /api/auth/login`) de uma conta de teste. Ele
vale 30 dias. Pedido de exemplo, sem falar o nome da tool: "o que ainda falta comprar na
lista <id>?". A conversa fica gravada em `conversa.log`.

## Para o dono do negócio

Demos ao assistente de IA uma ferramenta que consulta uma lista de compras do TáNaLista e
diz o que ainda falta comprar, com a quantidade de cada item. Assim dá para perguntar "o
que falta comprar?" sem abrir o app. A ferramenta só lê: não marca item como comprado, não
adiciona nem apaga nada, e não mostra quem adicionou ou comprou cada item. Também não
enxerga listas das quais a conta não participa. Se alguém da lista escrever no nome de um
item uma ordem para o assistente, inclusive escondida em caracteres invisíveis, a
ferramenta tira o que é invisível, avisa que o texto veio de outra pessoa e continua sem
poder alterar nada. A trava está no código, não na boa vontade do assistente.

## Qual risco mais ameaça este domínio

Prompt injection (LLM01). Numa lista compartilhada, quem escreve os nomes dos itens não é
só a dona: é qualquer pessoa que entrou pelo convite. Então todo nome de item é texto de
terceiro chegando ao agente. Output handling pesa menos aqui, porque a saída da tool não
vira HTML nem comando. Supply chain também pesa menos, porque o server é meu e tem só duas
dependências: o SDK oficial do MCP e o zod.