# Mapa de contratos da API Hubla

> Este documento pertence a um cliente comunitário e não oficial. Os contratos foram observados no portal web e podem mudar sem aviso. Não representam uma API pública ou estável oferecida pela Hubla.

## Autenticação

O portal expõe sua configuração pública do Firebase em:

```text
GET https://app.hub.la/__/firebase/init.json
```

O CLI obtém `apiKey` dessa configuração e usa os fluxos de senha e renovação do Firebase:

```text
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword
POST https://securetoken.googleapis.com/v1/token
```

Os BFFs recebem o ID token de curta duração no cabeçalho `Authorization: Bearer ...`. O CLI nunca documenta, imprime ou versiona o valor desse cabeçalho.

A senha serve apenas para criar a primeira sessão. A persistência local guarda o token renovável. Depois de um HTTP 401, o transporte invalida o ID token, renova a sessão e tenta a requisição uma única vez.

Contas com CAPTCHA ou MFA adicional podem precisar concluir o fluxo no portal. Essas proteções não devem ser contornadas.

## Serviços permitidos

| Alias | Base |
| --- | --- |
| `web` | `https://backend-bff-web.platform.hub.la/api/v1` |
| `product` | `https://backend-bff-product.platform.hub.la/api/v1` |
| `members_area` | `https://backend-bff-members-area.platform.hub.la/api/v1` |
| `access` | `https://backend-bff-access.platform.hub.la/api/v1` |
| `creators` | `https://backend-bff-creators.platform.hub.la/api/v1` |
| `crm` | `https://backend-bff-web-crm.platform.hub.la/api/v1` |
| `data` | `https://backend-bff-data.platform.hub.la/api/v1` |
| `pay` | `https://bff-pay.platform.hub.la/v1` |
| `member_portal` | `https://backend-bff-member-portal.platform.hub.la/api/v1` |
| `certificate` | `https://bff-certificate.platform.hub.la` |
| `functions` | `https://us-central1-chatpay-cd120.cloudfunctions.net` |

`HublaTransport` aceita apenas um desses aliases e um caminho relativo. URLs absolutas, URLs relativas a protocolo e hosts externos são rejeitados.

## Vendas e faturamento

| Método | Serviço | Caminho | Classe |
| --- | --- | --- | --- |
| POST | `web` | `/invoices/list` | leitura |
| GET | `web` | `/invoices/{invoiceId}` | leitura |
| POST | `web` | `/invoices/summaries` | leitura |
| POST | `web` | `/invoices/background-export` | exportação confirmada |
| PUT | `web` | `/invoices/{invoiceId}/refund` | alteração confirmada |
| POST | `web` | `/receiver/summary/net-revenue` | leitura |
| POST | `web` | `/receiver/summary/sales` | leitura |
| POST | `web` | `/receiver/summary/refunds` | leitura |
| POST | `web` | `/receiver/summary/average-ticket` | leitura |
| POST | `web` | `/receiver/summary/average-ticket-by-currency` | leitura |
| POST | `web` | `/receiver/summary/conversion-rate` | leitura |
| POST | `web` | `/leads/summary/total-leads` | leitura |

O corpo de listagem e resumo usa seleção explícita de ofertas:

```json
{
  "offerIds": ["OFFER_ID"],
  "hasSelectedAll": false,
  "filters": {
    "startDate": "2026-01-01T00:00:00-03:00",
    "endDate": "2026-01-31T23:59:59-03:00",
    "status": ["paid"],
    "type": [],
    "paymentMethod": [],
    "search": "",
    "utmSource": "",
    "utmMedium": "",
    "utmCampaign": "",
    "utmContent": "",
    "utmTerm": "",
    "dateRangeBy": null,
    "wallet": null
  },
  "page": 1,
  "pageSize": 25,
  "orderBy": "createdAt",
  "orderDirection": "DESC"
}
```

## Solicitações de reembolso

