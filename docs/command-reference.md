# Referência completa de operações

> Gerado por `scripts/generate_command_reference.py`. Não edite manualmente.
> Este projeto é comunitário e não oficial; as APIs do portal podem mudar.

Use qualquer operação abaixo com:

```bash
hubla-cli --json call RECURSO OPERAÇÃO --params '{"parametro":"valor"}'
```

Operações marcadas como **alteração** exigem autorização específica do usuário e `--confirm`.
Parâmetros com `?` são opcionais. Consulte o schema executável para tipos e valores padrão:

```bash
hubla-cli --json schema RECURSO OPERAÇÃO
```

## account

Inspect account settings and perform confirmed account changes.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `account.add_collaborator` | **alteração — `--confirm`** | `payload` |
| `account.business` | leitura | — |
| `account.collaborators` | leitura | — |
| `account.notifications` | leitura | — |
| `account.payout` | leitura | — |
| `account.profile` | leitura | — |
| `account.reference` | leitura | — |
| `account.remove_collaborator` | **alteração — `--confirm`** | `collaborator_id` |
| `account.start_mfa` | **alteração — `--confirm`** | — |
| `account.two_factor_devices` | leitura | — |
| `account.update_collaborator` | **alteração — `--confirm`** | `payload` |
| `account.update_email` | **alteração — `--confirm`** | `email` |
| `account.update_login_preferences` | **alteração — `--confirm`** | `payload` |
| `account.update_notifications` | **alteração — `--confirm`** | `payload` |
| `account.update_profile` | **alteração — `--confirm`** | `payload` |
| `account.verify_mfa` | **alteração — `--confirm`** | `payload` |

## affiliates

Inspect affiliates and perform confirmed commission changes.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `affiliates.change_commission` | **alteração — `--confirm`** | `affiliate_id`, `sell_commission?`, `renewal_commission?`, `use_default_commission?`, `validation_code?` |
| `affiliates.export` | **alteração — `--confirm`** | `file_type?` |
| `affiliates.get_program` | leitura | `product_id` |
| `affiliates.list` | leitura | `page?`, `page_size?` |
| `affiliates.list_affiliations` | leitura | `filters?` |
| `affiliates.remove` | **alteração — `--confirm`** | `affiliate_id` |

## analytics

Read account metrics from Hubla's dashboard summaries.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `analytics.abandoned_checkouts` | leitura | `start_date`, `end_date`, `offer_ids?`, `has_selected_all?` |
| `analytics.average_ticket` | leitura | `start_date`, `end_date`, `offer_ids?`, `has_selected_all?`, `wallet?` |
| `analytics.average_ticket_by_currency` | leitura | `start_date`, `end_date`, `offer_ids?`, `has_selected_all?` |
| `analytics.conversion_rate` | leitura | `start_date`, `end_date`, `payment_method?`, `offer_ids?`, `has_selected_all?`, `wallet?` |
| `analytics.net_revenue` | leitura | `start_date`, `end_date`, `period`, `offer_ids?`, `has_selected_all?`, `wallet?` |
| `analytics.refunds` | leitura | `start_date`, `end_date`, `offer_ids?`, `has_selected_all?`, `wallet?` |
| `analytics.sales` | leitura | `start_date`, `end_date`, `offer_ids?`, `has_selected_all?`, `wallet?` |

## coupons

Inspect and manage account coupons.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `coupons.create` | **alteração — `--confirm`** | `payload` |
| `coupons.delete` | **alteração — `--confirm`** | `coupon_id` |
| `coupons.detail` | leitura | `coupon_id` |
| `coupons.export` | **exportação binária — `--confirm` e `--output`** | `offer_ids?`, `has_selected_all?`, `statuses?` |
| `coupons.get` | leitura | `coupon_id` |
| `coupons.list` | leitura | `offer_ids?`, `has_selected_all?`, `statuses?`, `search?`, `page?`, `page_size?`, `order_by?`, `order_direction?` |

## finance

