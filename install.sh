#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY_URL="https://github.com/pycodebr/hubla-cli"
VERSION="${HUBLA_CLI_VERSION:-0.1.0}"
PACKAGE_URL="${HUBLA_CLI_PACKAGE_URL:-${REPOSITORY_URL}/archive/refs/tags/v${VERSION}.zip}"
INSTALL_ROOT="${HUBLA_CLI_HOME:-${HOME}/.local/share/hubla-cli}"
BIN_DIR="${HUBLA_CLI_BIN_DIR:-${HOME}/.local/bin}"
AGENT="${HUBLA_CLI_AGENT:-auto}"

info() {
  printf '\033[1;36m%s\033[0m\n' "$1"
}

fail() {
  printf '\033[1;31mErro:\033[0m %s\n' "$1" >&2
  exit 1
}

python_is_compatible() {
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    >/dev/null 2>&1
}

find_python() {
  if [[ -n "${HUBLA_CLI_PYTHON:-}" ]]; then
    python_is_compatible "${HUBLA_CLI_PYTHON}" || \
      fail "HUBLA_CLI_PYTHON precisa apontar para Python 3.10 ou superior."
    printf '%s\n' "${HUBLA_CLI_PYTHON}"
    return
  fi

  local candidate
  for candidate in python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1 && \
      python_is_compatible "${candidate}"; then
      command -v "${candidate}"
      return
    fi
  done
  fail "Python 3.10 ou superior não foi encontrado. Instale o Python e tente novamente."
}

append_user_path() {
  local profile="$1"
  local marker="# hubla-cli user path"
  local found="0"
  local quoted_bin
  touch "${profile}"
  while IFS= read -r line; do
    if [[ "${line}" == "${marker}" ]]; then
      found="1"
      break
    fi
  done < "${profile}"
  if [[ "${found}" == "0" ]]; then
    printf -v quoted_bin '%q' "${BIN_DIR}"
    printf '\n%s\nexport PATH=%s:$PATH\n' \
      "${marker}" "${quoted_bin}" >> "${profile}"
  fi
}

ensure_user_path() {
  case ":${PATH}:" in
    *":${BIN_DIR}:"*) return ;;
  esac

  append_user_path "${HOME}/.profile"
  case "${SHELL:-}" in
    */zsh|zsh) append_user_path "${HOME}/.zprofile" ;;
    */bash|bash) append_user_path "${HOME}/.bash_profile" ;;
  esac
}

PYTHON_BIN="$(find_python)"
VENV_DIR="${INSTALL_ROOT}/venv"

info "Instalando Hubla CLI em ${INSTALL_ROOT}"
mkdir -p "${INSTALL_ROOT}" "${BIN_DIR}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --disable-pip-version-check --upgrade pip
"${VENV_DIR}/bin/python" -m pip install \
  --disable-pip-version-check \
  --upgrade \
  "${PACKAGE_URL}"

for command_name in hubla-cli hubla; do
  destination="${BIN_DIR}/${command_name}"
  if [[ -e "${destination}" && ! -L "${destination}" ]]; then
    fail "${destination} já existe e não é um link gerenciado."
  fi
  ln -sfn "${VENV_DIR}/bin/${command_name}" "${destination}"
done

if [[ "${HUBLA_CLI_SKIP_SKILL:-0}" != "1" ]]; then
  info "Instalando a skill para agentes de IA"
  "${VENV_DIR}/bin/hubla-cli" --json skill install --agent "${AGENT}"
fi

ensure_user_path

info "Hubla CLI instalado."
printf 'Executável: %s\n' "${BIN_DIR}/hubla-cli"
printf 'Próximo passo: hubla-cli login\n'
if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
  printf 'Para usar nesta sessão agora: export PATH="%s:$PATH"\n' "${BIN_DIR}"
fi