| Método | Serviço | Caminho | Classe |
| --- | --- | --- | --- |
| POST | `web` | `/refunds/seller/list` | leitura |
| GET | `web` | `/refunds/{refundId}` | leitura |
| PATCH | `web` | `/refunds/{refundId}/accept` | alteração confirmada |
| PATCH | `web` | `/refunds/{refundId}/reject` | alteração confirmada |
| POST | `web` | `/refunds/seller/background-export` | exportação confirmada |
| POST | `web` | `/refunds/request` | alteração confirmada |
| GET | `web` | `/payer/refunds` | leitura |
| GET | `web` | `/payer/refunds/{refundId}` | leitura |
| PATCH | `web` | `/refunds/{refundId}/cancel` | alteração confirmada |
| PATCH | `web` | `/refunds/{refundId}/reactivate` | alteração confirmada |

## Assinaturas, trials e parcelas

| Método | Serviço | Caminho | Classe |
| --- | --- | --- | --- |
| POST | `web` | `/subscriptions/list` | leitura |
| GET | `web` | `/subscriptions/{subscriptionId}` | leitura |
| GET | `web` | `/subscriptions/{subscriptionId}/invoices` | leitura |
| PUT | `web` | `/subscriptions/{subscriptionId}/deactivate` | alteração confirmada |
| PUT | `web` | `/subscriptions/{subscriptionId}/add-daily-credits` | alteração confirmada |
| POST | `web` | `/subscriptions/export` | exportação confirmada |
| POST | `web` | `/receiver/summary/subscriptions/activated` | leitura |
| POST | `web` | `/receiver/summary/subscriptions/canceled` | leitura |
| POST | `web` | `/receiver/summary/subscriptions/inactivated` | leitura |
| POST | `web` | `/receiver/summary/subscriptions/newers` | leitura |
| POST | `web` | `/pay/enable-subscription-auto-renew` | alteração confirmada |
| POST | `web` | `/pay/disable-subscription-auto-renew` | alteração confirmada |
| GET | `web` | `/pay/get-pending-invoice-for-subscription` | leitura |
| GET | `web` | `/pay/get-subscription-value` | leitura |
| GET | `web` | `/pay/upgrade-state` | leitura |
| POST | `web` | `/pay/init-upgrade` | alteração confirmada |
| POST | `web` | `/pay/submit-upgrade` | alteração confirmada |
| POST | `web` | `/pay/cancel-upgrade` | alteração confirmada |
| POST | `web` | `/pay/init-change-payment-method` | alteração confirmada |
| POST | `pay` | `/change-subscription-funding` | alteração confirmada |
| POST | `web` | `/smart-installments/list` | leitura |
| POST | `web` | `/smart-installments/summaries` | leitura |
| POST | `web` | `/smart-installments/all-installments` | leitura |
| PUT | `web` | `/smart-installments/{installmentId}/cancel` | alteração confirmada |
| POST | `web` | `/free-trial/summaries` | leitura |

Desativar renovação automática não prova que um acesso deve terminar imediatamente. O consumidor deve interpretar período pago, estado da assinatura e demais direitos da conta antes de qualquer mudança separada de acesso.

## Produtos, ofertas, turmas e recursos

