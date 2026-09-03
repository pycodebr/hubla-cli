## O que mudou


## Risco

- [ ] Somente leitura
- [ ] Exportação sensível
- [ ] Alteração de estado protegida por `confirm`

## Verificação

- [ ] Teste novo falhou antes da implementação.
- [ ] `pytest -q`
- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `python scripts/generate_command_reference.py --check`
- [ ] `python -m build`
- [ ] Nenhuma credencial ou dado real foi incluído.
- [ ] README, mapa de API e skill foram atualizados quando necessário.
