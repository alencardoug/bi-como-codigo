# Plano — bi-como-codigo e o estudo

> **O que vive aqui:** o plano dos dois conteúdos novos — a vitrine `bi-como-codigo` e o estudo — e
> da versão de manutenção do eng_dados que eles pedem: o que se constrói, a arquitetura, os impactos
> da separação, as etapas com o esforço de cada uma, as decisões do Owner, tomadas e pendentes, e o
> que foi medido para sustentar tudo isso.
>
> **O que não vive aqui:** a proposta original do Codex e a crítica a ela (ver
> [`REVIEW.md`](REVIEW.md): §§1–11 e os achados RP-01 a RP-15); o que o eng_dados é e como se
> opera (ver [README](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/README.md) e [Execução Local](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md)); as decisões, depois de
> registradas — elas viram ADR no repositório dono.

| Campo | Informação |
|---|---|
| Data | 22/10/2026 — revisão 5: todas as decisões tomadas; pronta para a revisão do Codex |
| Autor | Claude Code, a pedido do Owner |
| Base | eng_dados em `26b58b3`, sem alteração além deste arquivo e do `REVIEW.md` |
| Situação | **Proposta completa.** Nada implementado. Todas as decisões do Owner tomadas (§1.2); falta a revisão do Codex (§10) |
| Natureza | Transitório, fora do Git e do mapa do README. Na Etapa 2.1, as §§ comuns e a Parte II vão para o `bi-como-codigo` como plano de fundação, junto com o `REVIEW.md`; na 3.2, a Parte III vai para o `caderno-de-dados`; a Parte I vira ADR e pendência no eng_dados |
| Evidência | `data/medicoes/caminho_dos_dados_20261022/` (fora do Git): sondas SQL somente leitura, protótipo de linhagem, exportação para Parquet, medição do motor DuckDB, cobertura do catálogo, as saídas literais e o `ro.sh` que reexecuta as sondas |

---

## 1. O que já está decidido

### 1.1 Pelo Owner, na conversa de 22/10/2026