Inspect balances and movements and perform confirmed withdrawals.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `finance.account_statement` | leitura | `params?` |
| `finance.all_movements` | leitura | `account_type`, `start_date`, `end_date`, `currency?`, `page_size?` |
| `finance.availability_forecast` | leitura | `target_dates?`, `currency?`, `timezone?` |
| `finance.balance` | leitura | `currency?` |
| `finance.invoice_details` | leitura | `invoice_id` |
| `finance.invoice_movements` | leitura | `invoice_id` |
| `finance.movements` | leitura | `params?` |
| `finance.movements_export` | **alteração — `--confirm`** | `params?`, `receiver_email?` |
| `finance.withdraw` | **alteração — `--confirm`** | `amount_in_cents`, `currency?`, `validation_code?` |
| `finance.withdrawal_details` | leitura | `withdrawal_id` |

## groups

Inspect Hubla groups and manage their resources and whitelist.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `groups.add_resource` | **alteração — `--confirm`** | `payload` |
| `groups.free_members` | leitura | `payload` |
| `groups.generate_whitelist_link` | **alteração — `--confirm`** | `payload` |
| `groups.group` | leitura | `group_id` |
| `groups.group_resource` | leitura | `resource_id` |
| `groups.remove_whitelist_member` | **alteração — `--confirm`** | `payload` |
| `groups.whitelist` | leitura | `group_id` |

## integrations

Inspect and manage integrations, rules, and event retries.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `integrations.create` | **alteração — `--confirm`** | `payload` |
| `integrations.create_rule` | **alteração — `--confirm`** | `integration_id`, `payload` |
| `integrations.delete` | **alteração — `--confirm`** | `integration_id` |
| `integrations.delete_rule` | **alteração — `--confirm`** | `integration_id`, `rule_id` |
| `integrations.get` | leitura | `integration_id` |
| `integrations.get_event` | leitura | `integration_id`, `event_id` |
| `integrations.get_rule` | leitura | `integration_id`, `rule_id` |
| `integrations.history` | leitura | `integration_id`, `payload` |
| `integrations.list` | leitura | `page?`, `page_size?`, `provider?` |
| `integrations.overview` | leitura | `page?`, `page_size?` |
| `integrations.provider` | leitura | `provider` |
| `integrations.provider_lists` | leitura | `integration_id` |
| `integrations.provider_tags` | leitura | `integration_id` |
| `integrations.retry_events` | **alteração — `--confirm`** | `integration_id`, `event_ids` |
| `integrations.rules` | leitura | `integration_id`, `page?`, `page_size?` |
| `integrations.update_rule` | **alteração — `--confirm`** | `integration_id`, `rule_id`, `payload` |

## members

Inspect members and manage account-authorized access changes.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `members.accesses_by_product` | leitura | `product_id` |
| `members.active` | leitura | `page?`, `page_size?`, `product_id?`, `types?`, `search?`, `cohort_ids?`, `include_items_quantity_total?` |
| `members.add` | **alteração — `--confirm`** | `product_id`, `emails`, `lifetime`, `days?`, `offer_id?`, `quantity?` |
| `members.cancel_invite` | **alteração — `--confirm`** | `invite_id` |
| `members.change_cohorts` | **alteração — `--confirm`** | `members`, `new_cohorts` |
| `members.change_cohorts_by_product` | **alteração — `--confirm`** | `product_id`, `member_ids`, `cohorts` |
| `members.create_free_subscription` | **alteração — `--confirm`** | `product_id`, `emails`, `lifetime`, `days?`, `offer_id?`, `quantity?` |
| `members.deactivated` | leitura | `page?`, `page_size?`, `product_id?`, `search?` |
| `members.edit_access` | **alteração — `--confirm`** | `payload` |
| `members.export_active` | **exportação binária — `--confirm` e `--output`** | `page?`, `page_size?`, `product_id?`, `offer_id?`, `types?`, `search?`, `timezone?` |
| `members.export_deactivated` | **exportação binária — `--confirm` e `--output`** | `page?`, `page_size?`, `product_id?`, `offer_id?`, `search?`, `timezone?` |
| `members.list_active` | leitura | `page?`, `page_size?`, `product_id?`, `types?`, `search?`, `cohort_ids?`, `include_items_quantity_total?` |
| `members.list_deactivated` | leitura | `page?`, `page_size?`, `product_id?`, `search?` |
| `members.offers_and_cohorts` | leitura | `product_id` |
| `members.pending_invites` | leitura | — |
| `members.recover_password` | **alteração — `--confirm`** | `payload` |
| `members.remove` | **alteração — `--confirm`** | `product_id`, `user_id` |
| `members.remove_free_subscription` | **alteração — `--confirm`** | `product_id`, `user_id` |
| `members.send_access_link` | **alteração — `--confirm`** | `payload` |
| `members.send_ticket` | **alteração — `--confirm`** | `payload` |
| `members.ticket_counters` | leitura | `product_id` |
| `members.transfer_access` | **alteração — `--confirm`** | `to_user_email`, `access_code`, `notes?` |
| `members.transform_free_members` | **alteração — `--confirm`** | `product_id`, `user_ids`, `days`, `lifetime` |

