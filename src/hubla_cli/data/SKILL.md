---
name: hubla-cli
description: Use when a user wants to consultar ou gerenciar sua própria conta Hubla pelo terminal, automação ou agente de IA usando o comando hubla-cli.
license: MIT
compatibility: Requer o executável hubla-cli instalado, acesso à internet e uma conta Hubla autorizada pelo usuário.
metadata:
  version: "0.1.1"
---

# Hubla CLI

Use o `hubla-cli` como interface local para a conta Hubla autorizada pelo usuário. Prefira os comandos de alto nível e a saída JSON. Não tente reproduzir as requisições por `curl` quando o CLI já cobre o recurso.

## Primeiro uso

1. Verifique a instalação:

```bash
hubla-cli --version
hubla-cli --json doctor
```

Antes do primeiro login, `doctor` retorna código 2 e informa que credenciais e conta ainda não foram validadas. Isso indica que o próximo passo é o login, não uma tentativa de contornar a autenticação.

2. Verifique a sessão:

```bash
hubla-cli --json status
```

3. Se não houver login, não execute `hubla-cli login` pelo terminal interno do agente. Mostre ao usuário o comando abaixo para ele executar em um terminal separado:

```bash
hubla-cli login
```

Pare e aguarde o usuário responder `autenticado`. Só então execute:

```bash
hubla-cli --json status
```

O terminal separado deve usar o mesmo computador, usuário do sistema e ambiente em que o CLI foi instalado. Em uma VPS, o usuário deve executar o login por SSH nessa VPS. Um terminal local não compartilha credenciais com containers, sandboxes ou máquinas remotas.

Nunca peça que a pessoa envie e-mail, senha, token ou código de autenticação pelo chat, em argumento de comando, arquivo, log ou variável escrita por você. O prompt de login mascara a senha com asteriscos. O CLI não salva a senha; guarda somente o token renovável no cofre do sistema ou, quando ele não existe, em arquivo privado do usuário.

Para contas diferentes, use um perfil explícito e preserve o mesmo perfil nos comandos seguintes:

```bash
hubla-cli --profile trabalho login
hubla-cli --profile trabalho --json status
```

## Descoberta antes da execução

Consulte o catálogo em vez de adivinhar nomes ou parâmetros:

```bash
hubla-cli --json schema
hubla-cli --json schema sales
hubla-cli --json schema sales list
```

O catálogo marca cada operação com `mutating: true` ou `false` e descreve os parâmetros em `snake_case`.

## Leituras comuns

```bash
hubla-cli --json account show
hubla-cli --json sales list --page-size 25
hubla-cli --json sales list --search cliente@example.com
hubla-cli --json sales get INVOICE_ID
hubla-cli --json refunds list
hubla-cli --json refunds get REFUND_ID
hubla-cli --json subscriptions list --page-size 25
hubla-cli --json subscriptions get SUBSCRIPTION_ID
hubla-cli --json products list
hubla-cli --json products offers PRODUCT_ID
hubla-cli --json products cohorts PRODUCT_ID
hubla-cli --json members list --product-id PRODUCT_ID
hubla-cli --json finance balance
```

Datas devem ser ISO 8601 com o fuso necessário para a pergunta do usuário:

```bash
hubla-cli --json sales list \
  --start-date 2026-01-01T00:00:00-03:00 \
  --end-date 2026-01-31T23:59:59-03:00
```

## Cobertura completa

Use `call` para qualquer método público exibido por `schema`. O objeto de parâmetros usa os nomes exatamente como aparecem no catálogo:

```bash
hubla-cli --json call analytics net_revenue \
  --params '{"start_date":"2026-01-01T00:00:00-03:00","end_date":"2026-01-31T23:59:59-03:00","period":"daily"}'
```

Para exportação binária, `--output` é obrigatório. Escolha um caminho protegido:

```bash
hubla-cli --json call sales export \
  --params '{"offer_ids":["OFFER_ID"],"has_selected_all":false}' \
  --confirm --output ./vendas.xlsx
```

Use `api` apenas quando o recurso ainda não estiver no catálogo e quando o contrato exato da rota oficial estiver confirmado. O CLI bloqueia hosts externos. Toda chamada raw diferente de GET exige `--confirm`.

## Operações que alteram dados

`--confirm` é uma autorização para uma ação específica, não uma opção para tentar fazer um comando funcionar.

Antes de qualquer operação com `mutating: true`:

1. Leia o registro exato e valide conta, IDs, valores, moeda, datas e impacto.
2. Mostre ao usuário o alvo, o payload e o efeito esperado sem expor dados pessoais desnecessários.
3. Aguarde confirmação explícita para essa ação exata.
4. Execute uma vez com `--confirm`.
5. Leia novamente o mesmo alvo e compare o estado retornado.

Exemplo:

```bash
hubla-cli --json sales get INVOICE_ID
hubla-cli --json sales refund INVOICE_ID --confirm
hubla-cli --json sales get INVOICE_ID
```

Não repita automaticamente reembolsos, saques, cancelamentos, alterações de acesso, mudanças de produto/oferta/turma, convites ou qualquer escrita após timeout, erro 5xx ou resposta ambígua. Pare e verifique o estado primeiro.

## Regras de privacidade e integridade

- Use somente a conta e o escopo autorizados pelo usuário.
- Não imprima nem salve senha, token, cabeçalho `Authorization`, cookie, CAPTCHA ou código de MFA.
- Minimize e redija e-mail, telefone, documento e outros dados pessoais nas respostas.
- Não trate página vazia ou erro da Hubla como zero vendas, zero saldo ou ausência de acesso.
- Paginação deve continuar até o total declarado pela resposta ou até uma página vazia, conforme o contrato do endpoint.
- Preserve IDs, datas, moedas, status e valores literalmente; não os “corrija” por suposição.
- Se a conta exigir CAPTCHA ou MFA que o CLI não conclua, use o fluxo oficial do portal Hubla. Não tente contornar a proteção.
- O CLI usa APIs do portal que podem mudar. Em 404 ou 422, confira a versão instalada e o catálogo antes de propor uma rota raw.

## Interface humana

Quando o usuário quiser navegar sem montar comandos, abra a TUI de consultas:

```bash
hubla-cli tui
```

A TUI é somente leitura. Para automação e agentes, mantenha `--json` para receber o envelope estável `{ "ok": true, "data": ... }` ou `{ "ok": false, "error": ... }`.
