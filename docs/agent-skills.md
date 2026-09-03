# Skills para agentes de IA

O Hubla CLI distribui uma skill no formato aberto [Agent Skills](https://agentskills.io/). Ela contém instruções operacionais, não credenciais nem código executado automaticamente.

## Instalação automática

```bash
hubla-cli --json skill install --agent auto
hubla-cli --json skill status --agent auto
```

Os scripts de instalação verificam Python, `venv` e `pip`. Quando Python 3.10+ não está disponível, eles instalam Python 3.12 no escopo do usuário por meio de uma versão fixada do uv, sem exigir acesso administrativo.

`auto` sempre instala em `~/.agents/skills/hubla-cli` e adiciona diretórios nativos quando detectados. O resultado JSON lista cada destino e um dos estados:

- `installed`: primeira instalação;
- `updated`: cópia gerenciada atualizada;
- `up-to-date`: conteúdo já corresponde à versão instalada;
- `conflict`: já existe uma skill homônima não gerenciada e nada foi alterado.

`--force` substitui um conflito, portanto só deve ser usado após revisar e decidir descartar a cópia existente.

O marcador gerenciado registra formato, origem, versão e SHA-256 do `SKILL.md`. Marcador inválido, conteúdo alterado pelo usuário ou diretório simbólico vira conflito e não é sobrescrito automaticamente.

## Handoff seguro de login

O terminal interno de um agente normalmente não expõe um TTY para o usuário. Por isso, o agente deve instalar o CLI e a skill, mostrar `hubla-cli login` e parar. O usuário executa esse comando em um terminal separado e responde `autenticado`. Somente então o agente roda `hubla-cli --json status`.

O login precisa acontecer no mesmo computador, usuário do sistema e ambiente em que o agente instalou o CLI. Em uma VPS, o comando deve ser executado por SSH na VPS. Containers, sandboxes e máquinas remotas não compartilham automaticamente o cofre ou o perfil local.

O usuário nunca deve enviar e-mail, senha, token ou código de autenticação pelo chat. O agente não deve executar `hubla-cli login` pelo próprio terminal interno nem tentar alimentar o prompt por argumento, variável, arquivo ou stdin.

## Compatibilidade verificada por convenção pública

| Harness | Caminho usado | Referência |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/<nome>/SKILL.md` | [Claude Code Skills](https://code.claude.com/docs/en/skills) |
| Codex | `~/.agents/skills/<nome>/SKILL.md` | [Codex Skills](https://developers.openai.com/codex/skills) |
| OpenCode | `~/.agents/skills/<nome>/SKILL.md` | [OpenCode Skills](https://opencode.ai/docs/skills/) |
| OpenClaw | `~/.agents/skills` e diretório de estado | [OpenClaw Skills](https://docs.openclaw.ai/tools/skills) |
| Antigravity (`agy`) | `~/.gemini/config/skills/<nome>/SKILL.md` | [Antigravity Skills](https://antigravity.google/docs/skills) |
| Pi | `~/.agents/skills/<nome>/SKILL.md` | [Pi Skills](https://pi.dev/docs/latest/skills) |
| Hermes | `$HERMES_HOME/skills/<nome>/SKILL.md` | [Hermes Skills](https://hermes-agent.nousresearch.com/docs) |

Harnesses que implementam Agent Skills e leem `~/.agents/skills` recebem a cópia genérica sem integração especial.

## Escopo e precedência

A instalação padrão é global para o usuário. Ela não altera a configuração do projeto atual nem concede ferramentas ao agente.

Se o harness tiver allowlist de skills, a skill ainda pode precisar ser habilitada nessa allowlist. Se a sessão já estava aberta, inicie uma sessão nova quando o agente não detectar a mudança.

## Atualização segura

O instalador grava `.hubla-cli-managed.json` ao lado de `SKILL.md`. Atualizações automáticas só tocam uma cópia cujo marcador é válido e cujo hash ainda corresponde ao conteúdo instalado. Uma pasta criada ou modificada manualmente pelo usuário permanece intacta.

A fonte revisável fica em:

```text
skills/hubla-cli/SKILL.md
```

A cópia empacotada em `src/hubla_cli/data/SKILL.md` é validada por teste para permanecer idêntica.