## products

Inspect and manage products, offers, cohorts, settings, and resources.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `products.archive_offer` | **alteração — `--confirm`** | `product_id`, `offer_id` |
| `products.associated_cohorts` | leitura | `resource_external_id`, `product_id` |
| `products.bind_brain` | **alteração — `--confirm`** | `offer_id`, `brain_id`, `cohort_ids` |
| `products.bind_resource` | **alteração — `--confirm`** | `offer_id`, `external_resource_id`, `cohort_ids` |
| `products.change_offer_status` | **alteração — `--confirm`** | `product_id`, `offer_id`, `status` |
| `products.change_status` | **alteração — `--confirm`** | `product_id`, `status` |
| `products.create` | **alteração — `--confirm`** | `payload` |
| `products.create_cohort` | **alteração — `--confirm`** | `product_id`, `name`, `sections?`, `groups?`, `tracks?` |
| `products.create_offer` | **alteração — `--confirm`** | `product_id`, `payload` |
| `products.delete` | **alteração — `--confirm`** | `product_id` |
| `products.delete_resource` | **alteração — `--confirm`** | `resource_id` |
| `products.detail` | leitura | `product_id` |
| `products.duplicate_cohort` | **alteração — `--confirm`** | `product_id`, `cohort_id` |
| `products.duplicate_offer` | **alteração — `--confirm`** | `product_id`, `offer_id` |
| `products.external_contents` | leitura | `product_id` |
| `products.get` | leitura | `product_id` |
| `products.get_combo_cohorts` | leitura | `product_id` |
| `products.get_offer` | leitura | `product_id`, `offer_id` |
| `products.get_offers_and_cohorts` | leitura | `product_id` |
| `products.get_settings` | leitura | `product_id`, `setting_type` |
| `products.global_offers` | leitura | — |
| `products.global_product_filters` | leitura | — |
| `products.list` | leitura | `types?`, `page?`, `page_size?`, `time_scope?`, `include_deleted?` |
| `products.list_cohorts` | leitura | `product_id`, `page?`, `page_size?`, `enhance_with_details?` |
| `products.list_offers` | leitura | `product_id`, `page?`, `page_size?`, `archived?` |
| `products.list_products` | leitura | `types?`, `page?`, `page_size?`, `time_scope?`, `include_deleted?` |
| `products.list_resources` | leitura | `resource_type`, `has_product_association?` |
| `products.products_by_offer_ids` | leitura | `main_offer_ids`, `page?`, `page_size?` |
| `products.rename_cohort` | **alteração — `--confirm`** | `product_id`, `cohort_id`, `name` |
| `products.rename_offer` | **alteração — `--confirm`** | `product_id`, `offer_id`, `name` |
| `products.resources_by_cohort_ids` | leitura | `cohort_ids`, `resource_type?` |
| `products.save_settings` | **alteração — `--confirm`** | `product_id`, `setting_type`, `payload` |
| `products.ticket_counters` | leitura | `product_id` |
| `products.toggle_visibility` | **alteração — `--confirm`** | `product_id` |
| `products.unarchive_offers` | **alteração — `--confirm`** | `product_id`, `offer_ids` |
| `products.unbind_brain` | **alteração — `--confirm`** | `offer_id`, `brain_id`, `cohort_ids` |
| `products.unbind_resource` | **alteração — `--confirm`** | `offer_id`, `external_resource_id`, `cohort_ids` |
| `products.update_cohort` | **alteração — `--confirm`** | `product_id`, `cohort_id`, `name`, `sections?`, `groups?`, `tracks?` |
| `products.update_combo_cohorts` | **alteração — `--confirm`** | `product_id`, `cohort_ids` |
| `products.update_offer` | **alteração — `--confirm`** | `product_id`, `offer_id`, `payload` |
| `products.update_offer_resource` | **alteração — `--confirm`** | `resource_id`, `product_id`, `payload`, `cohort_ids?` |

