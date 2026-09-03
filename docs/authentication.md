# Autenticação e credenciais

## Fluxo de login

1. `hubla-cli login` pede o e-mail.
2. O prompt de senha usa modo password do `prompt_toolkit`, exibindo um asterisco por caractere.
3. O cliente obtém a configuração pública do Firebase em `https://app.hub.la/__/firebase/init.json`.
4. E-mail e senha são enviados diretamente ao endpoint Firebase usado pelo portal.
5. O ID token é usado para validar uma leitura de `/business`.
6. Somente depois dessa validação o token renovável é persistido.
7. A variável local que contém a senha é descartada ao sair do fluxo.

O CLI não recebe nem salva a senha em opção de linha de comando. Isso evita que ela apareça no histórico do shell ou na lista de processos.

## Armazenamento

A ordem é:

1. cofre suportado pela biblioteca `keyring` e pelo sistema operacional;
2. arquivo privado no diretório retornado por `platformdirs`.

O arquivo contém e-mail, tipo de armazenamento e, apenas no fallback, token renovável. Em POSIX, o diretório recebe `0700` e o arquivo `0600`. A gravação usa arquivo temporário e `os.replace` para evitar perfil parcial.

A senha nunca faz parte do formato salvo.

## Renovação

O ID token fica apenas em memória. Antes da expiração, o cliente usa o token renovável para obter outro. Depois de uma resposta 401, faz uma única renovação forçada e uma única repetição da requisição.

O transporte não implementa repetição automática genérica para timeout ou erro 5xx. Isso evita duplicar operações financeiras ou destrutivas.

## Perfis

Cada `--profile NOME` usa metadados e entrada de cofre próprios. Nomes são validados e não podem conter separador de diretório, o que impede escape do diretório de configuração.

## Ambientes automatizados

`HUBLA_REFRESH_TOKEN` é a opção preferida para um ambiente efêmero. `HUBLA_EMAIL` e `HUBLA_PASSWORD` também são aceitos, mas o operador deve usar um gerenciador de segredos e impedir que os valores entrem em logs.

`HUBLA_SIGN_KEY` é opcional e apenas substitui a configuração pública descoberta. Uma chave de configuração Firebase exposta ao navegador não substitui as credenciais da conta.

## Logout

`hubla-cli logout` remove primeiro a entrada correspondente do cofre e só então apaga os metadados do perfil. Se o cofre estiver bloqueado ou falhar, o comando retorna erro e preserva o perfil para não declarar um logout que não aconteceu. O comando não revoga sessões em outros dispositivos; para isso, use os controles oficiais da conta.

Quando a autenticação vem de `HUBLA_REFRESH_TOKEN` ou de `HUBLA_EMAIL`/`HUBLA_PASSWORD`, `logout` retorna erro e orienta a remover essas variáveis do processo. O CLI não pode apagar o segredo mantido pelo ambiente que o iniciou.
