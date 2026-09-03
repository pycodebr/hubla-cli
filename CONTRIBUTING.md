# Contribuindo

Contribuições são bem-vindas, principalmente correções de contratos, compatibilidade entre sistemas, testes e melhorias de acessibilidade da TUI.

Este projeto é comunitário e não oficial. Não envie dados reais de contas ou material proprietário do portal.

## Ambiente local

```bash
git clone https://github.com/pycodebr/hubla-cli.git
cd hubla-cli
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

No Windows:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Fluxo de mudança

1. Abra uma issue para mudanças grandes ou incompatíveis.
2. Escreva primeiro um teste que falhe pelo comportamento ausente.
3. Implemente a menor alteração necessária.
4. Atualize a documentação e a skill quando a interface pública mudar.
5. Rode todos os gates locais.
6. Abra um pull request pequeno, com motivação, risco e evidências de teste.

## Gates obrigatórios

```bash
pytest --cov=hubla_cli --cov-report=term --cov-fail-under=80 -q
ruff check .
ruff format --check .
mypy src/hubla_cli --ignore-missing-imports --check-untyped-defs
python scripts/generate_command_reference.py --check
python -m build
```

Não use uma conta real em testes automatizados. O pacote possui transportes falsos para validar método, rota, query, corpo e trava de confirmação sem rede.

## Alterações em rotas

As APIs do portal podem mudar. Para corrigir ou adicionar uma rota:

1. Confirme o contrato em uma sessão autorizada.
2. Registre apenas método, alias de serviço, caminho e formato sanitizado.
3. Adicione um método de recurso de alto nível.
4. Exija `confirm` se houver envio, exportação sensível ou alteração de estado.
5. Escreva teste para rota, quoting de IDs, payload e trava.
6. Atualize `docs/api-map.md`.
7. Nunca adicione captura com cookie, token, e-mail, telefone, documento ou resposta de produção.

## Estilo

- Python 3.10 ou superior.
- PEP 8, `snake_case` para funções e variáveis, `PascalCase` para classes.
- Type hints em interfaces públicas.
- Sem `shell=True`, `eval`, `exec` ou URL externa no transporte autenticado.
- Mensagens para usuário em PT-BR direto e com acentuação revisada.
- Commits no formato `tipo: descrição`, como `feat:`, `fix:`, `docs:` e `test:`.

## Skill

A skill existe em dois caminhos porque uma cópia entra no pacote Python:

- `skills/hubla-cli/SKILL.md`
- `src/hubla_cli/data/SKILL.md`

As duas devem permanecer idênticas. A suíte falha se houver divergência.

## Segurança

Vulnerabilidades não devem ser publicadas em issues. Siga [SECURITY.md](SECURITY.md).
