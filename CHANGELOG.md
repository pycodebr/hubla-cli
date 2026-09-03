# Changelog

Todas as mudanças relevantes deste projeto serão registradas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [0.1.1] - 2026-09-03

### Corrigido

- O prompt para agentes agora separa instalação e autenticação: o agente instala o CLI e a skill, mostra `hubla-cli login` e aguarda o usuário concluir o login em outro terminal.
- A skill proíbe executar o login pelo terminal interno do agente ou receber credenciais pelo chat.
- A documentação esclarece que terminal e agente precisam compartilhar computador, usuário do sistema e ambiente.
- Os instaladores agora verificam Python, `venv` e `pip` e instalam automaticamente Python 3.12 via uv quando necessário.

## [0.1.0] - 2026-09-03

### Adicionado

- Cliente Python para recursos de conta, vendas, reembolsos, assinaturas, produtos, membros, métricas, finanças, afiliados, cupons, vitrines, grupos e integrações.
- Login interativo com senha mascarada por asteriscos e persistência somente do token renovável.
- TUI Rich/prompt_toolkit somente leitura.
- Saída JSON estável, catálogo executável e invocação genérica de recursos.
- Travas explícitas para operações mutáveis e exportações sensíveis.
- Instaladores Bash e PowerShell em escopo de usuário.
- Agent Skill com instalação automática para harnesses compatíveis.
- Testes, lint, build e CI multiplataforma.

[Não lançado]: https://github.com/pycodebr/hubla-cli/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/pycodebr/hubla-cli/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/pycodebr/hubla-cli/releases/tag/v0.1.0
