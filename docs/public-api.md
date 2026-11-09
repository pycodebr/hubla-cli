# Backend da API pública

`HublaClient(backend="public" | "auto")` e a opção `--backend` do CLI usam a API pública oficial da Hubla
(`https://backend-bff-public-api.platform.hub.la`), autenticada pelo token de integração no header
`Authorization` (o token puro, sem `Bearer`). Não há login, refresh nem conta colaboradora: cada conta tem o
próprio token. O token vem de `HUBLA_API_TOKEN` ou do perfil salvo por `hubla-cli login --api-token`.

## Métodos cobertos

| Recurso | Métodos | Rota da API pública |
|---|---|---|
| `sales` | `list`, `filter`, `iter_all`, `all` | `POST /v1/invoices/list` |
| `sales` | `get`, `detail` | `GET /v1/invoices/{id}` |
| `sales` | `summaries` | calculado: listagem + detalhe de cada fatura (líquido) |
| `products` | `list`, `get` | `POST /v1/products/list`, `GET /v1/products/{id}` |
| `products` | `list_offers`, `iter_offers`, `all_offers`, `get_offer`, `global_offers` | `GET /v1/products/{id}/offers[/{offerId}]` |
| `members` | `active`, `all`, `iter_all`, `find_exact_by_email`, `get_current_cohort_ids` | `GET /v1/{legacyId}/participants` |
| `members` | `deactivated` (sem busca) | `GET /v1/{legacyId}/members?status=deactivate` |
| `members` | `create_free_subscription` sem `offer_id`/`quantity` | `POST /v1/{legacyId}/members/invites` |
| `subscriptions` | `get`, `deactivate`, `disable_auto_renew` | `/v1/subscriptions/{id}` |
| `subscriptions` | `list` com `search` | faturas do comprador + `GET /v1/subscriptions/{id}` |
| `subscriptions` | `list_smart_installments` | `POST /v1/smart-installments/list` |
| `refunds` | `list`, `list_seller` | `POST /v1/refunds/list` |
| `coupons` | `list`, `get`, `delete` | `/v1/coupons` |

Os demais métodos não têm equivalente: em `public` falham com `PublicApiUnsupported`; em `auto` usam o portal.
`hubla-cli api public GET /v1/...` faz chamadas cruas à API pública (escrita exige `--confirm`).

## Diferenças que o hubla-cli compensa

- Sem `dateStart`, a listagem de faturas da API pública devolve só os últimos dias. O portal devolvia o histórico
  inteiro; o CLI envia `dateStart=2015-01-01` quando `start_date` não é informado.
- A API pública ignora o fuso de `dateStart`/`dateEnd` (`00:00-03:00` vira `00:00Z`). O CLI converte para UTC
  toda data com fuso; datas sem fuso seguem como foram informadas.
- A API pública lista BRL, USD e EUR juntos. `wallet="national"` filtra BRL e `wallet="international"` as demais
  moedas, localmente; sem `wallet`, vêm todas.
- Filtros de UTM são aplicados localmente; `page_size` acima de 200 é montado localmente.
- Membros e participantes só aceitam o `legacyId` do produto; ofertas usam o ID público. O CLI converte os dois
  (mapa em cache por 24 h).
- A listagem de ofertas não traz `cohortIds`; o CLI lê o detalhe de cada oferta e guarda as turmas em cache
  (`HUBLA_PUBLIC_CACHE_TTL`, padrão 3 h; diretório `HUBLA_CACHE_DIR`).
- A listagem de faturas não traz `receivers`; o líquido (`amountDetail.netCents`) vem do detalhe. Os totais de
  `summaries` leem o detalhe de cada fatura uma vez e guardam só os valores em cache por versão da fatura.
- `participants` devolve uma linha por acesso; `find_exact_by_email` junta as linhas da mesma pessoa.
- A troca de turma só existe no portal. Em `auto`, `change_cohorts_with_readback` relê o membro no portal pelo
  e-mail e recusa a escrita se as turmas vistas pela API pública divergirem das do portal.

## Campos do formato do portal

`sales.list`/`get` mantêm todos os campos da API pública e acrescentam: `offers[]` (`id` = id do item, que é o id
da oferta, e `associatedSubscriptionId`), `items[].offerId` e `items[].productName`, `memberRef` (`id` = `payerId`,
e-mail, nome e telefone do comprador), `payer.identity`, `amount.paidCents`, `amount.returnedCents` (0 quando paga;
total quando reembolsada ou em chargeback), `payerSession.utm*`, `updatedAt` e, no detalhe, `amountDetail`
(`netCents`, `coProducers[].netCents`, `platformAmountCents`) a partir de `receivers[]`. Cada item traz
`_source: "public-api"`.

## Lacunas da API pública

Sem equivalente hoje: valor e quantidade de cada item da fatura, URL do checkout e parâmetros não UTM, valor
liquidado em reais de vendas internacionais, resumo de faturas, listagem de assinaturas, convites pendentes,
convite gratuito para uma oferta ou turma, troca de turma, oferta de origem de cada acesso, mudança de status e
duplicação de oferta, turmas, aceite ou recusa de reembolso, conta, colaboradores, afiliados, vitrines,
integrações, finanças, Hubla Agents e conteúdo da área de membros.
