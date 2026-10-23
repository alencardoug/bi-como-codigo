# Revisão de plano — site público para aprender o caminho dos dados

> **De Codex para Claude Code, a pedido do Owner.** Este é um plano para crítica, com ideias
> deliberadamente abertas a simplificação ou descarte. A entrega desta sessão é este documento.
> Implementação, escolha de ferramentas e publicação ainda não foram executadas.
>
> Passagem conforme a [skill `revisao`](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/.claude/skills/revisao/SKILL.md), adaptada à revisão de
> um plano ainda sem implementação. Arquivo transitório, fora do mapa do README. O pedido vivo
> do Owner continua definindo o papel de cada sessão.

| Campo | Informação |
|---|---|
| Data | 22/10/2026 |
| Autor da proposta | Codex |
| Revisor pretendido | Claude Code |
| Base inspecionada | `26b58b33deac1ee89b9f7de1292ba40fec0d4de2`; árvore limpa antes deste arquivo |
| Situação | Crítica do Claude Code registrada (achados RP-01 a RP-15, no fim). Plano resultante, com todas as decisões do Owner, em [`PLAN.md`](PLAN.md); próximo passo: a revisão do Codex sobre o plano, pedida na §10 dele |
| Fonte das restrições | Conversa com o Owner, [CLAUDE.md](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/CLAUDE.md) e código referenciado abaixo |

## 1. O pedido e as escolhas já feitas

O Owner quer publicar um site com o mapa dos dados do eng_dados. Seu primeiro objetivo é
**aprender o fluxo e as transformações**, começando pelo resultado analítico e investigando
como ele foi produzido. O dashboard deve responder às perguntas que já justificam as views
de `consumption`.

Estas escolhas vieram da conversa e não precisam ser perguntadas outra vez:

| Assunto | Escolha do Owner |
|---|---|
| Primeira análise | Começar por uma view: `consumption.monthly_revenue_by_channel_and_category`, a P01 |
| Interação | Filtros e gráficos interativos |
| Aprendizado | Clicar em um indicador e acompanhar um item de pedido até sua contribuição no resultado |
| Problema a resolver | O mapa atual de dependências abre quase todas as tabelas; a exploração deve ser focada e ilustrativa, possivelmente por coluna |
| Atualização | Sob solicitação, **somente reler a view**; o desafio local de engenharia já terminou |
| Quem atualiza | Apenas o Owner; análise e explicações ficam públicas |
| Complexidade | Solução simples; atualização pode ficar para depois se complicar a primeira entrega |
| Outras ideias | Anotar outras maneiras de explorar para o Claude avaliar quais valem a pena |

**Síntese para orientar a implementação futura:** um dashboard educativo da P01, ligado a um
percurso verificável de um item de pedido. A explicação abre por etapas e por coluna, mostra
transformações e regras que influenciam o resultado e reutiliza o projeto existente. A operação
pública deve funcionar independentemente da máquina local; o Owner publica novas leituras da
view quando quiser. Essa forma de operação é a proposta da §4, ainda sujeita à crítica.

## 2. Mapa de revisão e fontes que devem continuar sendo a referência

**Declaração desta entrega:** este `REVIEW.md`, escrito à mão e sujeito à revisão integral.
Não há código nem artefato derivado novo. As seções seguintes contêm propostas, não decisões
arquiteturais aceitas. Os documentos e modelos abaixo continuam donos dos fatos sobre o projeto.