| Método | Serviço | Caminho | Classe |
| --- | --- | --- | --- |
| GET | `product` | `/products` | leitura |
| GET | `product` | `/products/{productId}` | leitura |
| POST | `product` | `/products` | alteração confirmada |
| PATCH | `product` | `/products/{productId}/status` | alteração confirmada |
| PATCH | `product` | `/products/{productId}/visibility` | alteração confirmada |
| DELETE | `product` | `/products/{productId}` | alteração confirmada |
| GET | `product` | `/products/{productId}/offers` | leitura |
| GET | `product` | `/products/{productId}/offers/{offerId}/edit` | leitura |
| POST | `product` | `/products/{productId}/offers` | alteração confirmada |
| PUT | `product` | `/products/{productId}/offers/{offerId}/edit` | alteração confirmada |
| PATCH | `product` | `/products/{productId}/offers/{offerId}/name` | alteração confirmada |
| PUT | `product` | `/products/{productId}/offers/{offerId}/status` | alteração confirmada |
| POST | `product` | `/products/{productId}/offers/{offerId}/duplicate` | alteração confirmada |
| POST | `product` | `/products/{productId}/offers/{offerId}/archive` | alteração confirmada |
| POST | `product` | `/products/{productId}/offers/unarchive` | alteração confirmada |
| GET | `product` | `/filters/offers` | leitura |
| GET | `product` | `/filters/products` | leitura |
| GET | `product` | `/products/{productId}/cohorts` | leitura |
| POST | `product` | `/products/{productId}/cohorts` | alteração confirmada |
| PUT | `product` | `/products/{productId}/cohorts/{cohortId}` | alteração confirmada |
| PATCH | `product` | `/products/{productId}/cohorts/{cohortId}/name` | alteração confirmada |
| POST | `product` | `/products/{productId}/cohorts/{cohortId}/duplicate` | alteração confirmada |
| GET | `product` | `/products/{productId}/offers/offers-and-cohorts` | leitura |
| GET | `product` | `/products/{productId}/offers/combo-cohorts` | leitura |
| PUT | `product` | `/products/{productId}/offers/combo-cohorts` | alteração confirmada |
| GET | `product` | `/products/{productId}/settings/{type}` | leitura |
| PATCH | `product` | `/products/{productId}/settings/{type}` | alteração confirmada |
| GET | `product` | `/resources/get-resources-by-filters/{type}` | leitura |
| GET | `product` | `/resources/get-associated-cohorts/{resourceId}/{productId}` | leitura |
| POST | `product` | `/resources/get-resources-by-cohort-ids` | leitura |
| PATCH | `product` | `/resources/update-offer-resource/{resourceId}/{productId}` | alteração confirmada |
| DELETE | `product` | `/resources/{resourceId}` | alteração confirmada |
| POST | `product` | `/products/bind-resource/{offerId}` | alteração confirmada |
| POST | `product` | `/products/unbind-resource/{offerId}` | alteração confirmada |
| POST | `product` | `/products/bind-brain/{offerId}` | alteração confirmada |
| POST | `product` | `/products/unbind-brain/{offerId}` | alteração confirmada |

Os payloads de criação e atualização são dicionários flexíveis porque os DTOs do portal podem receber campos novos. Leia o objeto atual antes de enviar uma atualização e preserve os campos obrigatórios.

## Membros e acesso

| Método | Serviço | Caminho | Classe |
| --- | --- | --- | --- |
| GET | `members_area` | `/members/actives/list` | leitura |
| GET | `members_area` | `/members/deactivates/list` | leitura |
| GET | `members_area` | `/invites/list/pending` | leitura |
| POST | `members_area` | `/members/create-invites-free-subscription` | alteração confirmada |
| PUT | `members_area` | `/members/remove-free-subscription` | alteração confirmada |
| POST | `members_area` | `/members/free-subscription-old-members` | alteração confirmada |
| POST | `members_area` | `/members/get-accesses-by-product-id` | leitura |
| GET | `members_area` | `/members/actives/export` | exportação confirmada |
| GET | `members_area` | `/members/deactivates/export` | exportação confirmada |
| PUT | `members_area` | `/invites/{inviteId}/cancel` | alteração confirmada |
| POST | `access` | `/access/change-member-cohorts-by-product` | alteração confirmada |
| POST | `access` | `/access/change-members-cohorts` | alteração confirmada |
| PUT | `access` | `/access/member-edit-access` | alteração confirmada |
| POST | `access` | `/access/send-ticket` | alteração confirmada |
| POST | `access` | `/access/transfer-accesses` | alteração confirmada |
| POST | `web` | `/members/send-access-link` | alteração confirmada |
| POST | `web` | `/auth/recover-member-password` | alteração confirmada |

Adicionar acesso gratuito usa um corpo semelhante a:

```json
{
  "productId": "PRODUCT_ID",
  "receiverEmails": ["pessoa@example.com"],
  "days": 30,
  "lifetime": false,
  "offerId": "OFFER_ID"
}
```