## refunds

Inspect and manage seller and payer refund requests.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `refunds.accept` | **alteração — `--confirm`** | `refund_id` |
| `refunds.background_export` | **alteração — `--confirm`** | `file_type?`, `filters?` |
| `refunds.cancel_request` | **alteração — `--confirm`** | `refund_id` |
| `refunds.create_request` | **alteração — `--confirm`** | `invoice_id`, `description?`, `feedback?`, `refund_payer_data?` |
| `refunds.export_legacy` | **alteração — `--confirm`** | `file_extension?` |
| `refunds.get` | leitura | `refund_id` |
| `refunds.get_payer` | leitura | `refund_id` |
| `refunds.list` | leitura | `page?`, `page_size?`, `filters?` |
| `refunds.list_payer` | leitura | `params?` |
| `refunds.list_seller` | leitura | `page?`, `page_size?`, `filters?` |
| `refunds.reactivate_request` | **alteração — `--confirm`** | `refund_id` |
| `refunds.reject` | **alteração — `--confirm`** | `refund_id` |
| `refunds.request` | **alteração — `--confirm`** | `invoice_id`, `description?`, `feedback?`, `refund_payer_data?` |

## sales

List invoices, inspect sales, export data, and request refunds.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `sales.detail` | leitura | `invoice_id` |
| `sales.export` | **exportação binária — `--confirm` e `--output`** | `offer_ids?`, `has_selected_all?`, `start_date?`, `end_date?`, `statuses?`, `types?`, `methods?`, `search?`, `utm_source?`, `utm_medium?`, `utm_campaign?`, `utm_content?`, `utm_term?`, `date_range_by?`, `wallet?`, `page?`, `page_size?`, `order_by?`, `order_direction?` |
| `sales.filter` | leitura | `offer_ids?`, `has_selected_all?`, `start_date?`, `end_date?`, `statuses?`, `types?`, `methods?`, `search?`, `utm_source?`, `utm_medium?`, `utm_campaign?`, `utm_content?`, `utm_term?`, `date_range_by?`, `wallet?`, `page?`, `page_size?`, `order_by?`, `order_direction?` |
| `sales.get` | leitura | `invoice_id` |
| `sales.list` | leitura | `offer_ids?`, `has_selected_all?`, `start_date?`, `end_date?`, `statuses?`, `types?`, `methods?`, `search?`, `utm_source?`, `utm_medium?`, `utm_campaign?`, `utm_content?`, `utm_term?`, `date_range_by?`, `wallet?`, `page?`, `page_size?`, `order_by?`, `order_direction?` |
| `sales.reembolsar` | **alteração — `--confirm`** | `invoice_id` |
| `sales.refund` | **alteração — `--confirm`** | `invoice_id` |
| `sales.summaries` | leitura | `offer_ids?`, `has_selected_all?`, `start_date?`, `end_date?`, `statuses?`, `types?`, `methods?`, `search?`, `utm_source?`, `utm_medium?`, `utm_campaign?`, `utm_content?`, `utm_term?`, `date_range_by?`, `wallet?`, `page?`, `page_size?`, `order_by?`, `order_direction?` |

## storefronts

