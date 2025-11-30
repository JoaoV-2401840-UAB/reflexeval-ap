# reflexeval-ap
Arquitetura e Padrões de Software 2025
O ReflexEval AP utiliza o padrão de criação Factory Method para gerar diferentes tipos de sessões de reflexão (inicial, intermédia e final).

Estrutura do padrão no projeto:
ReflectionSession - classe base (Product)
InitialReflectionSession, IntermediateReflectionSession, FinalReflectionSession — Concrete Products
SessionFactory - interface que define o Factory Method
StandardSessionFactory - implementação concreta que decide que sessão criar
SessionService - cliente do padrão; coordena a lógica de criação e devolve a view model

Onde é usado?

O endpoint:

GET /debug/session?planId=demo-plan&sessionIndex=0

chama o SessionService, que por sua vez utiliza a StandardSessionFactory para criar dinamicamente a sessão correta.
O resultado final é devolvido em JSON.

Este padrão facilita:
"a inclusão de novos tipos de sessão,"
"a manutenção da lógica de criação num único ponto,"
"a redução de condicionais espalhadas pelo código,"
"uma arquitetura interna mais limpa e extensível."