## Grupos

| Método | Serviço | Caminho | Classe |
| --- | --- | --- | --- |
| POST | `functions` | `/group/get/pt` | leitura |
| POST | `functions` | `/group/getWhitelist/pt` | leitura |
| POST | `functions` | `/groupResource/get/pt` | leitura |
| POST | `functions` | `/groupWhitelist/listMembersByGroupResourceId/pt` | leitura |
| POST | `functions` | `/groupWhitelist/generateLink/pt` | alteração confirmada |
| POST | `functions` | `/groupWhitelist/remove/pt` | alteração confirmada |
| POST | `functions` | `/group/addResource/pt` | alteração confirmada |

## Financeiro

| Método | Serviço | Caminho | Classe |
| --- | --- | --- | --- |
| GET | `web` | `/financial-statement/balance` | leitura |
| GET | `web` | `/financial-statement/account-statement` | leitura |
| GET | `web` | `/financial-statement/movements` | leitura |
| POST | `web` | `/financial-statement/movements/export` | exportação confirmada |
| GET | `web` | `/dashboard/creator/invoices/{invoiceId}` | leitura |
| GET | `web` | `/financial-statement/invoices/{invoiceId}/movements` | leitura |
| GET | `web` | `/financial-statement/withdrawals/{withdrawalId}` | leitura |
| POST | `web` | `/financial-statement/withdrawal/web` | alteração confirmada |

Valores enviados a `finance.withdraw` usam centavos. Moeda, valor, dispositivo e código de validação devem ser confirmados antes da chamada.

## Conta e colaboradores

| Método | Serviço | Caminho | Classe |
| --- | --- | --- | --- |
| GET | `web` | `/business` | leitura |
| GET | `web` | `/user/me/profile` | leitura |
| GET | `web` | `/user/me/notifications` | leitura |
| GET | `web` | `/user/me/reference` | leitura |
| GET | `web` | `/kyc/get-payout` | leitura |
| GET | `web` | `/two-factor/list-devices` | leitura |
| POST | `web` | `/mfa/start` | alteração confirmada |
| POST | `web` | `/mfa/verify` | alteração confirmada |
| PUT | `web` | `/user/save-user-login-preferences` | alteração confirmada |
| PUT | `web` | `/auth/email` | alteração confirmada |
| POST | `functions` | `/userInfo/setBasicInfo/pt` | alteração confirmada |
| POST | `functions` | `/userInfo/updateNotificationSettings/pt` | alteração confirmada |
| GET | `web` | `/user/roleplay/collaborators` | leitura |
| POST | `web` | `/user/roleplay/collaborators` | alteração confirmada |
| PUT | `web` | `/user/roleplay/collaborators` | alteração confirmada |
| DELETE | `web` | `/user/roleplay/collaborators/{collaboratorId}/` | alteração confirmada |

## Afiliados, cupons, vitrines e integrações

A biblioteca expõe os contratos abaixo por métodos de alto nível:

- afiliados: listagem, programa, afiliações, comissão, remoção e exportação;
- cupons: listagem, detalhe, criação, exclusão e exportação;
- vitrines: listagem, slug, criação, atualização e vínculos de produtos;
- integrações: visão geral, detalhe, provedor, histórico, regras, tags, listas e retry de eventos.

Use `hubla-cli --json schema affiliates`, `coupons`, `storefronts` ou `integrations` para obter os parâmetros atuais de cada método.

## Classificação e confirmação

O verbo HTTP não basta para classificar uma rota. Algumas leituras usam POST e algumas exportações usam GET. A fonte de verdade do CLI é a assinatura do método:

- sem parâmetro `confirm`: leitura;
- com parâmetro `confirm`: alteração ou exportação sensível;
- acesso raw diferente de GET: sempre confirmado por precaução.

Depois de qualquer alteração, faça uma leitura específica do mesmo registro. Uma resposta HTTP de sucesso não prova sozinha que o estado final corresponde ao solicitado.