Inspect and manage creator storefronts.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `storefronts.add_products` | **alteração — `--confirm`** | `storefront_id`, `products` |
| `storefronts.check_slug` | leitura | `slug` |
| `storefronts.create` | **alteração — `--confirm`** | `payload` |
| `storefronts.list` | leitura | — |
| `storefronts.remove_products` | **alteração — `--confirm`** | `storefront_id`, `product_ids` |
| `storefronts.select_for_product` | **alteração — `--confirm`** | `product_id`, `storefront_id` |
| `storefronts.update` | **alteração — `--confirm`** | `storefront_id`, `payload` |

## subscriptions

Inspect subscriptions, renewals, trials, upgrades, and installments.

| Operação | Tipo | Parâmetros |
| --- | --- | --- |
| `subscriptions.active_summary` | leitura | `start_date`, `end_date`, `period?`, `offer_ids?`, `has_selected_all?` |
| `subscriptions.add_daily_credits` | **alteração — `--confirm`** | `subscription_id`, `payload` |
| `subscriptions.all_installments` | leitura | `page?`, `page_size?`, `order_by?`, `order_direction?`, `filters?` |
| `subscriptions.cancel_smart_installment` | **alteração — `--confirm`** | `installment_id` |
| `subscriptions.cancel_upgrade` | **alteração — `--confirm`** | `subscription_id` |
| `subscriptions.canceled_summary` | leitura | `start_date`, `end_date`, `offer_ids?`, `has_selected_all?` |
| `subscriptions.deactivate` | **alteração — `--confirm`** | `subscription_id` |
| `subscriptions.disable_auto_renew` | **alteração — `--confirm`** | `subscription_id` |
| `subscriptions.enable_auto_renew` | **alteração — `--confirm`** | `subscription_id` |
| `subscriptions.export` | **exportação binária — `--confirm` e `--output`** | `offer_ids?`, `has_selected_all?`, `start_date?`, `end_date?`, `statuses?`, `plan_type?`, `date_range_by?`, `is_free_trial_active?`, `timezone?` |
| `subscriptions.filter` | leitura | `offer_ids?`, `has_selected_all?`, `start_date?`, `end_date?`, `statuses?`, `search?`, `date_range_by?`, `plan_type?`, `is_free_trial_active?`, `page?`, `page_size?`, `order_by?`, `order_direction?` |
| `subscriptions.free_trial_summaries` | leitura | `offer_ids?`, `has_selected_all?`, `search?`, `start_date?`, `end_date?`, `date_range_by?` |
| `subscriptions.free_trials` | leitura | `offer_ids?`, `has_selected_all?`, `search?`, `start_date?`, `end_date?`, `date_range_by?`, `page?`, `page_size?` |
| `subscriptions.get` | leitura | `subscription_id` |
| `subscriptions.inactive_summary` | leitura | `start_date`, `end_date`, `offer_ids?`, `has_selected_all?` |
| `subscriptions.init_change_payment_method` | **alteração — `--confirm`** | `subscription_id` |
| `subscriptions.init_upgrade` | **alteração — `--confirm`** | `subscription_id` |
| `subscriptions.invoices` | leitura | `subscription_id`, `page?`, `page_size?` |
| `subscriptions.list` | leitura | `offer_ids?`, `has_selected_all?`, `start_date?`, `end_date?`, `statuses?`, `search?`, `date_range_by?`, `plan_type?`, `is_free_trial_active?`, `page?`, `page_size?`, `order_by?`, `order_direction?` |
| `subscriptions.list_smart_installments` | leitura | `offer_ids?`, `has_selected_all?`, `start_date?`, `end_date?`, `statuses?`, `methods?`, `types?`, `search?`, `date_range_by?`, `page?`, `page_size?`, `order_by?`, `order_direction?` |
| `subscriptions.new_summary` | leitura | `start_date`, `end_date`, `offer_ids?`, `has_selected_all?` |
| `subscriptions.pending_invoice` | leitura | `subscription_id` |
| `subscriptions.smart_installments_summaries` | leitura | `kwargs?` |
| `subscriptions.submit_change_payment_method` | **alteração — `--confirm`** | `payload` |
| `subscriptions.submit_upgrade` | **alteração — `--confirm`** | `subscription_id`, `selected_option_id`, `installments` |
| `subscriptions.upgrade_state` | leitura | `subscription_id` |
| `subscriptions.value` | leitura | `subscription_id` |
