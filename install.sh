#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY_URL="https://github.com/pycodebr/hubla-cli"
VERSION="${HUBLA_CLI_VERSION:-0.1.2}"
PACKAGE_URL="${HUBLA_CLI_PACKAGE_URL:-${REPOSITORY_URL}/archive/refs/tags/v${VERSION}.zip}"
INSTALL_ROOT="${HUBLA_CLI_HOME:-${HOME}/.local/share/hubla-cli}"
BIN_DIR="${HUBLA_CLI_BIN_DIR:-${HOME}/.local/bin}"
AGENT="${HUBLA_CLI_AGENT:-auto}"
UV_VERSION="${HUBLA_CLI_UV_VERSION:-0.12.9}"
MANAGED_PYTHON_VERSION="${HUBLA_CLI_MANAGED_PYTHON_VERSION:-3.12}"
UV_BOOTSTRAP_DIR="${INSTALL_ROOT}/bootstrap"

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

uv_version_is_expected() {
  local output
  output="$("${1}" --version 2>/dev/null)" || return 1
  [[ "${output}" == "uv ${UV_VERSION}" || "${output}" == "uv ${UV_VERSION} "* ]]
}

find_uv() {
  if [[ -n "${HUBLA_CLI_UV:-}" ]]; then
    [[ -x "${HUBLA_CLI_UV}" ]] || \
      fail "HUBLA_CLI_UV precisa apontar para um executável uv válido."
    uv_version_is_expected "${HUBLA_CLI_UV}" || \
      fail "HUBLA_CLI_UV precisa executar uv ${UV_VERSION}."
    printf '%s\n' "${HUBLA_CLI_UV}"
    return
  fi

  local uv_path="${UV_BOOTSTRAP_DIR}/uv"
  if [[ "${HUBLA_CLI_FORCE_UV_INSTALL:-0}" != "1" ]] && \
    [[ -x "${uv_path}" ]] && uv_version_is_expected "${uv_path}"; then
    printf '%s\n' "${uv_path}"
    return
  fi

  local installer_url="https://astral.sh/uv/${UV_VERSION}/install.sh"
  info "Python compatível não encontrado. Instalando uv ${UV_VERSION}." >&2
  mkdir -p "${UV_BOOTSTRAP_DIR}"
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf "${installer_url}" | \
      env UV_UNMANAGED_INSTALL="${UV_BOOTSTRAP_DIR}" sh >&2
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- "${installer_url}" | \
      env UV_UNMANAGED_INSTALL="${UV_BOOTSTRAP_DIR}" sh >&2
  else
    fail "curl ou wget é necessário para instalar automaticamente o Python."
  fi

  [[ -x "${uv_path}" ]] || \
    fail "A instalação automática do uv não produziu um executável válido."
  uv_version_is_expected "${uv_path}" || \
    fail "O uv instalado não corresponde à versão ${UV_VERSION}."
  printf '%s\n' "${uv_path}"
}

managed_python() {
  local uv_bin
  local python_bin
  uv_bin="$(find_uv)"
  info "Instalando Python ${MANAGED_PYTHON_VERSION} sem acesso administrativo." >&2
  env UV_PYTHON_INSTALL_DIR="${INSTALL_ROOT}/python" UV_PYTHON_INSTALL_BIN=0 \
    "${uv_bin}" python install "${MANAGED_PYTHON_VERSION}" >&2 || \
    fail "Não foi possível instalar o Python gerenciado."
  python_bin="$(env UV_PYTHON_INSTALL_DIR="${INSTALL_ROOT}/python" UV_PYTHON_INSTALL_BIN=0 \
    "${uv_bin}" python find --managed-python "${MANAGED_PYTHON_VERSION}")" || \
    fail "Não foi possível localizar o Python gerenciado."
  python_is_compatible "${python_bin}" || \
    fail "O Python gerenciado instalado não é compatível."
  printf '%s\n' "${python_bin}"
}

find_python() {
  if [[ -n "${HUBLA_CLI_PYTHON:-}" ]]; then
    python_is_compatible "${HUBLA_CLI_PYTHON}" || \
      fail "HUBLA_CLI_PYTHON precisa apontar para Python 3.10 ou superior."
    printf '%s\n' "${HUBLA_CLI_PYTHON}"
    return
  fi

  if [[ "${HUBLA_CLI_FORCE_MANAGED_PYTHON:-0}" != "1" ]]; then
    local candidate
    for candidate in python3.13 python3.12 python3.11 python3.10 python3 python; do
      if command -v "${candidate}" >/dev/null 2>&1 && \
        python_is_compatible "${candidate}"; then
        command -v "${candidate}"
        return
      fi
    done
  fi

  managed_python
}

ensure_venv_pip() {
  local venv_python="$1"
  if "${venv_python}" -m pip --version >/dev/null 2>&1; then
    return 0
  fi
  "${venv_python}" -m ensurepip --upgrade >/dev/null 2>&1 || return 1
  "${venv_python}" -m pip --version >/dev/null 2>&1
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
    # shellcheck disable=SC2016 # Keep $PATH literal in the profile.
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
if ! "${PYTHON_BIN}" -m venv "${VENV_DIR}"; then
  info "O módulo venv não está disponível. Usando Python gerenciado pelo uv."
  PYTHON_BIN="$(managed_python)"
  "${PYTHON_BIN}" -m venv --clear "${VENV_DIR}" || \
    fail "Não foi possível criar o ambiente Python isolado."
fi
if ! ensure_venv_pip "${VENV_DIR}/bin/python"; then
  info "O pip não está disponível. Recriando o ambiente com Python gerenciado pelo uv."
  PYTHON_BIN="$(managed_python)"
  "${PYTHON_BIN}" -m venv --clear "${VENV_DIR}" || \
    fail "Não foi possível recriar o ambiente Python isolado."
  ensure_venv_pip "${VENV_DIR}/bin/python" || \
    fail "Não foi possível instalar o pip no ambiente isolado."
fi
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
printf 'Próximo passo do usuário, em terminal separado: hubla-cli login\n'
printf 'Se um agente executou este script, ele deve parar e aguardar a resposta "autenticado".\n'
if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
  # shellcheck disable=SC2016 # Show a command with the caller's future $PATH.
  printf 'Para usar nesta sessão agora: export PATH="%s:$PATH"\n' "${BIN_DIR}"
fi
