# Changelog

Todas as mudanças relevantes deste projeto serão registradas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [0.2.1] - 2026-09-04

### Adicionado

- Paginação reconciliada para vendas, assinaturas, ofertas, turmas e membros.
- Leitura de detalhe de turma e das seções da área de membros.
- Busca exata de membro por produto e e-mail, com detecção de resultado ambíguo ou filtro ignorado.
- Troca de turmas com confirmação explícita e readback do conjunto final.
- Snapshot normalizado das seções associadas a uma turma.

## [0.2.0] - 2026-09-04

### Adicionado

- `finance forecast` projeta o saldo disponível para saque em uma ou mais datas. Sem `--date`, compara o último dia do mês atual com o último dia do mês seguinte.
- `finance.all_movements` percorre os cursores do extrato financeiro e elimina movimentos repetidos pelo identificador.
- O resultado separa saldo já disponível, recebíveis com liberação prevista e liberação estimada da reserva de saldo.

### Segurança e integridade

- O cronograma de recebíveis precisa reconciliar exatamente com `receivableInCents`; divergências interrompem a projeção.
- A reserva usa o saldo atual como total obrigatório e informa que a distribuição por data é uma estimativa sujeita a novas vendas, reembolsos e chargebacks.
- O fuso `America/Sao_Paulo` é aplicado por padrão e o pacote inclui a base IANA para manter o mesmo comportamento no Windows.
- A etapa de auditoria de dependências atualiza o `pip` antes da análise para não manter vulnerabilidades do bootstrap da imagem de CI.

## [0.1.2] - 2026-09-03

### Corrigido

- Se um ambiente virtual não tiver `pip` e o `ensurepip` falhar, os instaladores agora recriam o ambiente com o Python gerenciado antes de abortar.
- O instalador do Windows habilita TLS 1.2 sem remover protocolos existentes, inclusive no subprocesso que instala o uv.
- A CI executa o bootstrap completo no Windows PowerShell 5.1, além do PowerShell moderno usado na matriz principal.

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

[Não lançado]: https://github.com/pycodebr/hubla-cli/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/pycodebr/hubla-cli/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/pycodebr/hubla-cli/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/pycodebr/hubla-cli/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/pycodebr/hubla-cli/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/pycodebr/hubla-cli/releases/tag/v0.1.0