| Fonte | O que conferir ou reaproveitar |
|---|---|
| [Perguntas de negócio — P01](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/glossario_de_negocio/perguntas_de_negocio.md#p01--qual-a-receita-líquida-por-mês-canal-e-categoria-de-produto) | Pergunta, medidas e recortes existentes |
| [View da P01](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/consumption/monthly_revenue_by_channel_and_category.sql) | Grão publicado, dimensões, agregações e filtro de venda realizada |
| [Contrato de consumo](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/consumption/_consumption__models.yml) | Colunas, tipos e classificação; evitar inventar filtros que a view não oferece |
| [Receita em `trusted`](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/trusted/order_items.sql) | Cálculo e ponto exato de arredondamento |
| [Pedidos em `trusted`](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/trusted/orders.sql) | Regra de `is_realised` |
| [Fato de itens](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/dbt/models/analytics/fact_sales_order_item.sql) | Identidade da origem, data, dimensões e junções temporais |
| [Linhagem existente](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/src/mvp_ed1/models/lineage.py) e [derivação das folhas](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/src/mvp_ed1/models/sensitivity.py) | Dependências imediatas por coluna, origens terminais e limites da regra do valor |
| [Dicionário, §3](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/dicionario_de_dados.md#3-linhagem) | Linhagem publicada e travessias fora do dbt |
| [Trilha de estudo](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/CONVERSAS_COM_CHAT/trilha_de_estudo_fase_local.html) | Jornada, exemplos históricos, navegação e mapa já existentes; avaliar reaproveitamento |
| [Governança](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md) | Classificação e acesso; o consumidor analítico lê `consumption` |
| [ADR-0018](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0018-fatos-e-views-a-partir-de-perguntas-de-negocio.md) | Perguntas antes das views e contrato aplicado |

O site será uma apresentação didática derivada dessas fontes. Definição de métrica, SQL e
linhagem não devem ganhar uma segunda declaração manual dentro de componentes visuais. Texto
didático pode ser curado, com referência ao arquivo e à versão que o sustentam. Divergência entre
documento e implementação deve ser registrada, não escondida pela apresentação.

## 3. Experiência proposta

### 3.1 Uma pergunta e uma tela de análise

Abrir com a pergunta **“Qual a receita líquida por mês, canal e categoria de produto?”**,
uma explicação curta, indicação de dados sintéticos e data da extração. A primeira tela propõe:

- filtros de período **mensal**, canal e categoria, limitados às colunas da view;
- receita líquida do recorte como indicador principal;
- evolução mensal e comparação por canal ou categoria;
- tabela acessível com os valores que sustentam os gráficos;
- ação explícita **“Como este valor foi formado?”**, acessível também pelo teclado.

Receita bruta, desconto e unidades podem complementar a receita líquida se ajudarem a contar a
história. Não é necessário preencher a tela com todos os campos da view. **Contagem de pedidos
exige a análise da §5.2 antes de virar indicador.**

Filtros devem alterar gráficos, tabela e contexto da explicação de forma coerente. Distinguir
“nenhum resultado para este filtro” de receita igual a zero. Ordenar meses cronologicamente e
explicar a cobertura do período; ausência de linha não prova, sozinha, ausência de vendas.

### 3.2 Percurso didático com abertura progressiva

O clique começa na métrica selecionada. A primeira explicação mostra a conta em linguagem de
negócio; depois oferece as etapas que a sustentam. A proposta é usar uma sequência legível de
cartões conectados, antes de justificar uma biblioteca de grafos.

```text
Pergunta e filtros → indicador → explicação da conta
                                   ↓
                         item de pedido verificado
                                   ↓
                 etapas, colunas e regras expandíveis
```

O usuário pode investigar de trás para frente, mas as setas de **fluxo de dados** mantêm a direção
origem → consumidor. A legenda distingue essa direção da ordem de navegação.

Cada etapa mostra: camada e objeto, colunas relevantes, valores de entrada e saída, operação
aplicada e motivo. O trecho de SQL fica junto da explicação, com o restante sob expansão. Quando
uma etapa apenas transporta o valor, dizer isso; não inventar transformação para animar a tela.

**Três perguntas organizam o percurso:**

| Pergunta | O que mostrar |
|---|---|
| De onde vem o valor? | Quantidade, preço e desconto; cálculo por item; soma no consumo |
| Por que esta venda entra neste grupo? | Venda realizada, mês da venda, canal, categoria e junções que determinam sua associação |
| Que controles permitem que esse dado seja usado? | Ingestão, captura elegível do legado, limpeza, quarentena e demais dependências pertinentes |

A primeira abre por padrão. As outras ficam visíveis como caminhos adicionais, sem expandir
todas as tabelas de uma vez. Dependência de controle não deve ser desenhada como se fornecesse
diretamente o valor monetário.

### 3.3 O que aproveitar da linhagem por coluna

A linhagem já publicada liga `net_revenue_amount` a `quantity`, `unit_price` e `discount_amount`
de `order_items`, nas duas origens. O código mantém folhas imediatas em `Lineage.leaves` e fecha
as origens terminais em `origins()`. **Proposta:** avaliar a extração do percurso intermediário
dessas folhas, preservando `meta.lineage` nas pontes do legado.

Esse mecanismo segue as expressões que produzem valores. Não é, por si só, uma explicação
completa de filtros, condições, cardinalidade das junções ou pertencimento de uma linha a um
total. O próprio legado usa uma declaração explícita para atravessar o payload compartilhado.
Portanto, não prometer “linhagem completa automática” a partir dele.

Para a P01, propor uma declaração didática pequena que **referencie** as regras e os trechos de
SQL existentes. Usá-la para organizar a narrativa e as dependências complementares. O revisor
deve avaliar se isso basta ou se acrescentaria manutenção demais. Alterar o algoritmo de
classificação/linhagem geral do projeto não é pré-requisito desta primeira experiência.

No mapa, manter `retail` e `legacy` como ramos identificáveis; selecionar um ramo explica aquela
origem. Isso **não cria um filtro de origem no dashboard**: a view atual não expõe
`source_system`. Dependências amplas de limpeza/certificação podem aparecer agrupadas com
explicação e expansão opcional. O detalhe não desaparece; fica fora do percurso principal.

### 3.4 Um exemplo pequeno que realmente participa do resultado

Escolher uma identidade composta por `source_system` e `order_item_id`, mantendo `order_id`
quando necessário. O mesmo identificador numérico pode existir nas duas origens. Começar por um
item de `retail` é uma sugestão de simplificação; o ramo do legado pode ser a próxima aula.

A trilha existente usa `ORD-0000037`. É **candidato histórico**, não amostra atual confirmada.
Escolher ou reconfirmar o item por consultas somente de leitura. Preferir um caso que explique
preço, quantidade e desconto sem exigir muitas exceções de uma vez.

A amostra precisa provar:

1. a identidade do item nas etapas apresentadas e a origem/captura de cada leitura;
2. o cálculo em `trusted`, incluindo o arredondamento por item;
3. a passagem pela fato e as associações de mês, canal e categoria;
4. a elegibilidade pela regra de venda realizada;
5. a contribuição no grupo exato da view, distinguindo **valor do item**, **demais itens** e
   **total do grupo**. O item ilustra o total, não o substitui.

Leituras no armazém devem usar um estado coerente durante a captura. Uma leitura atual de
`source_db` e outra de `warehouse_db` não demonstram um corte comum entre bancos: preferir o
bruto já ingerido para comprovar o estado que alimenta o armazém; a travessia até a origem usa
o mapeamento existente e uma evidência compatível, ou fica explicitamente limitada.

**Simplificação sugerida:** oferecer inicialmente um recorte guiado conhecido. Se os filtros
do visitante excluírem o exemplo, informar isso e oferecer “Abrir o recorte do exemplo”. Não
escolher um item inexistente nem apresentar a amostra como participante de qualquer gráfico.

### 3.5 Como conciliar a amostra com a atualização somente da view

A view é agregada: relê-la não recupera os itens que a formaram. Há dois produtos de dados:

- **dashboard:** uma extração da view, que o Owner pode substituir sob solicitação;
- **aula:** uma amostra pequena e verificada das camadas, com seu contexto e data próprios.

Na primeira versão, construir ambos a partir de um corte conciliado. Em uma atualização futura
limitada à view, conservar a aula como **exemplo histórico** e abrir o recorte histórico que foi
verificado. Não afirmar que o item continua compondo o total recém-extraído. Igualdade de totais
também não prova igualdade dos itens que os compõem.

Essa separação preserva o pedido “somente view”. Atualizar automaticamente a amostra exigiria
novas leituras das camadas e seria uma ampliação a discutir. O Claude deve criticar se a mudança
entre análise atual e exemplo histórico fica compreensível; se não, priorizar uma primeira
publicação fixa e adiar a atualização, possibilidade já aceita pelo Owner.

## 4. Forma simples de implementar e publicar — proposta para crítica

### 4.1 Alternativa preferida: site estático com extração local

```text
Owner, na máquina local
  → leitura da view em sessão somente de leitura
  → exportação e conferência de um pacote de dados
  → publicação do pacote validado junto do site
  → visitantes filtram e exploram os dados no navegador
```

A preferência por essa alternativa é uma **hipótese de simplicidade**, não uma medição de custo
ou desempenho. Ela evita depender de um banco local acessível pela internet. O mecanismo de
atualização pode ser um comando local documentado, seguido de publicação pelo Owner; um botão
administrativo dentro do site não é requisito da conversa.

| Alternativa | Benefício | Custo ou limite a avaliar |
|---|---|---|
| A — extração local e hospedagem estática | Operação pública independente do banco; atualização controlada pelo acesso do Owner à publicação | Exige exportação, validação e rotina de publicação; tamanho do pacote ainda não medido |
| B — site com API e área administrativa | Atualização pela interface | Acrescenta serviço, autenticação e conectividade até o banco; parece desproporcional ao primeiro escopo |
| C — publicação fixa inicial | Menor escopo para validar análise e aprendizado | Não oferece nova leitura da view; alternativa autorizada se a atualização atrasar o essencial |

Pedir ao Claude que compare A e C primeiro. Hospedagem, biblioteca de gráficos e eventual
framework continuam sem escolha. Não há preço, limite de plano de serviço ou prazo estimado
confirmado neste documento. A escolha de ferramenta segue o processo do Owner em `CLAUDE.md` §5.

### 4.2 Peças pequenas, separadas pelo que muda

O revisor deve propor os caminhos definitivos. Como organização conceitual:

- **declaração da análise:** identificação da view, campos permitidos, métricas, filtros,
  formatos e regras de agregação; preferir derivar do contrato o que ele já declara;
- **declaração do percurso:** sequência didática, referências ao código, relações complementares
  e identidade do exemplo; sem copiar o modelo de negócio inteiro;
- **exportador local:** leitura da view e serialização; a captura inicial da amostra é uma
  operação distinta, com permissões e procedência próprias;
- **artefatos derivados:** dados da análise, amostra didática, trechos/arestas da linhagem e
  metadados de versão;
- **interface:** apresentação e estado dos filtros, lendo esses artefatos.

Um frontend simples com HTML, CSS e JavaScript é uma opção a comparar; o projeto já tem material
nesse formato. Reaproveitar padrões úteis da trilha não significa publicar o HTML inteiro:
seu conteúdo, imagens, exemplos e scripts precisam ser selecionados para este escopo público.
Escolher biblioteca de gráficos apenas se ela reduzir trabalho de interação e acessibilidade.

O pacote precisa identificar sua versão, view de origem, momento da extração, período coberto,
versão do código de referência e versão/data da amostra. O commit do exportador não prova qual
código construiu o armazém: registrar a versão do build apenas se houver evidência; caso contrário,
deixar esse vínculo não verificado. Hora da extração também não é hora da ingestão.

Arquivos públicos devem resultar de uma lista explícita de inclusão. `dbt/target/`, `.env`, logs,
credenciais e dumps completos não fazem parte do pacote. O `.gitignore` já exclui `data/`,
`dbt/target/` e alguns formatos de dados; definir conscientemente onde ficam os artefatos de
publicação, sem abrir uma exceção ampla ou usar inclusão forçada como desenho permanente.

### 4.3 Comportamento da atualização

Preparar a nova extração separadamente, validar contrato e valores e só então promover a versão
publicada. Falha de leitura ou de validação preserva a última publicação válida, com sua data.
Registrar o erro no ambiente do Owner; não apresentar sucesso nem mudar a data no site.

A rotina lê a view existente. Não dispara Airbyte, DAG, dbt build, geração de dados nem streaming.
Se a view estiver ausente ou inconsistente, relatar o impedimento; reconstruir o fluxo é outro
trabalho. Publicação deve manter dados, interface e metadados de versão compatíveis para evitar
misturar arquivos antigos e novos por cache. A solução concreta depende da hospedagem escolhida.

### 4.4 Publicação e classificação já existente

A publicação pública foi solicitada. Sua implementação precisa representar essa decisão de forma
concreta: quais campos agregados e qual amostra sintética serão expostos. O contrato atual marca
valores monetários da P01 como `confidential`; a política também restringe dados pessoais mesmo
sintéticos. Isso merece avaliação explícita pelo Claude, com referência à
[Governança, §§4 e 10](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#4-classificação-de-sensibilidade).

Proposta: declarar o escopo da demonstração pública e preservar a classificação de origem;
não trocar metadados gerados para `public` só para viabilizar o site. Definir com o Owner o
registro necessário para a publicação e eventuais alterações de acesso. A autorização de ler a
view não confere ao visitante acesso às camadas intermediárias.

O dashboard usa o acesso de consumo. A amostra didática é preparada no contexto autorizado de
estudo/auditoria do Owner e publica somente campos necessários, sem nome, documento, e-mail,
endereço ou payload completo. A política e a forma de acessar essas camadas precisam ser
conferidas antes da captura; não ampliar `analyst` nem criar nova role implicitamente.

## 5. Cuidados de semântica que influenciam a interface

### 5.1 Cálculo e precisão

O SQL de `trusted.order_items` calcula a receita por item como
`round(quantity * unit_price, 2) - discount_amount`; a view soma o resultado dos itens elegíveis.
Uma explicação que arredonde apenas o total pode ensinar outra regra. Mostrar o arredondamento
onde ele ocorre e manter valores exatos nos cálculos que alimentam a interface.

Proposta de transporte: decimais como texto com escala preservada. Para somar campos monetários
de duas casas no navegador, avaliar inteiros de centavos com faixa validada ou aritmética decimal.
O preço unitário tem quatro casas no código inspecionado: não converter toda coluna monetária
cegamente em centavos. Se o desenho do gráfico usar aproximação numérica, o rótulo e o total devem
vir do cálculo exato. Sem escolher biblioteca aqui.

O calendário do recorte segue a regra da fato, que obtém a data da venda em
`America/Sao_Paulo`. Categoria pode depender da versão do produto na venda. Não trocar essas
definições por mês da extração ou cadastro atual para facilitar a apresentação.

### 5.2 Pedidos e recortes disponíveis

O SQL usa `count(distinct f.order_id)` por grupo. Somar as contagens de categorias não garante
pedidos distintos no total, porque um pedido pode ter itens em mais de uma categoria. A view
agregada não oferece os identificadores necessários para deduplicar novamente no frontend.

Há uma segunda questão para o revisor: a contagem não inclui `source_system`, embora as origens
possam reutilizar `order_id`. **É um risco identificado por leitura do SQL; não foi medida uma
subcontagem nesta sessão.** Conferir antes de publicar essa métrica. Não corrigir a view nem
redefinir a pergunta como efeito colateral do site. Priorizar receita e unidades no MVP é uma
forma de manter o escopo enquanto a contagem é avaliada.

A P01 não expõe item, SKU, pedido, origem ou dia individual. Explorar um exemplo desses campos na
aula não permite oferecer esses filtros na análise agregada. Um recorte novo exige avaliar o
contrato, não distribuir totais existentes por aproximação.

## 6. Sequência de trabalho sugerida

| Etapa | Entrega | Critério para avançar |
|---|---|---|
| 1 — crítica deste plano | Parecer do Claude: viabilidade, cortes, lacunas, alternativas e decisões do Owner | Escopo mínimo explícito, sem confundir sugestões com escolhas aceitas |
| 2 — esboço da experiência | Uma tela e um percurso de receita, com anotações de interação | Owner consegue explicar o que vai aprender; números ausentes ficam como pendentes |
| 3 — pacote inicial | Extração somente de leitura da P01 e amostra conciliada, após definir publicação/acesso | Grão, identidade, cálculo, pertencimento e procedência conferidos |
| 4 — versão local utilizável | Filtros, gráficos, tabela, explicação progressiva e estados sem dados | Valores conferem com a extração e o percurso continua compreensível |
| 5 — primeira publicação | Site público independente dos serviços locais | Conteúdo publicado confere com o pacote e pode ser usado por teclado e em tela estreita |
| 6 — atualização sob demanda | Rotina do Owner, se o esforço compensar | Releitura só da view, falha preserva versão anterior e aula mantém seu contexto histórico |

Não há estimativa em horas nem volume do pacote medidos. Pedir ao Claude uma avaliação qualitativa
de esforço por etapa; qualquer estimativa futura precisa ser rotulada como estimativa. Não esperar
implementar todas as formas de exploração para validar a primeira pergunta.

## 7. Ideias adicionais para o Claude criticar

Tudo nesta seção é **sugestão**, não requisito aprovado. Classificar cada ideia como manter,
simplificar, adiar ou descartar, explicando o motivo.

| Ideia | Valor para o aprendizado | Dependência ou risco | Prioridade sugerida |
|---|---|---|---|
| Fórmula que destaca a coluna correspondente em cada etapa | Conecta linguagem de negócio, SQL e dado | Precisa preservar escala e arredondamento reais | Candidata ao primeiro percurso |
| Comparação antes/depois, com mudanças destacadas | Explica renome, cast, limpeza e cálculo | Muitas etapas não alteram o valor; representar isso honestamente | Candidata ao primeiro percurso |
| “Por que esta venda entra?” com filtro e junção destacados | Explica a população da métrica, além da fórmula | Condições não vêm completas da linhagem do valor | Candidata ao primeiro percurso |
| Glossário contextual de grão, dimensão, fato e view | Reduz a necessidade de sair da análise | Referenciar o glossário existente para evitar definições paralelas | Baixo escopo aparente, não medido |
| Pergunta curta antes de revelar uma transformação | Faz o visitante prever e depois conferir | Resposta deve vir da evidência; dispensar gamificação no início | Testar após o percurso básico |
| Link que preserva filtros e etapa da aula | Facilita voltar ao estudo e compartilhar um recorte | Precisa preservar também a versão ou avisar sobre mudança dos dados | Próxima melhoria |
| Navegação livre por coluna | Permite investigar além do roteiro | Pode recriar o mapa excessivo; exigir foco e expansão local | Depois da P01 guiada |
| Mesmo campo em `retail` e `legacy` | Mostra duas entradas chegando ao mesmo contrato | Chaves iguais não provam que é a mesma venda; comparar casos identificados | Próxima aula candidata |
| Uma rejeição até a quarentena | Mostra por que nem todo dado chega ao indicador | Escolher caso verdadeiro e evitar expor payload inteiro | Próxima aula candidata |
| Mapa das dependências de controle do legado | Explica por que tantas tabelas aparecem no grafo atual | Certificação e limpeza compartilhadas exigem narrativa própria | Expansão da aula do legado |
| Categoria na venda versus categoria atual | Ensina histórico e junção temporal | Só vale com caso observado e evidência das versões | Adiar até localizar exemplo |
| Comparar duas extrações da P01 | Mostra o que mudou no consumo | Dois totais diferentes não explicam a causa; precisa evidência adicional | Adiar |
| Evidência de qualidade junto da etapa | Liga dado, regra e verificação | Teste de outra data não comprova a qualidade da extração atual | Adiar ou mostrar apenas referência datada |
| Simular inclusão de pedidos não realizados | Explora a regra de seleção | Não se calcula isso só com a view filtrada; precisaria outro conjunto autorizado | Adiar |

Evitar tornar chatbot, SQL livre no navegador, grafo universal, acesso a todas as views ou ambiente
de execução de pipelines pré-requisitos da primeira entrega. São escopos distintos, sem benefício
demonstrado para a experiência inicial.

## 8. Critérios propostos de aceitação e validação

**Aprendizado:** ao terminar o percurso, o Owner consegue localizar as colunas que formam a
receita, explicar onde ela é calculada e arredondada, por que um item entra no grupo e como a
contribuição dele se relaciona com o total. Fazer essa avaliação com a tela pronta; desenho bonito
e clique funcionando, isoladamente, não demonstram aprendizado.

**Correção:** comparar valores por grupo e por recortes representativos com a consulta da view;
conferir as somas monetárias sem perda de precisão, a identidade composta do exemplo e suas
junções, e o tratamento de recortes sem dados. Não criar resultados simulados com aparência de
medição. A amostra deve ter valores extraídos e consultas de conferência preservadas.

**Navegação:** filtro, gráfico e tabela concordam; toda etapa expandida tem um caminho de volta;
setas e legendas são consistentes; diferenças não dependem só de cor. Conferir teclado, foco,
contraste e tela estreita na implementação. Preferir links para trechos de fonte na versão
referenciada, sem depender de números de linha de um arquivo que pode mudar.

**Operação:** visitar o site não consulta nem altera a máquina local. Quando implementada, a
atualização é exclusiva do Owner, relê somente a view e conserva a publicação anterior se falhar.
Datas de extração e de exemplo histórico aparecem com os significados corretos.

**Revisão:** revisar integralmente as declarações da análise, do percurso e dos campos públicos;
conferir o derivado por amostragem e reconciliação. Testar o que tem risco real — agregação,
precisão, pertencimento, mistura de versões e falha de publicação —, sem acrescentar uma suíte
extensa só para repetir a marcação da interface.

## 9. O que não foi verificado e premissas

### Não verificado nesta entrega

- Estado dos bancos, disponibilidade da view e correspondência do armazém atual com o commit lido.
- Valores, cardinalidade, tamanho da extração e tempo de leitura/publicação.
- Item candidato, participação no grupo, compatibilidade entre cortes e existência de desconto
  ou outra transformação ilustrativa na amostra que vier a ser escolhida.
- Ocorrência e impacto de colisões na contagem de pedidos da P01.
- Completude e atualidade de `dbt/target/manifest.json`; um manifest parcialmente compilado não
  sustenta a geração de um percurso completo.
- Hospedagem, bibliotecas, custos, desempenho, acessibilidade e usabilidade do futuro site.
- Solução concreta de publicação dos campos classificados e de leitura das camadas para a amostra.

### Premissas a confirmar

- O objetivo principal continua sendo estudo do projeto concluído, com uma demonstração pública.
- O recorte agregado da P01 provavelmente cabe numa publicação estática; **tamanho não medido**.
- Um exemplo pequeno, com expansão guiada, deve ser mais legível que o grafo inteiro; **usabilidade
  não testada**.
- Os artefatos de linhagem podem ser reaproveitados sem alterar a classificação geral; o caminho
  de extração das arestas intermediárias ainda precisa ser prototipado.

### Ambiente que a revisão precisa

Para criticar o plano, basta este checkout. Nenhum serviço precisa ser iniciado. Sondas futuras
de dados exigem apenas o ambiente estritamente necessário e consultas somente de leitura,
conforme a [Execução Local](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md). Não são parte da revisão documental presente.

O gerador da skill não foi executado: ele pressupõe uma entrega em commits e roda `make check`,
que inclui dbt build. Este plano foi preparado manualmente e sua estrutura é conferida com
`dossie.py --conferir`; isso não constitui validação dos dados nem do futuro site.

### Onde hesitei

- **Grafo livre ou percurso curado:** proponho começar pelo percurso; deixa aberta a exploração
  livre por coluna depois de comprovar que a primeira explicação funciona.
- **API ou pacote estático:** proponho o pacote; um botão local ou rotina de publicação satisfaz
  a atualização exclusiva do Owner com menos peças conceituais, a confirmar na implementação.
- **Amostra sempre atual ou histórica:** proponho uma aula datada para respeitar a releitura
  somente da view. A experiência entre versões precisa ser julgada pelo Claude e pelo Owner.
- **Todas as métricas da view ou receita primeiro:** proponho receita primeiro; a contagem de
  pedidos tem limitações que a interface não pode resolver somando linhas agregadas.

## 10. Evidência desta preparação

O que segue é **inspeção de arquivos**, não medição operacional. Nenhuma consulta ao banco,
build, instalação ou publicação foi executada. Exemplos históricos da trilha não foram
remedidos e não foram copiados como se fossem resultados atuais.

Comando executado:

```bash
git log -1 --format='%H%n%cs%n%s'
```

Saída literal:

```text
26b58b33deac1ee89b9f7de1292ba40fec0d4de2
2026-10-22
docs: mostra no R24 o caminho do source() até o nome da tabela, com ilustração
```

Comando executado:

```bash
rg -n 'count\(distinct|sum\(f.net_revenue_amount\)|where f.is_realised|group by' dbt/models/consumption/monthly_revenue_by_channel_and_category.sql
```

Saída literal:

```text
21:    count(distinct f.order_id)                      as order_count,
25:    sum(f.net_revenue_amount)                       as net_revenue_amount
30:where f.is_realised
31:group by 1, 2, 3, 4, 5, 6, 7
```

Comando executado:

```bash
rg -n 'round\(quantity \* unit_price, 2\)' dbt/models/trusted/order_items.sql
```

Saída literal:

```text
26:    round(quantity * unit_price, 2)                          as gross_revenue_amount,
28:    round(quantity * unit_price, 2) - discount_amount        as net_revenue_amount,
```

Comando executado:

```bash
rg -n 'for projecao in consulta.selects|resultado\[projecao.alias_or_name\]' src/mvp_ed1/models/sensitivity.py
```

Saída literal:

```text
352:            for projecao in consulta.selects:
353:                resultado[projecao.alias_or_name] = folhas_de(projecao, escopo)
```

Conferência documental executada:

```bash
python3 .claude/skills/revisao/dossie.py --conferir
```

Saída literal:

```text
dossiê completo: sem pendências e sem verificação falhando
```

A mensagem verifica as marcas de preenchimento e de falha reconhecidas pela ferramenta.
As decisões, hipóteses e validações ainda abertas nas seções anteriores continuam pendentes;
esse resultado não é aprovação do plano nem teste de viabilidade da implementação.

## 11. Pedido de parecer ao Claude Code

Avalie este plano contra o código, os ADRs e as escolhas já registradas do Owner. A resposta deve
permitir reduzir o escopo antes de implementar. Em particular:

1. O percurso proposto ensina o fluxo sem esconder filtros, junções e controles relevantes?
2. Qual é a menor experiência convincente para a P01? O que pode ser cortado já?
3. A linhagem existente oferece uma base suficiente? Qual complemento declarativo seria necessário?
4. A separação entre dashboard atualizado e aula histórica preserva a intenção do Owner de forma
   clara? Se não, qual alternativa respeita a atualização somente da view?
5. Qual opção de interface, exportação e hospedagem recomenda, com contrapartidas e decisões que
   cabem ao Owner? Qual registro é necessário para publicar o pacote sintético selecionado?
6. Quais limitações de dados ou agregação afetam o primeiro escopo, e quais podem ser adiadas?
7. Para cada ideia da §7, o parecer é manter, simplificar, adiar ou descartar?
8. Quais validações ainda faltam e qual seria a ordem de execução após as decisões necessárias?

Registre achados abaixo e acrescente o parecer, distinguindo leitura do código, hipótese e
medição. Não marque sugestões deste plano como implementadas ou aprovadas. Ao encerrar a revisão,
preserve as decisões e o plano resultante no destino documental apropriado antes de remover este
arquivo transitório, conforme a skill; não criar agora uma segunda cópia do plano.

## Achados da revisão

Preenchido pelo Claude Code em 22/10/2026, a partir do checkout em `26b58b3` e de sondas somente
leitura no armazém de pé. A base de cada achado vem marcada: **leitura** (do código ou dos
documentos), **medição** (as Mn do [plano](PLAN.md#2-o-que-foi-medido), com as
saídas literais em `data/medicoes/caminho_dos_dados_20261022/`) ou **hipótese**. Nenhuma sugestão
desta proposta foi implementada ou aprovada por esta revisão.

| # | Onde | Achado | Veredito | Situação |
|---|---|---|---|---|
| RP-01 | §1, §4, §6 | A proposta não confronta o [Termo §4](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/Abertura_de_projeto.md#4-fora-do-escopo) e o [Plano §6](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/plano_de_desenvolvimento.md#6-fora-deste-plano): BI, *dashboards* e CI/CD estão fora do escopo do eng_dados, e mudança de escopo passa pela §10 do Termo. **Leitura** | `bloqueante` | Resolvido pela decisão O1 do Owner (22/10/2026): projeto separado, em repositório novo. Impactos no [plano §4](PLAN.md#4-impactos-da-separação) |
| RP-02 | §4.4 | A classificação não é só obstáculo à publicação: a regra da Governança §4 para `confidential` — fora das views abertas ao `analyst` — já não vale hoje. 28 colunas `confidential` em 10 views de `consumption` são lidas pelo `analyst`, porque o *grant* é da camada inteira. **Leitura** do `_consumption__models.yml` e do `dbt_project.yml` | `ajuste` | O Owner decidiu (O2) que nenhum campo sintético é restrito nas análises, e a N8 (22/10/2026) fixou o alcance: classificar não é expor. Registro em ADR no eng_dados — Etapa 1.2 |
| RP-03 | §5.2 | O risco da contagem é real e já se manifesta, mas fora da P01: 126 `order_id` existem nas duas origens; P01 e P02 sem grupo afetado hoje; **P05 e P06 subcontam um pedido num grupo cada**. E 2.479 de 3.292 pedidos têm itens em mais de uma categoria, enquanto a P01 nem declara `order_count` como medida no Glossário. **Medição** M3 e M4 | `ajuste` | `order_count` fora do painel. A correção das quatro views vai para a v1.1.0 do eng_dados (Etapa 1.1), não para o site |
| RP-04 | §3.4 | `ORD-0000037` identifica dois pedidos diferentes — no legado, 2024-12; no varejo, 2025-07 —, e o do varejo é o caso da D65, vendido antes do lançamento. **Medição** M10 | `ajuste` | Item escolhido por critério declarado, depois da correção do dado. A colisão vira gancho da aula da identidade composta |
| RP-05 | §3.1 | "Explicar a cobertura" tem um caso concreto: 2026-09 tem um dia só (`as_of_date`), 3 grupos e R$ 17.795,87 — o gráfico mensal mostraria uma queda que não existe. Há ainda 15 combinações ausentes em meses completos. **Medição** M5 e M6 | `ajuste` | Mês parcial marcado e recorte sem venda dito como tal (Etapa 2.5) |
| RP-06 | §3.1, §3.3 | O eixo de categoria não tem sentido de negócio: a maioria das folhas fica sob raiz sem relação ("Moda › Notebooks"), com o pai atribuído por rodízio; e o preço não tem afinidade com a categoria — faixa única —, embora a Geração de Dados §5 a dê por implementada. A análise por categoria, centro da P01, ensinaria uma comparação sem conteúdo. **Leitura** e **medição** M7 e M8 | `ajuste` | Correção no gerador, na v1.1.0 (O3; Etapas 1.4 a 1.6). A N6 (22/10/2026) decidiu: já, antes de tudo |
| RP-07 | §3.3 | A cautela com a linhagem se confirma, agora medida: o caminho do valor da receita tem 15 nós e 14 arestas até `raw` e `raw_legacy`; `year_month` termina em `dim_date`, gerada, e `category_name` chega ao nome da categoria sem passar pela junção temporal do produto — o pertencimento não aparece; no ramo legado, o `meta.lineage` da ponte salta a limpeza inteira. **Medição** M12 | `observação` | Declaração pequena para pertencimento e controles (plano §3.3; Etapa 3.3) |
| RP-08 | §3.4 | O corte coerente é mais simples do que a proposta supõe: as cinco camadas do percurso estão no mesmo `warehouse_db`, e uma transação `REPEATABLE READ READ ONLY` dá a mesma fotografia em todas. Só a origem transacional fica de fora, e a aula começa no `raw`. **Leitura**; o comportamento na captura real é **hipótese** até a Etapa 3.3 | `observação` | Etapa 3.3 |
| RP-09 | §5.1 | "Decimal como texto com escala preservada" transportaria uma escala que varia por origem: no varejo, desconto com escala de 0 a 2 e preço de 0 a 4; no legado, sempre 2 e 4. **Medição** M11 | `ajuste` | Formatar pela escala declarada. As medidas vão para o Parquet como decimal de escala fixa e o DuckDB soma em decimal exato; rótulo e total vêm do valor exato, e a conversão para ponto flutuante só desenha o gráfico. A aula recebe valores já calculados pelo exportador |
| RP-10 | §4.1–§4.3 | A view inteira tem ~96 kB em texto: o pacote cabe dentro do próprio HTML. Arquivo único resolve de uma vez a mistura de versões por *cache* da §4.3 e abre também como arquivo local, como a trilha. **Medição** M1 | `ajuste` | Superado pela N2 (22/10/2026): com as 16 views no escopo (O5), a publicação atômica do Firebase é que impede a mistura de versões, e o pacote vai em Parquet (M14) |
| RP-11 | §9 | O `manifest.json` está completo hoje — 192 modelos com SQL compilado, gerado em 22/10 17:23Z —, mas qualquer `dbt --select` o regrava parcial. **Medição** e **leitura** do aviso do R29 da trilha | `observação` | O exportador recusa linhagem com problema, como o `lineage.main` já faz (Etapas 1.3 e 3.3) |
| RP-12 | §4.1 | Publicação por GitHub Actions seria CI/CD, fora do escopo do eng_dados; no repositório novo vira escolha nova. O GitHub Pages servindo uma pasta da `main` publica sem *workflow* no repositório. **Leitura** | `observação` | Decidido na N2 (22/10/2026): Firebase Hosting com a esteira do GitHub Actions. No repositório novo, CI/CD é parte do produto (plano §4) |
| RP-13 | §4.4 | Com repositórios separados, o acesso deixa de ser abstrato: o único login do armazém hoje é o superusuário (Governança §7), e copiá-lo para outro repositório é o que um ambiente real não faria. **Leitura** | `ajuste` | Decisões N4 e N5 |
| RP-14 | §3.5, §6 | A correção do dado muda todo valor do armazém: as saídas reais da trilha, datadas, passam a descrever o dado da v1.0.0, e o pacote de recuperação aprovado deixa de representar o estado. **Leitura** | `observação` | A N6 (22/10/2026) decidiu corrigir já; o aviso na trilha é a N7, na rodada 2; a Etapa 1.6 refaz o pacote |
| RP-15 | §4.4 | Com a O2, campos `personal` podem ser publicados. O gerador torna impossível a coincidência com pessoa real no documento (sufixo `SIN`) e no e-mail (`example.com`), mas não no telefone, que sai em formato de celular válido. **Leitura** de `generator/providers.py` | `observação` | No modelo dimensional não há telefone (M16); a ressalva só volta se `trusted` ou `raw` forem publicados (plano §1.3) |

### Parecer do Claude Code

O plano de desenvolvimento que resulta desta revisão está em
[`PLAN.md`](PLAN.md); aqui ficam só as respostas às oito
perguntas da §11.

1. **O percurso ensina sem esconder filtros, junções e controles?** Ensina, desde que as perguntas
   2 e 3 não dependam da linhagem do valor: ela não enxerga o filtro `is_realised`, a data da venda
   convertida para `America/Sao_Paulo`, a junção temporal com o produto nem a limpeza do legado
   (RP-07). Com a declaração pequena da Etapa 3.3, sim.
2. **A menor experiência convincente.** Para a P01, que virou o primeiro corte (O5): o relatório com receita líquida e a tabela com bruta, desconto
   e unidades; três filtros; dois gráficos; mês parcial e recorte vazio tratados; e uma aula de um
   item do varejo, com a pergunta 1 aberta, a 2 a um clique e a 3 em lista curta que aponta para o
   estudo da governança. Corta-se já: `order_count`, filtro de origem, navegação livre, link com
   estado e tudo o que a tabela abaixo adia.
3. **A linhagem basta?** Para o valor, sim — 15 nós e 14 arestas, medidos (M12). O complemento
   declara as junções e o filtro que dão pertencimento, o ponto do arredondamento e os controles. A
   linhagem chega ao projeto novo por uma saída JSON do próprio eng_dados, sem reimplementação.
4. **Painel atualizado e aula histórica.** A separação preserva a intenção, e fica mais simples do
   que parece: o dado do eng_dados só muda por regeneração deliberada. A página compara o total do
   grupo da aula com o do painel e, se divergirem, rotula a aula como histórica, com a data dela.
   Igualdade de totais não é apresentada como prova de que os itens são os mesmos.
5. **Interface, exportação e hospedagem.** Para a P01 sozinha, recomendei HTML sem biblioteca, em
   arquivo único, no GitHub Pages. Com o escopo ampliado pela O5 — todas as views —, a rodada 1
   decidiu (N2): Parquet consultado por DuckDB no navegador, Firebase Hosting em projeto próprio e
   esteira no GitHub Actions, com prévia por PR; exportador em Python com `uv`. Com o acesso por
   perfil (O7), cada relatório é publicado cifrado, e a senha de cada perfil abre só as chaves dos
   seus relatórios (N23). O *framework* é a N3; o acesso ao armazém e à esteira, as N4 e N15. O
   registro necessário é o ADR da O2, com o alcance da N8: classificar não é expor.
6. **Limitações que afetam o primeiro escopo.** Mês parcial (RP-05), contagem de pedidos (RP-03),
   eixo de categoria sem sentido (RP-06), escala por origem (RP-09) e ausência de origem na view.
   Podem esperar: a colisão de identificadores como aula própria e a categoria na venda versus a
   atual.
7. **As ideias da §7** — tabela abaixo.
8. **Validações que faltam e a ordem.** Todas as do plano §9; a ordem está no
   [plano §6.3](PLAN.md#63-ordem-recomendada).

| Ideia da §7 | Parecer | Motivo |
|---|---|---|
| Fórmula que destaca a coluna em cada etapa | Manter | É a pergunta 1; os valores vêm da captura, com o arredondamento onde ele ocorre |
| Antes e depois, com mudanças destacadas | Simplificar | Entrada e saída por etapa, e a etapa que só transporta dita como tal — a captura mostra quais são |
| "Por que esta venda entra?" | Manter | É a pergunta 2; as condições vêm da declaração, não da linhagem |
| Glossário contextual | Simplificar | Link para o Glossário do eng_dados no commit fixado; nenhuma definição paralela |
| Pergunta antes de revelar | Adiar | Depois de o percurso básico passar no critério de aprendizado |
| Link que preserva filtros e etapa | Adiar | Exige carregar a versão do pacote junto |
| Navegação livre por coluna | Adiar | Recria o mapa excessivo que o Owner quer evitar |
| Mesmo campo em `retail` e `legacy` | Adiar | Próxima aula; `ORD-0000037` é o gancho medido (M10) |
| Uma rejeição até a quarentena | Adiar | Aula própria, ligada ao estudo da governança |
| Dependências de controle do legado | Adiar | Pertence ao estudo da governança e à aula do legado |
| Categoria na venda versus a atual | Adiar | Só com caso observado depois da regeneração |
| Comparar duas extrações da P01 | Descartar | O dado é estático entre regenerações, e o histórico do pacote no Git já mostra a diferença |
| Evidência de qualidade junto da etapa | Simplificar | O nome e o link do teste que guarda a etapa, sem afirmar que passou nesta extração |
| Simular pedidos não realizados | Descartar | Muda a pergunta e exige dado que o consumo não oferece |