As escolhas da conversa com o Codex continuam valendo
([`REVIEW.md` §1](REVIEW.md#1-o-pedido-e-as-escolhas-já-feitas)), redistribuídas pela O6: a P01
é o primeiro relatório da vitrine e a primeira aula do estudo.

| # | Decisão |
|---|---|
| **O1** | Projeto **separado, em repositório novo**. O eng_dados está concluído, e a exclusão de BI e *dashboards* do Termo §4 vale para ele e continua valendo |
| **O2** | **Nenhum campo sintético é restrito nas análises**: todos podem — e devem — aparecer |
| **O3** | Se houver valor, **corrigir o dado sintético** que hoje é incoerente |
| **O4** | **Estudo aprofundado da governança**: como está feita, que valor tem e como usá-la no projeto |
| **O5** | O projeto **cresce para todas as views e análises** do eng_dados. A tese: relatórios tão ricos quanto os do Power BI, ou melhores, **sem licença**, e sem levar o banco inteiro |
| **O6** | **Dois conteúdos.** A **vitrine** (`bi-como-codigo`) exibe capacidade técnica: produto robusto e resumido, apresentação executiva que dispensa orador; a governança do projeto; e, principalmente, a governança de dados, contada como um **portal de leitura** — "acabei de chegar neste banco e quero entender tudo o que tem aqui" —, organizado e instigante, para que quem consulta aprenda rápido e reconheça um projeto bem governado. A governança pode ser reavaliada e refinada. O **estudo** é o aprendizado: explorações, o caminho das views até a origem, entender a governança e o projeto |
| **O7** | **Login e exibição segregada por login** na vitrine: dois logins, um deles com acesso a um único relatório que faça sentido na história, para mostrar **mínimo privilégio**. Implementação simples, direto no código; sem mais logins e sem tela de gestão |

### 1.2 As decisões, nas quatro rodadas

| # | Pergunta | Escolha |
|---|---|---|
| **N1** | Nome da vitrine | **`bi-como-codigo`** |
| **N2** | Dado, consulta e publicação | **Parquet consultado por DuckDB no navegador; Firebase Hosting em projeto próprio; GitHub Actions publica no *merge* e gera prévia por PR; o motor do DuckDB vem do jsDelivr** |
| **N6** | Quando corrigir o dado sintético | **Já, antes de tudo** |
| **N8** | Alcance do ADR da O2 | **Classificar não é expor**: a classificação continua — metadado e base das *policy tags* da Etapa 13 —, e a exposição de dado sintético fica livre. Reescreve a regra da [Governança §4](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#4-classificação-de-sensibilidade) e resolve a divergência de hoje (RP-02) |
| **N17** | Como organizar os dois conteúdos | **Dois repositórios, dois sites**; o estudo lê os dados que a vitrine publica e tem a própria captura para as aulas |
| **N18** | Onde fica o estudo | **Privado no claude.ai, desde que nada fique limitado; se algum recurso for limitado, um `*.web.app`.** A sonda da Etapa 3.1 decide |
| **N20** | Quando refinar a governança | **Na v1.1.0**, em etapa própria, separada da regeneração |
| **N14** | D62, D63 e D64 na v1.1.0 | **Não** — continuam pendências próprias |
| **N23** | Como implementar o acesso por perfil (O7) | **A senha vira chave**: cada relatório é cifrado na publicação, e a senha fixa de cada perfil abre só as chaves dos seus relatórios — sem conta, sem Firebase Authentication, sem Firestore |
| **N22** | As senhas aparecem para quem visita? | **As duas, abaixo da caixa de login**, com o texto da §3.2; acima da caixa, uma explicação do que é a página e o produto |
| **N4** | Com que login o exportador lê as views | **Login só de leitura**, membro de `analyst`, criado pelo eng_dados na v1.1.0 |
| **N16** | O modelo dimensional na vitrine | **Só as 16 views, por ora**: o contrato de consumo fica intacto, e o detalhe, quando um relatório pedir, vem com ADR no eng_dados |
| **N7** | A trilha depois da regeneração | **Aviso no topo**: as saídas reais foram medidas no dado da v1.0.0. Entra só junto da próxima atualização da trilha, nunca sozinho |
| **N21** | Nome do repositório de estudo | **`caderno-de-dados`** |
| **N3** | *Framework* dos relatórios e do portal | **Protótipo comparativo na P01** — Evidence contra construção própria com DuckDB-WASM e uma biblioteca de gráficos —, e a escolha depois dele (Etapa 2.3) |
| **N15** | Autenticação da esteira no Firebase | **Federação de identidade** do GitHub com o Google Cloud, sem chave guardada |
| **N10** | O relógio de estudo conta o `caderno-de-dados` | **Sim** |
| **N12** | A vitrine no portfólio | **Link na página do projeto A** |

### 1.3 Consequências

- A N2 resolve a antiga N13: atualizar a vitrine é abrir um PR com o pacote novo (§3.4). E substitui
  o desenho de arquivo único da revisão 1 (RP-10).
- Com a N23, a O7 não acrescenta componente: o Hosting continua servindo tudo, e os relatórios vão
  cifrados (§3.2). O estudo lê os relatórios da vitrine pela URL e os abre com a senha da Diretoria
  (§3.3); a sonda da 3.1 testa a WebCrypto dentro do Artifact.
- A O6 resolve a antiga N9: o estudo da governança fica no conteúdo de estudo; a vitrine tem o
  portal de leitura.
- Com a N2, a vitrine fica num projeto Firebase próprio; se a sonda mandar o estudo para um
  `*.web.app`, ele ganha o seu, pelo mesmo motivo — cota não compartilhada. A antiga N19 não precisa
  de pergunta.
- A N6 e a N20 põem a Parte I na frente da fila.
- A N16 deixa o modelo dimensional fora por ora: a Etapa 2.12 só existe se um relatório pedir
  detalhe.
- No modelo dimensional, os campos `personal` são nome, documento com sufixo `SIN`, data de
  nascimento e e-mail em `example.com` — nenhum telefone (M16). A ressalva do telefone (RP-15) só
  volta se `trusted` ou `raw` forem publicados.

---

## 2. O que foi medido

Leitura em sessão `default_transaction_read_only=on` no armazém de pé, entre 23/10/2026 00:12Z e
01:22Z (22/10, 21:12 a 22:22 em Brasília), sobre o commit `26b58b3`. A view foi lida como
`analyst`; as camadas internas, pelo superusuário na mesma sessão somente leitura; os arquivos, sem
banco. Saídas literais na pasta de evidência.

| # | O quê | Resultado | Consequência |
|---|---|---|---|
| M1 | A view P01 | 1.140 linhas; 33 meses (2024-01 a 2026-09); 3 canais; 4 categorias-raiz e 12 folhas; R$ 33.076.529,47 de receita líquida; ~96 kB em texto | — |
| M2 | A P01 recalculada a partir da fato, no mesmo grão | 0 linhas divergentes em contagem e receita | Oráculo pronto para o exportador |
| M3 | Contagem de pedidos sem `source_system` | 126 `order_id` existem nas duas origens. P01 e P02: nenhum grupo afetado hoje. **P05 e P06 subcontam um pedido num grupo cada**: P06 2025-07 · Aplicativo · Eletrônicos (11 × 12); P05 2024-T4 · Aplicativo · SP (20 × 21) | Defeito real no datamart, contra a regra da macro `empilhado` — "a origem entra na condição junto com a chave, sempre". Nenhum teste o pega |
| M4 | Pedidos realizados com itens em mais de uma categoria | 2.479 de 3.292 | `order_count` da P01 não se soma entre categorias, e a P01 nem a declara como medida no [Glossário](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/glossario_de_negocio/perguntas_de_negocio.md#p01--qual-a-receita-líquida-por-mês-canal-e-categoria-de-produto) |
| M5 | Cobertura | primeira venda realizada em 2024-01-02, última em 2026-09-01 (`as_of_date`). 2026-09 tem 3 grupos, 9 unidades e R$ 17.795,87; os outros meses, de R$ 0,65 mi a R$ 2,07 mi | 2026-09 é um mês de um dia: o gráfico mensal mostraria uma queda que não existe |
| M6 | Combinações mês × canal × categoria sem linha | 15 em meses completos; 33 em 2026-09 | Recorte sem venda, distinto de zero |
| M7 | Árvore de categorias | a maioria das folhas fica sob raiz sem relação: "Moda › Notebooks", "Moda › Sofás", "Eletrônicos › Panelas", "Eletrônicos › Camisetas", "Casa e Cozinha › Calças". O pai é atribuído por rodízio (`generator/domains/catalogo.py`) | O eixo principal da P01 não tem sentido de negócio |
| M8 | Preço por categoria, no varejo | média de R$ 1.970 (Caixas de som) a R$ 2.930 (Organizadores), faixas sobrepostas de R$ 63 a R$ 6.939. O preço-base sai de uma faixa única para todo produto (`geracao.yml`: `faixa_de_preco: [9.90, 4800.00]`) | Contraria a [Geração de Dados §5](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/geracao_de_dados.md#5-realismo-e-coerência), que dá por implementada a afinidade entre produto, categoria e preço |
| M9 | Venda antes do lançamento (D65) | 3.130 de 7.500 itens do varejo — o mesmo número de 04/10 | Continua aberto |
| M10 | `ORD-0000037` | dois pedidos diferentes com o mesmo número: no legado, 2024-12-09, Eletrônicos; no varejo, 2025-07-01, Moda e Eletrônicos — este é o caso citado na D65 | Mau exemplo para a primeira aula; bom gancho para a aula da identidade composta |
| M11 | Escala decimal em `trusted.order_items` | varejo: desconto com escala de 0 a 2 e preço de 0 a 4; legado: sempre 2 e 4 | Formatar pela escala declarada, nunca pelo texto que o banco devolve |
| M12 | Linhagem por coluna — protótipo que percorre `Lineage.leaves`, sem reimplementar nada | `net_revenue_amount`: 15 nós e 14 arestas até `raw` e `raw_legacy`, 0 problemas, *manifest* completo (192 modelos), 20 a 30 s. `year_month` termina em `dim_date` (gerada); `category_name` vai ao nome em `raw.product_categories` sem passar pela junção temporal do produto; o ramo legado salta de `raw_legacy.order_items` direto para `legado__order_items` | A linhagem do valor responde "de onde vem o valor". Pertencimento e controles precisam de uma declaração pequena |
| M13 | Tamanho do armazém | **588 MB** no banco inteiro: `raw_legacy` 206 MB, `trusted` 138 MB, `raw` 86 MB, `quarantine` 77 MB, `analytics` 50 MB, `staging` 8 MB, o resto abaixo de 1 MB; `consumption` são views | O grosso é o que fica antes do produto: levar o banco não faz sentido |
| M14 | O produto analítico em Parquet (zstd) | 25 tabelas do `analytics` e 16 views: 162.351 linhas, **8,10 MiB**. Só as views: 15.377 linhas, 0,23 MiB; a maior, `inventory_turnover_by_sku_and_warehouse`, 77 KiB. A maior tabela, `fact_cart_event`: 81.199 linhas, 3,4 MiB. Exportação em 4,0 s | Cabe em arquivos no próprio site, cifrado por relatório |
| M15 | Motor DuckDB-WASM 1.32.0, de 16/12/2025 — a última estável no npm | **6,8 MB** baixados com brotli, 7,6 MB com gzip e 34,2 MB sem compressão, estáveis em três leituras. A primeira leitura deu 5,2 MB, de outro nó do CDN — não explicada | Servido pelo Firebase gratuito, a cota de 360 MB/dia aguentaria ~50 primeiros acessos por dia. Por isso o motor vem do jsDelivr |
| M16 | Campos `personal` no `analytics` | 9 colunas: nome, sobrenome, nome completo, documento e nascimento em `dim_customer`; nome, sobrenome, nome completo e e-mail em `dim_support_agent`. Nenhum telefone | A ressalva do telefone não se aplica ao modelo dimensional |
| M17 | Cobertura do catálogo, no *manifest* | Classificação, linhagem, acesso e retenção completos; 700 testes de dados. **Descrição de coluna**: `analytics` 26 de 477, `consumption` 31 de 188, `trusted` 56 de 1.069, `staging` 659 de 1.114, `raw` e `raw_legacy` 0 de 1.161. **`domain` e `owner`**: 0 dos 41 objetos de `analytics` e `consumption`, embora a [Governança §5.1](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#51-padrão-de-metadados) os exija em todo modelo | Um portal de leitura com descrição em branco desmente o que exibe; a regra da §5.1 não é cumprida hoje |
| M18 | Descrição herdável pela linhagem — estimativa | As 418 colunas da origem têm descrição declarada nos modelos SQLAlchemy. Sem descrição e com uma única folha de mesmo nome: 357 em `analytics`, 113 em `consumption`, 198 em `trusted`. Pedem texto — folha renomeada, várias folhas ou nenhuma —: 94 em `analytics`, 44 em `consumption`; em `trusted`, 815, a maior parte porque o `union` das duas origens aparece como duas folhas de mesmo nome | O mecanismo que já deriva a classificação pode derivar a descrição; o texto escrito fica para as colunas calculadas. Mesmo nome não garante mesmo significado: é estimativa |

**Lido nas fontes oficiais em 22/10/2026 — não medido:**

| Fonte | O que diz |
|---|---|
| [Firebase](https://firebase.google.com/pricing), plano Spark | Hosting: 10 GB de armazenamento e 360 MB/dia de transferência; no Blaze, US$ 0,026/GB e US$ 0,15/GB além disso. O que acontece ao estourar no Spark, a página não diz |
| [Firestore](https://firebase.google.com/docs/firestore/quotas), cota gratuita | 1 GiB armazenado; 50 mil leituras, 20 mil gravações e 20 mil exclusões por dia; 10 GiB/mês de saída; documento de até 1 MiB |
| [Cloud Storage do Firebase](https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024) | Exige o plano Blaze, inclusive o *bucket* padrão; no Spark, as chamadas respondem 402 ou 403 |
| [Firebase Authentication](https://firebase.google.com/docs/auth/flutter/manage-users) | O usuário autenticado pode trocar a própria senha e excluir a própria conta pelo SDK do cliente; essas ações exigem *login* recente |
| [Neon](https://neon.com/pricing), plano Free | 1 GB por projeto; 100 CU-horas; suspende após 5 min ocioso; 5 GB/mês de transferência pública — estourou, a computação fica suspensa até o período seguinte |
| [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) | Site publicado até 1 GB; 100 GB/mês de banda, limite brando |
| API do GitHub | Evidence: versão de 06/02/2026 e último *push* em 22/10/2026, MIT. Observable Framework: versão de 02/03/2026 e último *push* em 15/05/2026, ISC. DuckDB-WASM: último *push* em 22/10/2026, MIT |

**Não medido:** tempo de montagem dos sites; comportamento de qualquer *framework* com estes dados;
o DuckDB e a WebCrypto dentro do Artifact do claude.ai; o tempo de abrir as chaves no navegador;
usabilidade; o efeito das correções sobre os testes do eng_dados.

---

## 3. O que se constrói

### 3.1 Os dois conteúdos

| | **Vitrine — `bi-como-codigo`** | **Estudo — `caderno-de-dados`** |
|---|---|---|
| Para quem | Quem avalia o seu trabalho, em minutos, sem você presente | Você |
| Tom | Apresentação executiva autossuficiente | Exploração, laboratório, dúvida |
| Conteúdo | Visão geral; relatórios das 16 perguntas, com acesso por perfil; portal de leitura da governança de dados; governança do projeto | Aulas da view até a origem; estudo da governança; explorações em SQL; ligação com a trilha |
| Dados | Parquet das 16 views, cifrado por relatório; metadados de governança públicos, gerados do eng_dados | Os relatórios da vitrine, lidos pela URL e abertos com a senha da Diretoria; captura própria para as aulas |
| Onde | Firebase Hosting, num projeto próprio (N2) | Artifact privado no claude.ai ou `*.web.app`, pela sonda da 3.1 (N18) |

### 3.2 A vitrine

**Princípios.** Cada página se explica sozinha, sem orador e sem jargão que não leve ao glossário.
Todo número sai de um registro do eng_dados num commit fixado, com data — nenhum é digitado (P5).
Narrativa primeiro, referência depois: quem tem dois minutos lê a história; quem tem vinte, desce
ao catálogo. Navegação por abas e links, sempre com caminho de volta; busca no catálogo;
acessibilidade e tela estreita.

- **Visão geral.** O projeto em uma página: o que é, a arquitetura numa imagem, os números que
  provam a robustez e três portas — relatórios, governança de dados, como foi feito.
- **Relatórios — BI como código.** As 16 perguntas, cada uma um arquivo de texto revisável com a
  consulta e a apresentação; filtros, cruzamentos, gráficos e tabela no navegador. A P01 primeiro.
  Regras fixadas pela revisão: mês parcial marcado (M5); recorte sem venda dito como tal (M6);
  `order_count` nunca somado entre categorias (M4); razão reagregada só por numerador e
  denominador; nenhum filtro que a view não ofereça; nenhuma métrica redefinida no relatório.
- **Acesso por perfil (O7, N23).** Esconder um relatório no JavaScript não é controle de acesso: o
  arquivo continuaria baixável pela URL, e quem avalia vê isso na aba de rede. E uma conta no
  Firebase Authentication não deixa a senha imutável: o visitante logado pode trocá-la ou excluir a
  conta (§2). Por isso **a senha vira chave**:
  - dois perfis, declarados uma vez no código: **Diretoria**, que abre os 16 relatórios, e
    **Logística**, que abre só a **P13** — entrega no prazo por transportadora. Quem cuida de
    transportadora não precisa de receita, margem nem pagamento;
  - na publicação, a esteira cifra o Parquet de cada relatório com uma chave só dele (AES-GCM, vetor
    de inicialização aleatório por arquivo). A senha de cada perfil gera, por PBKDF2 com sal
    próprio, a chave que embrulha só as chaves dos relatórios daquele perfil (AES-KW). É a
    criptografia de envelope com vários destinatários, a mesma ideia do SOPS e do age;
  - no navegador, a WebCrypto refaz a chave a partir da senha, desembrulha as chaves a que o perfil
    tem direito e decifra só esses relatórios. Senha errada não abre nada;
  - a senha é imutável de fato: não há conta para trocar nem excluir, e ela só muda numa publicação
    nova, por PR seu;
  - a tela de login tem, **acima** da caixa, uma explicação do que é a página e o produto e,
    **abaixo**, as credenciais (N22), geradas da mesma declaração dos perfis:

    ```text
    Para acessar, use:
    Login: Diretoria
    Senha: senha_complexa_123
    ou
    Login: Logística
    Senha: complexa_senha_321
    ```

  - visão geral, portal e governança do projeto continuam abertos, sem login;
  - a prova é por execução, como o `test_acesso` do eng_dados: a montagem confere que a senha da
    Logística abre a P13 e falha nas outras quinze, que a da Diretoria abre todas e que nenhum
    Parquet vai em claro para o Hosting. Na vitrine, a Logística é convidada a abrir outro relatório
    e vê que a chave dela não o abre.
- **Portal de leitura da governança de dados.** Gerado das declarações do eng_dados — *manifest*,
  YAMLs, glossário, ADRs, linhagem —, com a narrativa curada em capítulos:

  | Capítulo | O que responde |
  |---|---|
  | 1. Comece aqui | Que banco é este, as duas origens, as nove camadas numa imagem, por onde seguir |
  | 2. O mapa | Cada camada: para que existe, quem escreve, quem lê, quanto tempo guarda, quantos objetos |
  | 3. O catálogo | Cada objeto e coluna: descrição, domínio, dono, grão, tipo, classificação, testes que o guardam, linhagem de entrada e saída, perguntas que o usam |
  | 4. As perguntas de negócio | Pergunta → view → medidas e aditividade → fato e dimensões → relatório |
  | 5. O vocabulário | Glossário de negócio e técnico |
  | 6. Quem vê o quê | Classificação por camada, papéis × camadas no armazém, a prova por execução, classificar não é expor — e o mesmo mínimo privilégio aplicado na própria vitrine |
  | 7. De onde vem cada número | Linhagem por coluna até a origem, com as travessias fora do dbt — um salto por vez, nunca o grafo inteiro |
  | 8. Por que confiar | Testes por camada, reconciliação em toda fronteira, invariantes, quarentena com motivo, certificação de captura |
  | 9. Como isto é mantido | Catálogo como código: tudo aqui é gerado das declarações, e o `make check` impede que divirjam |

- **Governança do projeto.** Princípios P1–P10; as decisões em ADR, em linha do tempo e com busca;
  a revisão por um segundo agente, rodada a rodada, até não restar achado; a definição de pronto; o
  mapa documental com um dono por assunto; riscos e tratamentos; marcos; o ciclo do zero medido e o
  ponto de recuperação. Gerada dos documentos e do histórico do eng_dados.

### 3.3 O estudo

- **Aulas, começando pela P01.** Um item escolhido por critério declarado — varejo, realizado, com
  desconto, quantidade maior que um e arredondamento visível —, capturado num corte único: `raw`,
  `staging`, `trusted`, `analytics` e `consumption` estão todos no `warehouse_db`, e uma transação
  `REPEATABLE READ READ ONLY` dá a mesma fotografia em todas. A aula começa no `raw`. As três
  perguntas da [`REVIEW.md` §3.2](REVIEW.md#32-percurso-didático-com-abertura-progressiva)
  organizam o percurso, com valor do item, demais itens e total do grupo.
- **Estudo da governança (O4).** Para cada mecanismo do eng_dados: como está feito, que valor tem —
  com o incidente real que ele pegou ou evita —, como usar e o que ele não cobre, com laboratórios
  executados de verdade. Três incidentes já conferidos por leitura: o *grant* dado à mão ao
  `analyst` em `trusted`, revogado na execução seguinte
  ([Governança §7](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#7-regras-de-acesso-por-camada)); a P11, que passou no
  `dbt build` e falhava na primeira leitura (`tests/test_consumo.py`); o `unique` de `dim_customer`
  quebrado na primeira carga com legado (`dbt/tests/legado_nao_colide_com_a_origem_principal.sql`).
- **Explorações.** SQL livre, com o DuckDB no navegador, sobre os relatórios da vitrine abertos com
  a senha da Diretoria; e as próximas aulas candidatas — a identidade composta (M10) e uma rejeição
  até a quarentena.
- **A trilha** continua no eng_dados, como está; o estudo aponta para ela.

### 3.4 A arquitetura

```text
eng_dados, na sua máquina       bi-como-codigo (GitHub)                    Firebase Hosting           navegador
warehouse_db ─exportador─▶ Parquet + manifesto ─PR─▶ Actions: confere, ─▶ prévia do PR
repositório ──exportador─▶ metadados (JSON)          cifra e monta  └merge─▶ app, páginas e    ─▶ senha → chave,
                                                                             relatórios cifrados    DuckDB-WASM
estudo (GitHub) ── aulas e captura própria ──▶ Artifact ou *.web.app ◀── URL + senha da Diretoria
```

- Os exportadores rodam só na sua máquina: o armazém nunca fica acessível pela internet, e a esteira
  nunca o lê.
- O **manifesto** acompanha os Parquet: contagem de linhas, soma de cada medida e *hash* de cada
  arquivo, a versão do eng_dados e a hora da leitura. A esteira recusa o pacote cujo manifesto não
  confere, e então nada é publicado — a versão no ar continua.
- **Atualizar é abrir um PR** com o pacote novo: a prévia mostra o resultado, o diff do manifesto
  mostra o que mudou, e o *merge* publica.
- A esteira cifra cada relatório antes de montar; nenhum Parquet vai em claro para o Hosting — a
  montagem confere isso, e falha se encontrar um.

### 3.5 O contrato com o eng_dados

Todo cruzamento entre os repositórios é explícito e versionado.

| O que se usa | Como | Por quê |
|---|---|---|
| As 16 views | Lidas por um login que é membro de `analyst` (N4) | O próprio banco garante que o exportador só lê consumo |
| O modelo dimensional | Fora por ora (N16); se um relatório pedir detalhe, por contrato de consumo, com ADR no eng_dados | A [Governança §7](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/governanca_de_dados.md#7-regras-de-acesso-por-camada) e o [ADR-0008](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0008-schemas-do-armazem.md) não deixam consumidor ler `analytics`, e o [ADR-0018](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/adr/0018-fatos-e-views-a-partir-de-perguntas-de-negocio.md) recusou "uma view por fato" |
| Metadados de governança | Lidos do repositório num commit fixado — *manifest*, YAMLs, glossário, ADRs, documentos —, sem acesso ao dado | O portal é derivado, não escrito; o que mudar no eng_dados muda no portal na exportação seguinte |
| O contrato das views | Colunas e tipos conferidos contra o *manifest* antes de exportar | Mudança de contrato no eng_dados falha alto, em vez de virar número errado |
| Linhagem por coluna | `python -m mvp_ed1.models.lineage --json`, rodado com o `.venv` do eng_dados (Etapa 1.3) | Nem segunda declaração da linhagem, nem dependência de código interno |
| Trechos de SQL e documentos | Âncora textual por arquivo, lida com `git show <commit>:<caminho>` num commit fixado; link para o GitHub nesse commit | Trecho que sumiu quebra a montagem; link não apodrece |
| Captura das aulas | Pelo custodiante: superusuário, transação somente leitura `REPEATABLE READ`, comando explícito e raro | É o padrão de leitura de estudo que o eng_dados já usa (`make pgcli-*`); nenhum papel novo |
| Versão | Commit do eng_dados, `generated_at` do *manifest*, hora da leitura | "Este armazém foi construído por este commit" não tem evidência hoje: fica marcado como não verificado |

---

## 4. Impactos da separação

| Aspecto | Impacto | Tratamento |
|---|---|---|
| Escopo do eng_dados | Nenhum: ele continua concluído, e BI continua fora dele | Objetivo, escopo e fora do escopo no README de cada repositório novo |
| Correções e refinamentos no eng_dados | A separação não os dispensa: o gerador, as views e as declarações de governança moram lá. O projeto concluído reabre para uma **versão de manutenção v1.1.0**, com aceite e *tag* próprios | Parte I |
| Acesso ao armazém | O único login de hoje é o superusuário (Governança §7). Copiar essa senha para outro repositório é o que um ambiente real não faria | Login dedicado membro de `analyst` (N4) — o "passo seguinte" que a própria §7 já declara |
| Acesso à vitrine | Nenhum componente novo: a cifra é feita na esteira e aberta no navegador pela WebCrypto (N23). Firebase Authentication e Firestore ficaram de fora | Etapa 2.6; ADR no `bi-como-codigo` |
| Ambiente | Exportar exige só os bancos do eng_dados de pé (`make up`) | — |
| Governança | A política do eng_dados continua dona do dado publicado; cada repositório novo declara o que publica e cita o ADR | Etapa 1.2 |
| CI/CD | Fora do escopo do eng_dados (Termo §4); parte do produto na vitrine | Etapa 2.2, com federação de identidade, sem chave guardada (N15) |
| Hospedagem | Vitrine decidida (N2), com cota de 360 MB/dia. Estudo pela sonda da 3.1 | Motor pelo jsDelivr; cada página carrega só os seus arquivos; projetos Firebase separados |
| Segredos | Cada repositório novo precisa da própria guarda. O `secrets_review` do eng_dados conhece as chaves do `.env` de lá. As duas senhas de demonstração são públicas por desenho (N22) e não são segredo: entram num registro com o motivo, como o `segredos_tratados.yml` do eng_dados, para a guarda não acusá-las | Etapas 2.1 e 3.2 |
| Convenções e *skills* | `CLAUDE.md` e `AGENTS.md` não vêm sozinhos. A *skill* `revisao` foi escrita para ser portátil — só o `comandos.txt` muda —; a `adr` aponta caminhos do eng_dados | Etapas 2.1 e 3.2 |
| Memória do Claude Code | É por pasta: cada repositório novo começa sem nenhuma | Convenções no `CLAUDE.md` de cada um; preferências de trabalho em memórias novas |
| Relógio de estudo | O gancho do bash só registra comandos dentro do eng_dados; no Artifact, o relógio já funciona pela capacidade de banco | O gancho e o coletor passam a cobrir o `caderno-de-dados` (N10; Etapa 3.8) |
| Trilha de estudo | Fica no eng_dados. Com a N6, as saídas reais dela passam a descrever o dado da v1.0.0 | Aviso no topo (N7), junto da próxima atualização da trilha — local e Artifact —, nunca sozinho |
| Portfólio | A vitrine é a peça de portfólio | Link na página do projeto A (N12), na Etapa 2.10 |
| Este plano e o `REVIEW.md` | Soltos na raiz do eng_dados, fora do Git | Vão para os repositórios novos e saem daqui |

---

## 5. Parte I — a versão de manutenção v1.1.0 do eng_dados

Primeira na fila (N6, N20).

### 5.1 Contagem de pedidos com a origem

`count(distinct (source_system, order_id))` nas views P01, P02, P05 e P06, uma varredura das
demais contagens e junções por identificador sem a origem, e um teste que falha quando o consumo
conta identificador sem ela. **Valor:** corrige os dois grupos errados de hoje (M3) e fecha a
classe do defeito. **Custo:** pequeno; os tipos do contrato não mudam. É correção — o comportamento
passa a ser o que a regra já escrita manda.

### 5.2 ADR da O2, linhagem em JSON e login do exportador

O ADR que separa classificar de expor (N8). O `--json` no módulo de linhagem: folhas imediatas e
origens terminais por coluna. Com a N4, `governance.garantir()` passa a
criar um login membro de `analyst`, com senha no `.env`, e o `test_acesso` ganha a prova de que ele
lê `consumption` e nada além.

### 5.3 Realismo do dado sintético (O3, N6)

| Correção, no gerador | Valor | O que muda |
|---|---|---|
| Árvore de categorias declarada — folha, meio e raiz coerentes, ainda equilibrada | O eixo da P01 passa a ter sentido de negócio (M7) | Nomes e pais das categorias |
| Faixa de preço por categoria | A comparação de receita entre categorias passa a contar algo; fecha a divergência entre a Geração §5 e o código (M8) | Todo valor monetário do armazém |
| Lançamento antes da venda, com a invariante 14 | Fecha a D65 (M9) | Datas de lançamento ou de venda; histórico SCD do produto |

**Custo:** a regeneração da [Execução Local §3.2](https://github.com/alencardoug/mvp_eng_dados_1/blob/26b58b3/docs/execucao_local.md#32-regerar-uma-origem-que-já-alimenta-streaming)
— manutenção destrutiva, com o `FORCE=1` próprio do procedimento —, o legado regenerado pelo mesmo
motor e capturado de novo, `dbt build` e `make check`, o *streaming* refeito, o pacote de
recuperação refeito (o aprovado deixa de representar o estado) e os documentos que citam números.
**Efeitos laterais:** as saídas reais da trilha passam a descrever o dado da v1.0.0, e o aviso no
topo entra na próxima atualização dela (N7);
`ORD-0000037` muda de conteúdo; a cópia da trilha no Artifact também.

### 5.4 Refinamento da governança de dados (O6, N20)

- **Descrição derivada pela linhagem**, pelo mesmo mecanismo que já deriva a classificação: a
  declaração continua nos modelos SQLAlchemy da origem — as 418 colunas já descritas —, e a coluna
  que só transporta herda o texto. Quem discorda do herdado escreve a descrição à mão com o motivo,
  como o `sensitivity_reason` já faz. A catraca da classificação ganha uma irmã: coluna sem
  descrição falha o `make check`.
- **Texto escrito para as colunas calculadas** — chaves, medidas, flags e colunas renomeadas —,
  começando por `analytics` e `consumption` (M18). É declaração: revisão integral sua.
- **`domain` e `owner`** nos 41 objetos que não os têm, como a §5.1 já exige (M17).
- Os ajustes que o portal revelar entram aqui, na declaração — nunca no derivado.

### 5.5 Fora da v1.1.0

D62, D63 e D64 (N14). O contrato de consumo do modelo dimensional (N16). Onde
a v1.1.0 fica registrada no eng_dados — o plano dele termina na Etapa 13 — se decide no roteiro da
Etapa 1.4.

---

## 6. Etapas e esforço

### 6.1 Como ler o esforço

**Esforço** é o nível do `/effort` recomendado para o Claude Code em cada etapa — troque na
fronteira entre etapas. **Tamanho** é estimativa, não medição: serve para ordenar o trabalho, não
para prometer prazo.

| Esforço | Quando |
|---|---|
| `low` | Nenhuma etapa deste plano: todas tocam dado, governança, acesso ou publicação |
| `medium` | Especificação fechada e risco contido: fundar repositório, sondar, publicar |
| `high` | Desenvolvimento com testes e risco semântico ou de segurança moderado |
| `xhigh` | Semântica sutil, em que o erro parece certo, ou texto que vai representar o projeto: o roteiro da regeneração, a cifra por perfil, as descrições, a visão geral, o portal, a aula, a redação da governança |
| `max` | Operação longa e destrutiva na máquina, com muitos modos de falha. O ciclo comparável, o do B5, achou oito desvios |

| Tamanho | Estimativa |
|---|---|
| P | Uma sessão |
| M | Uma a duas sessões cheias |
| G | Várias sessões, com pausas para decisão ou revisão |

### 6.2 As etapas

**Parte I — eng_dados v1.1.0**

| Etapa | Entrega | Esforço | Tamanho | Depende de | Critério para avançar |
|---|---|---|---|---|---|
| **1.1** | Contagem de pedidos com a origem (§5.1) | `high` | P | — | O teste novo falha antes da correção e passa depois; M3 refeito dá zero; `make check` verde |
| **1.2** | ADR da O2 (N8) | `high` | P | — | `verificar.py` sem pendência órfã; `make check-offline` verde |
| **1.3** | Linhagem em JSON e o login só de leitura do exportador (N4) | `high` | P | — | A saída contém as 14 arestas da M12; o login lê `consumption` e é recusado nas outras camadas; `make check` verde |
| **1.4** | Roteiro da correção do dado: estado de partida, passos, oráculos, recuo — revisado pelo Codex | `xhigh` | M | — | Codex sem bloqueante |
| **1.5** | As três correções no gerador, a invariante 14 e os testes que não precisam de banco | `high` | M | 1.4 | Geração em memória determinística; M7–M9 refeitos sobre ela; `make check-offline` verde |
| **1.6** | Regeneração e ciclo completo na máquina | `max` | G | 1.5 e autorização do Owner | `make check` verde, com a diferença de contagens explicada; captura legada certificada; reconciliações; pacote de recuperação refeito e conferido; M3 e M7–M9 refeitos no armazém |
| **1.7** | Descrição derivada pela linhagem e a catraca de descrição (§5.4) | `high` | M | — | Contraprova: coluna de transporte sem texto herda, coluna calculada sem texto falha; `make check` verde |
| **1.8** | Texto das colunas calculadas; `domain` e `owner` nos 41 objetos | `xhigh` | M | 1.7 | Catraca de descrição em 100% em `analytics` e `consumption`; sua revisão integral do texto |
| **1.9** | Documentos, revisão do Codex, aceite e *tag* `v1.1.0` | `high` | M | 1.1–1.8 | Aceite do Owner; *push* autorizado |

**Parte II — a vitrine `bi-como-codigo`**

| Etapa | Entrega | Esforço | Tamanho | Depende de | Critério para avançar |
|---|---|---|---|---|---|
| **2.1** | Repositório: estrutura, convenções, *skills*, guarda de segredos, README com objetivo e mapa, este plano e o `REVIEW.md` transferidos | `medium` | P | — | Criado por você ou com a sua autorização; guarda de segredos verde |
| **2.2** | Projeto Firebase próprio e esteira: conferência do manifesto, montagem, prévia por PR, publicação no *merge* | `high` | M | 2.1 | Um PR de teste gera prévia; manifesto adulterado é recusado e nada é publicado |
| **2.3** | Protótipo comparativo do *framework* na P01, abrindo um Parquet cifrado | `high` | M | 2.1 | A mesma página nos candidatos, com o que cada um custou e o que faltou; você escolhe |
| **2.4** | Exportadores: as 16 views em Parquet com manifesto; os metadados de governança em JSON | `high` | M | 1.3, 1.9 | Cada Parquet reproduz a view, com a M2 generalizada como oráculo; somas exatas; recusa contrato divergente; os metadados batem com as contagens do *manifest* |
| **2.5** | Relatório da P01 completo | `high` | M | 2.3, 2.4 | Filtro, gráfico e tabela concordam com o pacote, conferidos no navegador *headless*; teclado e foco; 360 px; claro e escuro; mês parcial e recorte vazio |
| **2.6** | Acesso por perfil (O7, N23): declaração dos perfis, cifra na esteira, abertura no navegador, tela de login com a explicação e as credenciais, e o relatório da P13 | `xhigh` | M | 2.2, 2.5 | Matriz conferida na montagem: a senha da Logística abre a P13 e falha nas outras quinze, a da Diretoria abre todas; nenhum Parquet em claro no Hosting; vetor de inicialização nunca repetido; o Codex revisa o desenho da cifra |
| **2.7** | Portal de leitura da governança de dados (§3.2) | `xhigh` | G | 1.8, 2.4 | Os nove capítulos; todo número com origem e data; cada objeto do armazém alcançável pela busca; nenhum texto que contradiga a declaração |
| **2.8** | Governança do projeto | `high` | M | 2.4 | Cada afirmação aponta para documento, ADR ou histórico no commit fixado |
| **2.9** | Visão geral executiva | `xhigh` | M | 2.5–2.8 | Lida sozinha por alguém de fora, sem orador; todo número gerado |
| **2.10** | Validação, revisão do Codex, primeira publicação e o link no portfólio (N12) | `high` | M | 2.9 e autorização | Codex sem bloqueante; o site no ar é o da prévia aprovada; o link no projeto A, com o seu *push* no portfólio |
| **2.11** | Os outros catorze relatórios, em lotes por domínio | `high` | G | 2.10 | Por relatório: oráculo contra a view; razão só por numerador e denominador; a matriz de acesso continua provada |
| **2.12** | Modelo dimensional para exploração e detalhe, só quando um relatório pedir (N16) | `xhigh` | G | ADR no eng_dados | Contrato de consumo aplicado; cada tabela publicada reproduz a de origem |

**Parte III — o estudo**

| Etapa | Entrega | Esforço | Tamanho | Depende de | Critério para avançar |
|---|---|---|---|---|---|
| **3.1** | Sonda no claude.ai: um Artifact privado com DuckDB-WASM, *worker*, um Parquet cifrado aberto pela WebCrypto e a leitura de um arquivo publicado por URL | `medium` | P | 2.2 | Tudo funciona → estudo no Artifact; qualquer item falha → `*.web.app` (N18) |
| **3.2** | Repositório `caderno-de-dados` e o site do estudo | `medium` | P | 3.1 | Guarda de segredos verde; o site lê os relatórios da vitrine |
| **3.3** | Aula da P01, da view até a origem | `xhigh` | G | 1.3, 1.9, 2.4 | As cinco provas da [`REVIEW.md` §3.4](REVIEW.md#34-um-exemplo-pequeno-que-realmente-participa-do-resultado), cada uma com a consulta de conferência guardada; nenhuma afirmação sem evidência |
| **3.4** | Estudo da governança: inventário e roteiro, revisados pelo Codex | `high` | P | 1.9 | Cada mecanismo com fonte, incidente e laboratório previstos |
| **3.5** | Estudo da governança: redação por mecanismo | `xhigh` | G | 3.4 | Cada afirmação aponta para código ou ADR num commit fixado; cada "valor" aponta para incidente registrado |
| **3.6** | Estudo da governança: laboratórios executados de verdade | `high` | M | 3.5 | Toda saída colada vem de execução gravada, com data; estado da máquina devolvido |
| **3.7** | Explorações em SQL e ligação com a trilha | `high` | M | 3.2 | Consultas sobre os relatórios da vitrine funcionando no site do estudo |
| **3.8** | Relógio de estudo no `caderno-de-dados` (N10) | `medium` | P | 3.2 | Minutos registrados com a mesma regra da trilha |

### 6.3 Ordem recomendada

1. **1.1, 1.2 e 1.4.** Enquanto o Codex revisa o roteiro da 1.4, **1.7 e 1.8** — o refinamento não
   depende do dado. Depois, **1.5 e 1.6**, o caminho crítico: a etapa mais longa, a única
   destrutiva e a que mais pode surpreender. A **1.3** em qualquer ponto; por fim, a **1.9**.
2. Em paralelo à Parte I, porque não tocam o armazém: **2.1, 2.2, 2.3 e 3.1**.
3. Depois da 1.9: **2.4 a 2.10** — a primeira publicação leva a visão geral, a P01 e a P13 com o
   acesso por perfil, o portal e a governança do projeto —; depois, a **2.11** em lotes.
4. Depois da 1.9 e da 2.4: **3.2 a 3.8**.

---

## 7. O que ainda se decide, na hora certa

Todas as perguntas de desenho estão respondidas (§1.2). Ficam dois tipos de decisão.

**Escolhas que valem salvo objeção sua:** o perfil restrito é a **Logística, só com a P13** — você
delegou a escolha, e é a que a história explica melhor; a linhagem chega por `--json` do eng_dados
(a antiga N11); a aula lê as camadas internas pelo custodiante, em transação somente leitura, sem
papel novo (a antiga N5).

**Decisões que só cabem durante a execução** — o trabalho para até você responder:

- o *framework*, depois do protótipo da Etapa 2.3;
- a autorização da regeneração, antes da 1.6, porque ela é destrutiva;
- a revisão integral das descrições escritas, na 1.8;
- o aceite da v1.1.0 e cada *push*, da 1.9 em diante;
- a criação dos repositórios e do projeto Firebase, na 2.1 e na 2.2 — feita por você ou com a sua
  autorização;
- os ADRs dos componentes novos de cada repositório — hospedagem, esteira e cifra por perfil —,
  registrados quando cada um nasce;
- o resultado da sonda da 3.1 não pede decisão: a regra da N18 já diz o que fazer.

---

## 8. Riscos

| Risco | Tratamento |
|---|---|
| A regeneração quebra o que nenhum teste cobre | Roteiro revisado (1.4), pacote de recuperação conferido antes, um passo por vez com oráculo, recuo escrito |
| Memória da máquina (R11) | Só os alvos guardados; recusa por memória para e pede ao Owner, nunca `FORCE=1` por conta própria |
| Descrição herdada com significado errado | Herança só por transporte; discordância escrita à mão com motivo; revisão por amostragem do herdado e integral do escrito |
| A vitrine afirma o que o registro não sustenta | Todo número gerado de um registro num commit fixado; o Codex revisa a vitrine antes da primeira publicação |
| Cifra montada errado — vetor repetido, derivação fraca, chave ou Parquet em claro no site | Só primitivas padrão da WebCrypto (PBKDF2 com muitas iterações, AES-KW, AES-GCM com vetor aleatório por arquivo); a montagem confere a matriz e a ausência de texto em claro; o Codex revisa o desenho antes da publicação |
| Senha pública acusada pela guarda de segredos | As duas credenciais registradas como públicas por desenho, com o motivo (N22) |
| O portal vira o grafo inteiro de novo | Linhagem um salto por vez; narrativa por capítulos antes da referência |
| Cota diária do Firebase gratuito | Motor pelo jsDelivr; cada página carrega só os seus arquivos; projetos separados |
| O jsDelivr fora do ar desliga a interatividade | Aceito na N2; a página mostra o erro em vez de números velhos ou vazios |
| O claude.ai limita o estudo | A sonda da 3.1 decide antes de construir; a regra da N18 manda para um `*.web.app` |
| Razão reagregada como média de médias | Regra da §3.2 e oráculo por relatório contra a view |
| O eng_dados muda e um site diverge em silêncio | Contrato conferido e âncoras num commit fixado: exportação e montagem falham alto |
| *Manifest* parcial depois de um `dbt --select` | O exportador recusa linhagem com problema, como o `lineage.main` já faz |
| Volume que ninguém revisa (R14) | Relatórios, capítulos do portal, regras de acesso e percurso são declaração em texto, revisados por inteiro; o derivado, por oráculo |

---

## 9. Não verificado e premissas

**Não verificado:**

- se o DuckDB-WASM, o *worker* e a WebCrypto funcionam dentro do Artifact do claude.ai — a 3.1 mede;
- quanto tempo a derivação da chave leva no navegador, com as iterações escolhidas — a 2.6 mede;
- o que o Firebase faz quando o plano Spark estoura a cota;
- se o *framework* escolhido empacota o DuckDB-WASM no próprio site ou aceita o jsDelivr;
- a federação de identidade do GitHub com o Firebase, na prática;
- se alguma consulta, teste ou documento do eng_dados depende dos nomes atuais das categorias ou da
  faixa única de preço — a 1.4 levanta;
- quantas descrições herdadas precisam ser corrigidas à mão — a M18 é estimativa;
- o tempo e a memória da regeneração com o dado novo;
- se a mudança da §4 da Governança afeta algum teste de classificação ou de acesso;
- acessibilidade e usabilidade dos sites.

**Premissas:**

- o eng_dados continua a fonte única do dado, das regras e da governança; os repositórios novos não
  recalculam métrica nem reescrevem metadado;
- o dado só muda por regeneração deliberada, então atualizar é raro;
- relatórios, capítulos, regras de acesso e percurso ficam pequenos o bastante, como texto, para
  revisão integral.

---

## 10. Pedido de revisão ao Codex

Revisar este plano contra o código, os ADRs e as decisões O1–O7 e N1–N23 da §1. Em particular:

1. a arquitetura da §3.4 — manifesto, PR e recusa — garante que nada errado é publicado?
2. a cifra por perfil da §3.2 é controle de acesso de verdade, com primitivas padrão, sem chave nem
   Parquet em claro, e a prova na montagem basta?
3. a §5.3 subestima o custo ou o efeito da regeneração?
4. a §5.4 — descrição derivada pela linhagem — é o mecanismo certo, e a catraca nova cabe no
   `make check` sem custo excessivo?
5. a N16 lê corretamente o ADR-0008, o ADR-0018 e a Governança §7?
6. os capítulos do portal (§3.2) contam a história que um recém-chegado precisa, na ordem certa?
7. a ordem da §6.3, as dependências e o esforço de cada etapa se sustentam?
8. falta alguma decisão, ou alguma das pendentes não deveria ser do Owner?

As sondas se reexecutam com os bancos de pé (`make up`) e mais nada:
`data/medicoes/caminho_dos_dados_20261022/ro.sh <arquivo.sql>`, da raiz do eng_dados, sempre em
sessão somente leitura. O protótipo de linhagem e as medições do catálogo precisam só do `.venv` e
de um *manifest* completo; a exportação para Parquet, do `uv`, conforme o cabeçalho de
`exportar.saida.txt`.
