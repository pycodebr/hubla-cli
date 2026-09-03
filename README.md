# Hubla CLI

[![CI](https://github.com/pycodebr/hubla-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/pycodebr/hubla-cli/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Use sua conta Hubla pelo terminal ou por qualquer agente de IA com acesso ao computador.

O Hubla CLI reúne autenticação, vendas, reembolsos, assinaturas, produtos, ofertas, turmas, membros, métricas, finanças, afiliados, cupons, vitrines, integrações e dados da conta em um único comando. Ele também instala uma [Agent Skill](https://agentskills.io/) para que o agente descubra os recursos e aplique as proteções corretas antes de agir.

> [!IMPORTANT]
> Este é um projeto comunitário e **não oficial**, sem vínculo, suporte ou endosso da Hubla. Ele usa contratos observados no portal web, que podem mudar. Use apenas em uma conta que você tem autorização para acessar.

## O que você recebe

- Instalação com um comando em Linux, macOS ou Windows.
- `hubla-cli login` com a senha mascarada por asteriscos (`*`).
- Senha usada apenas durante o login e nunca salva pelo CLI.
- Token renovável no cofre do sistema quando disponível; fallback em arquivo privado do usuário.
- TUI interativa e somente leitura para quem não quer montar comandos.
- Saída humana com tabelas e saída `--json` estável para agentes e automações.
- Catálogo executável com todos os recursos, parâmetros e indicação de risco.
- Operações de escrita bloqueadas até receberem `--confirm` explicitamente.
- Skill compatível com o padrão aberto Agent Skills e instalada junto com o CLI.

## Instalação em agentes de IA

Funciona com **Claude Code, Codex, Hermes, OpenClaw, Antigravity (comando `agy`), OpenCode, Pi e outros agentes compatíveis com Agent Skills**.

### Prompt para copiar

Cole o texto abaixo no seu agente:

```text
Instale o Hubla CLI deste repositório público: https://github.com/pycodebr/hubla-cli

1. Detecte se o computador usa Linux, macOS ou Windows.
2. No Linux/macOS, execute:
   curl -fsSL https://raw.githubusercontent.com/pycodebr/hubla-cli/main/install.sh | bash
3. No Windows PowerShell, execute:
   irm https://raw.githubusercontent.com/pycodebr/hubla-cli/main/install.ps1 | iex
4. Verifique com `hubla-cli --version`.
5. Garanta que a skill foi instalada executando `hubla-cli --json skill install --agent auto` e confirme com `hubla-cli --json skill status --agent auto`.
6. Depois, abra `hubla-cli login` em um terminal interativo e me deixe digitar o e-mail e a senha. Não peça, capture, imprima nem salve minha senha no chat ou em arquivos. A senha deve aparecer apenas como asteriscos no terminal.
7. Confirme a conexão com `hubla-cli --json status` e passe a usar a skill `hubla-cli` para atender meus pedidos sobre a minha conta Hubla.
8. Antes de qualquer reembolso, saque, cancelamento, alteração de acesso ou outra escrita, mostre o alvo e o efeito, peça minha confirmação específica e só então use `--confirm`. Depois, leia o mesmo alvo novamente para verificar o resultado.
```

O instalador sempre grava uma cópia em `~/.agents/skills/hubla-cli`, o caminho compartilhado pelo padrão Agent Skills. Quando detecta um agente com diretório próprio, também instala ali. Uma skill existente, modificada manualmente ou localizada em diretório simbólico não é sobrescrita automaticamente.

## Instalação no terminal

Requisito: **Python 3.10 ou superior**.

### Linux e macOS

```bash
curl -fsSL https://raw.githubusercontent.com/pycodebr/hubla-cli/main/install.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/pycodebr/hubla-cli/main/install.ps1 | iex
```

Os scripts criam um ambiente Python isolado no diretório do usuário, instalam `hubla-cli` a partir deste repositório, adicionam o comando ao `PATH` do usuário e instalam a skill. Não precisam de acesso administrativo.

Se quiser revisar antes de executar, abra [install.sh](install.sh) ou [install.ps1](install.ps1).

### Instalação manual para desenvolvedores

```bash
git clone https://github.com/pycodebr/hubla-cli.git
cd hubla-cli
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
hubla-cli skill install --agent auto
```

No Windows, ative com `.venv\Scripts\Activate.ps1`.

## Login

Depois da instalação:

```bash
hubla-cli login
```

O terminal pede o e-mail e a senha. Cada caractere da senha aparece como `*`:

```text
E-mail da conta Hubla: voce@exemplo.com
Senha: ************
```

O CLI valida a sessão antes de salvá-la. A senha não vai para arquivo, cofre, log ou repositório. Apenas o token renovável é persistido:

- macOS e Windows: cofre nativo quando o backend do sistema está disponível;
- Linux com Secret Service: cofre do sistema;
- fallback: arquivo do perfil com permissão `0600` dentro do diretório de configuração do usuário.

Confira a conexão:

```bash
hubla-cli status
hubla-cli --json status
```

Saia e apague a sessão local:

```bash
hubla-cli logout
```

Se a autenticação vier de variáveis de ambiente, `logout` não declara sucesso: remova as variáveis no processo ou no gerenciador de segredos que iniciou o CLI.

Contas com CAPTCHA ou MFA não suportado devem concluir a verificação pelo portal oficial. O CLI não tenta contornar essas proteções.

## TUI interativa

Rode sem argumentos em um terminal interativo ou use:

```bash
hubla-cli tui
```

A TUI oferece um menu visual para conta, vendas, produtos, assinaturas e saldo. Ela é **somente leitura**: nenhuma ação financeira, destrutiva ou de acesso aparece no menu.

## Uso rápido

```bash
# Conta conectada
hubla-cli account show

# Vendas recentes
hubla-cli sales list --page-size 25

# Buscar uma venda por e-mail
hubla-cli sales list --search cliente@example.com

# Produtos, ofertas e turmas
hubla-cli products list
hubla-cli products offers PRODUCT_ID
hubla-cli products cohorts PRODUCT_ID

# Assinaturas e membros
hubla-cli subscriptions list --page-size 25
hubla-cli members list --product-id PRODUCT_ID

# Saldo
hubla-cli finance balance
```

Para agentes e scripts, coloque `--json` antes do grupo:

```bash
hubla-cli --json sales list --page-size 25
```

Resposta de sucesso:

```json
{"ok": true, "data": {"items": []}}
```

Resposta de erro:

```json
{"ok": false, "error": {"type": "CredentialError", "message": "..."}}
```

## Todos os comandos

### Comandos principais

| Comando | Função |
| --- | --- |
| `login` | Autentica de modo interativo e salva somente o token renovável. |
| `logout` | Remove a sessão do perfil atual. |
| `status` | Testa a sessão e lê a conta conectada. |
| `doctor` | Verifica Python, configuração pública, credenciais e acesso à conta. |
| `tui` | Abre a interface interativa somente leitura. |
| `schema` | Mostra recursos, operações, parâmetros e se há alteração de estado. |
| `call` | Executa qualquer método público do catálogo. |
| `api` | Acesso avançado a uma rota relativa em um host Hubla permitido. |
| `sales` | Atalhos para vendas e faturas. |
| `refunds` | Atalhos para solicitações de reembolso. |
| `subscriptions` | Atalhos para assinaturas. |
| `products` | Atalhos para produtos, ofertas e turmas. |
| `members` | Atalhos para membros e convites. |
| `analytics` | Atalhos para indicadores. |
| `finance` | Atalhos para saldo e movimentações. |
| `account` | Atalhos para negócio e perfil. |
| `skill` | Instala ou verifica a skill nos agentes. |

Opções globais:

```text
--profile, -p NOME   Seleciona uma conta local
--json               Ativa o envelope JSON estável
--no-color           Desativa cores
--version            Mostra a versão
--help               Mostra a ajuda
```

### Atalhos por grupo

| Grupo | Subcomandos documentados |
| --- | --- |
| `sales` | `sales list`, `sales get`, `sales summaries`, `sales refund` |
| `refunds` | `refunds list`, `refunds get`, `refunds accept`, `refunds reject` |
| `subscriptions` | `subscriptions list`, `subscriptions get` |
| `products` | `products list`, `products get`, `products offers`, `products cohorts` |
| `members` | `members list`, `members deactivated`, `members pending` |
| `analytics` | `analytics get` |
| `finance` | `finance balance`, `finance statement`, `finance movements` |
| `account` | `account show`, `account profile` |
| `skill` | `skill install`, `skill status` |

Cada nível tem ajuda própria:

```bash
hubla-cli --help
hubla-cli sales --help
hubla-cli sales list --help
```

## Catálogo completo para agentes

Os atalhos cobrem o uso diário. O comando `call` cobre toda a biblioteca: afiliados, cupons, vitrines, integrações, grupos, configurações de produtos, trial, parcelas, colaboradores e outras operações.

Descubra antes de executar:

```bash
hubla-cli --json schema
hubla-cli --json schema products
hubla-cli --json schema products list_offers
```

Execute com parâmetros em `snake_case`:

```bash
hubla-cli --json call products list_offers \
  --params '{"product_id":"PRODUCT_ID","page_size":100}'
```

A [referência completa de operações](docs/command-reference.md) enumera todos os métodos disponíveis. O [mapa de API](docs/api-map.md) documenta os contratos conhecidos do portal.

## Datas, ofertas e paginação

Use datas ISO 8601 com fuso explícito quando a pergunta depende do dia comercial:

```bash
hubla-cli --json sales list \
  --start-date 2026-01-01T00:00:00-03:00 \
  --end-date 2026-01-31T23:59:59-03:00 \
  --status paid
```

Sem `--offer-id`, o cliente descobre as ofertas visíveis da conta. Para um recorte exato, informe cada ID:

```bash
hubla-cli --json sales list --offer-id OFFER_ID
```

Os comandos de lista expõem `--page` e `--page-size`. Um agente que precisa de todos os registros deve paginar até reconciliar o total declarado pela resposta ou receber uma página vazia.

## Operações que alteram a conta

Operações mutáveis são bloqueadas por padrão:

```bash
hubla-cli --json sales refund INVOICE_ID
```

O comando acima falha sem `--confirm`. Fluxo correto:

```bash
# 1. Ler e conferir o alvo
hubla-cli --json sales get INVOICE_ID

# 2. Executar uma vez após a confirmação específica do usuário
hubla-cli --json sales refund INVOICE_ID --confirm

# 3. Ler novamente e validar o estado
hubla-cli --json sales get INVOICE_ID
```

O mesmo princípio vale para saques, cancelamentos, convites, alterações de acesso, produtos, ofertas, turmas, colaboradores, integrações e cupons. Não repita escritas automaticamente depois de timeout, erro 5xx ou resposta ambígua.

## Exportações

Respostas binárias exigem `--output` para evitar que dados de uma exportação sejam despejados no terminal ou no log do agente:

```bash
hubla-cli --json call sales export \
  --params '{"offer_ids":["OFFER_ID"],"has_selected_all":false}' \
  --confirm \
  --output ./vendas.xlsx
```

O CLI não substitui um arquivo existente sem `--force`.

## Perfis para mais de uma conta

```bash
hubla-cli --profile pessoal login
hubla-cli --profile empresa login

hubla-cli --profile empresa --json sales list
hubla-cli --profile pessoal logout
```

O nome do perfil aceita letras, números, ponto, hífen e sublinhado. Cada perfil mantém seu próprio token.

## Skill e compatibilidade com agentes

```bash
hubla-cli --json skill install --agent auto
hubla-cli --json skill status --agent auto
```

Alvos suportados:

| Agente | Local global usado |
| --- | --- |
| Codex, OpenCode e Pi | `~/.agents/skills/hubla-cli` |
| Claude Code | `~/.claude/skills/hubla-cli` |
| Hermes | `$HERMES_HOME/skills/hubla-cli` ou `~/.hermes/skills/hubla-cli` |
| OpenClaw | `$OPENCLAW_STATE_DIR/skills/hubla-cli` ou `~/.openclaw/skills/hubla-cli` |
| Antigravity | `~/.gemini/config/skills/hubla-cli` |
| Outros compatíveis | `~/.agents/skills/hubla-cli` |

Use `--agent claude`, `--agent hermes`, `--agent openclaw`, `--agent antigravity` (ou `--agent agy`), `--agent codex`, `--agent opencode`, `--agent pi`, `--agent generic` ou `--agent all` para escolher explicitamente.

O arquivo distribuído está em [`skills/hubla-cli/SKILL.md`](skills/hubla-cli/SKILL.md), portanto também pode ser revisado antes da instalação.

## API avançada

Quando um recurso ainda não estiver encapsulado, `api` aceita apenas um serviço conhecido e um caminho relativo. URLs completas e hosts externos são rejeitados.

```bash
# GET não exige confirmação
hubla-cli --json api web GET /business

# Toda chamada raw diferente de GET exige confirmação
hubla-cli --json api web POST /rota-conhecida \
  --body '{"campo":"valor"}' \
  --confirm
```

Serviços: `web`, `product`, `members_area`, `access`, `creators`, `crm`, `data`, `pay`, `member_portal`, `certificate` e `functions`.

## Uso como biblioteca Python

```python
from hubla_cli import HublaClient

client = HublaClient.from_profile()
products = client.products.list(page_size=100)
sales = client.sales.list(statuses=["paid"], page_size=25)
```

Toda escrita na biblioteca também exige `confirm=True`.

## Variáveis de ambiente

Úteis em automações controladas e ambientes sem armazenamento local:

| Variável | Uso |
| --- | --- |
| `HUBLA_EMAIL` | E-mail da conta. |
| `HUBLA_PASSWORD` | Senha somente em ambiente efêmero; prefira `login`. |
| `HUBLA_REFRESH_TOKEN` | Token renovável fornecido externamente. |
| `HUBLA_SIGN_KEY` | Sobrescreve a configuração pública descoberta automaticamente. |
| `HUBLA_TIMEOUT` | Timeout em segundos. |
| `HUBLA_REQUEST_ID` | Ativa ou desativa `x-request-id`. |
| `HUBLA_CLI_AGENT` | Alvo usado pelo instalador de skill. |
| `HUBLA_CLI_VERSION` | Versão publicada instalada pelos scripts. |
| `HUBLA_CLI_HOME` | Diretório do ambiente isolado do instalador. |
| `HUBLA_CLI_BIN_DIR` | Diretório dos wrappers do comando. |

Não coloque credenciais no repositório nem em comandos que ficam no histórico do shell.

## Atualização

Rode novamente o instalador do seu sistema. Ele atualiza o ambiente isolado e a skill gerenciada.

## Solução de problemas

### `hubla-cli: command not found`

No Linux ou macOS, abra um novo terminal. Para a sessão atual:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

No Windows, abra um novo PowerShell para carregar o `PATH` de usuário atualizado.

### Login inválido

Confira o e-mail e a senha no portal Hubla. Muitas tentativas podem bloquear temporariamente o login. CAPTCHA ou MFA adicional deve ser concluído no fluxo oficial.

### A API retornou 404 ou 422

Atualize o CLI. Se persistir, o contrato do portal pode ter mudado. Abra uma issue sem incluir e-mail, token, senha, cookie, payload pessoal ou cabeçalhos de autenticação.

### A skill não apareceu

```bash
hubla-cli --json skill status --agent auto
hubla-cli --json skill install --agent NOME_DO_AGENTE
```

Alguns agentes carregam novas skills apenas em uma sessão nova.

## Desenvolvimento

```bash
git clone https://github.com/pycodebr/hubla-cli.git
cd hubla-cli
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest --cov=hubla_cli --cov-report=term --cov-fail-under=80 -q
ruff check .
ruff format --check .
mypy src/hubla_cli --ignore-missing-imports --check-untyped-defs
python -m build
```

Leia [CONTRIBUTING.md](CONTRIBUTING.md) antes de enviar mudanças e [SECURITY.md](SECURITY.md) antes de relatar uma vulnerabilidade.

## Licença

[MIT](LICENSE). Hubla e demais marcas citadas pertencem aos seus respectivos titulares.
