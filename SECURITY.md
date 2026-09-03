# Política de segurança

O Hubla CLI é um projeto comunitário e não oficial. Ele acessa dados financeiros, comerciais e pessoais da conta autorizada pelo usuário, portanto qualquer vulnerabilidade deve ser tratada como sensível.

## Versões suportadas

Enquanto o projeto estiver na série `0.x`, somente a versão mais recente recebe correções de segurança.

## Como relatar

Não abra uma issue pública com detalhes exploráveis ou dados de conta. Use o recurso **Report a vulnerability** em:

https://github.com/pycodebr/hubla-cli/security/advisories/new

Inclua:

- versão do CLI e sistema operacional;
- impacto e pré-condições;
- passos mínimos para reproduzir com dados fictícios;
- correção sugerida, se houver.

Nunca inclua senha, token, cookie, CAPTCHA, código de MFA, cabeçalho `Authorization`, resposta com dados pessoais ou exportação real.

## Modelo de segurança

### Credenciais

- `hubla-cli login` lê a senha em um prompt mascarado por asteriscos.
- A senha existe apenas durante o processo de autenticação e não é persistida pelo CLI.
- O token renovável usa o cofre nativo quando há um backend funcional.
- O fallback grava o token no diretório de configuração do usuário; em sistemas POSIX, diretório e arquivo recebem permissões `0700` e `0600`.
- Exportações binárias exigem um caminho explícito, usam `0600` em POSIX e não substituem arquivos sem `--force`.
- Logout e troca de conta falham de modo fechado quando o cofre não confirma a remoção da sessão anterior.
- Tokens nunca entram na skill instalada.
- Erros conhecidos têm campos sensíveis redigidos antes de chegar à saída.

O fallback em arquivo protege contra outros usuários comuns do mesmo sistema, mas não contra administrador, root, malware executando como o usuário ou comprometimento do disco. Use criptografia de disco e um cofre nativo quando o risco exigir.

### Rede

O cliente aceita apenas aliases de serviços Hubla definidos no código. O comando raw rejeita URL absoluta, URL relativa a protocolo e host externo. Isso evita usar uma sessão autenticada para enviar credenciais a um destino arbitrário.

### Alterações de estado

Métodos que alteram conta, dinheiro, acesso, catálogo, assinatura, membro, integração ou configuração exigem `confirm=True` na biblioteca e `--confirm` no CLI. Exportações sensíveis também são confirmadas.

Essa trava reduz acidentes, mas não substitui autorização. O operador ou agente deve ler o alvo, validar IDs e payload, obter confirmação específica, executar uma vez e fazer leitura posterior do mesmo alvo.

### Agentes de IA

A skill orienta o agente a:

- não receber senha pelo chat;
- usar `--json` e consultar `schema` antes de agir;
- minimizar dados pessoais;
- não repetir escritas automaticamente;
- pedir confirmação específica antes de `--confirm`;
- verificar toda mudança com uma leitura posterior.

A instalação da skill não concede acesso ao terminal nem ignora as políticas de aprovação do agente. O usuário continua responsável pelas permissões concedidas ao harness.

O atualizador da skill valida propriedade, formato e hash do marcador gerenciado. Conteúdo modificado, marcador estrangeiro ou diretório simbólico gera conflito em vez de sobrescrita.

## Limites conhecidos

- As APIs usadas pelo portal podem mudar sem aviso.
- Contas com CAPTCHA ou MFA adicional podem exigir o portal oficial.
- Um token renovável equivale a uma sessão sensível da conta enquanto for válido.
- O CLI não implementa isolamento contra um processo malicioso já executando como o mesmo usuário.
