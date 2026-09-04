"""Command-line entry point for Hubla CLI."""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from hubla_cli.auth import FirebaseConfigResolver, HublaAuth
from hubla_cli.catalog import build_catalog, invoke_resource
from hubla_cli.client import HublaClient
from hubla_cli.credentials import CredentialStore
from hubla_cli.errors import CommandError, HublaError, HublaHttpError
from hubla_cli.prompts import prompt_email, prompt_password
from hubla_cli.resources.finance import DEFAULT_FINANCE_TIMEZONE
from hubla_cli.skills import install_skill, skill_status
from hubla_cli.transport import BASE_URLS
from hubla_cli.tui import render_data, run_tui
from hubla_cli.version import __version__

app = typer.Typer(
    name="hubla-cli",
    help="Use sua conta Hubla no terminal ou em agentes de IA.",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
    rich_markup_mode="rich",
)

sales_app = typer.Typer(help="Vendas, faturas e reembolsos de vendas.")
refunds_app = typer.Typer(help="Solicitações de reembolso.")
subscriptions_app = typer.Typer(help="Assinaturas da conta.")
products_app = typer.Typer(help="Produtos, ofertas e turmas.")
members_app = typer.Typer(help="Membros e acessos.")
analytics_app = typer.Typer(help="Indicadores da conta.")
finance_app = typer.Typer(help="Saldo e movimentações financeiras.")
account_app = typer.Typer(help="Dados da conta.")
skill_app = typer.Typer(help="Instala e verifica a skill para agentes de IA.")

app.add_typer(sales_app, name="sales")
app.add_typer(refunds_app, name="refunds")
app.add_typer(subscriptions_app, name="subscriptions")
app.add_typer(products_app, name="products")
app.add_typer(members_app, name="members")
app.add_typer(analytics_app, name="analytics")
app.add_typer(finance_app, name="finance")
app.add_typer(account_app, name="account")
app.add_typer(skill_app, name="skill")


@dataclass
class RuntimeContext:
    """Global CLI settings inherited by every command."""

    profile: str
    json_output: bool
    console: Console


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"hubla-cli {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    ctx: typer.Context,
    profile: str = typer.Option(
        "default",
        "--profile",
        "-p",
        help="Perfil local para usar mais de uma conta.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Retorna um envelope JSON estável para automações e agentes.",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Desativa cores na saída humana.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Mostra a versão instalada.",
    ),
) -> None:
    """Use sua conta Hubla no terminal ou em agentes de IA."""
    del version
    runtime = RuntimeContext(
        profile=profile,
        json_output=json_output,
        console=Console(no_color=no_color),
    )
    ctx.obj = runtime
    if ctx.invoked_subcommand is None:
        if not sys.stdin.isatty():
            typer.echo(ctx.get_help())
            return
        _execute(ctx, lambda: run_tui(get_client(profile), console=runtime.console))


def _runtime(ctx: typer.Context) -> RuntimeContext:
    if isinstance(ctx.obj, RuntimeContext):
        return ctx.obj
    return RuntimeContext("default", False, Console())


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {
            "encoding": "base64",
            "content": base64.b64encode(value).decode("ascii"),
            "bytes": len(value),
        }
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Iterator):
        return [_json_safe(item) for item in value]
    return value


def _emit_success(ctx: typer.Context, data: Any, *, title: str = "Resultado") -> None:
    runtime = _runtime(ctx)
    if runtime.json_output:
        typer.echo(
            json.dumps({"ok": True, "data": _json_safe(data)}, ensure_ascii=False)
        )
    elif data is not None:
        render_data(runtime.console, data, title=title)


def _emit_error(ctx: typer.Context, exc: Exception) -> None:
    runtime = _runtime(ctx)
    error: dict[str, Any] = {
        "type": exc.__class__.__name__,
        "message": str(exc),
    }
    if isinstance(exc, HublaHttpError):
        error["status_code"] = exc.status_code
        if exc.data is not None:
            error["details"] = exc.data
    if runtime.json_output:
        typer.echo(json.dumps({"ok": False, "error": error}, ensure_ascii=False))
    else:
        runtime.console.print(f"[bold red]Erro:[/bold red] {exc}")


def _execute(ctx: typer.Context, operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except (HublaError, ValueError, TypeError, OSError) as exc:
        _emit_error(ctx, exc)
        raise typer.Exit(code=2) from exc


def _parse_object(value: str, option_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise CommandError(f"{option_name} não contém JSON válido") from exc
    if not isinstance(parsed, dict):
        raise CommandError(f"{option_name} deve conter um objeto JSON")
    return parsed


def _write_binary(path: Path, content: bytes, *, force: bool) -> dict[str, Any]:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if force:
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(content)
            if os.name != "nt":
                temporary_path.chmod(0o600)
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)
    else:
        try:
            file_descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as exc:
            raise CommandError(
                f"o arquivo já existe: {path}; use --force para substituir"
            ) from exc
        try:
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(content)
        except Exception:
            path.unlink(missing_ok=True)
            raise
    if os.name != "nt":
        path.chmod(0o600)
    return {"path": str(path.resolve()), "bytes_written": len(content)}


def _preflight_binary_output(output: Path | None, *, force: bool) -> Path:
    if output is None:
        raise CommandError(
            "a resposta é binária; informe --output antes de executar a operação"
        )
    path = output.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_dir():
            raise CommandError(f"o destino é um diretório: {path}")
        if not force:
            raise CommandError(
                f"o arquivo já existe: {path}; use --force para substituir"
            )
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.preflight.",
        suffix=".tmp",
    )
    os.close(file_descriptor)
    Path(temporary_name).unlink(missing_ok=True)
    return path


def _catalog_operation(resource: str, operation_name: str) -> dict[str, Any]:
    catalog = build_catalog()
    resource_data = catalog["resources"].get(resource)
    if resource_data is None:
        raise CommandError(f"recurso desconhecido: {resource}")
    operation = resource_data["operations"].get(operation_name)
    if operation is None:
        raise CommandError(f"operação desconhecida: {resource}.{operation_name}")
    return operation


def _prepare_result(
    result: Any,
    *,
    output: Path | None = None,
    force: bool = False,
) -> Any:
    if isinstance(result, bytes):
        if output is None:
            raise CommandError(
                "a resposta é binária; informe --output para evitar expor a exportação"
            )
        return _write_binary(output, result, force=force)
    return result


def get_client(profile: str) -> HublaClient:
    """Build the selected authenticated client. Kept separate for testing."""
    return HublaClient.from_profile(profile=profile)


def _environment_auth_configured() -> bool:
    return bool(
        os.getenv("HUBLA_REFRESH_TOKEN")
        or (os.getenv("HUBLA_EMAIL") and os.getenv("HUBLA_PASSWORD"))
    )


def verify_login(auth: HublaAuth) -> Any:
    """Verify that a Firebase session can read the associated Hubla account."""
    return HublaClient(auth=auth).account.business()


@app.command("login")
def login_command(
    ctx: typer.Context,
    email: str | None = typer.Option(
        None,
        "--email",
        help="E-mail da conta. A senha é sempre solicitada de modo interativo.",
    ),
) -> None:
    """Entra na Hubla e salva somente o token renovável, nunca a senha."""

    def operation() -> None:
        runtime = _runtime(ctx)
        selected_email = (email or prompt_email()).strip()
        if not selected_email:
            raise CommandError("informe o e-mail da conta Hubla")
        password = prompt_password()
        if not password:
            raise CommandError("informe a senha da conta Hubla")
        auth = HublaAuth(email=selected_email, password=password)
        try:
            tokens = auth.login()
            account = verify_login(auth)
        finally:
            del password
        if not tokens.refresh_token:
            raise CommandError("a Hubla não retornou uma sessão renovável")
        storage = CredentialStore(profile=runtime.profile).save(
            selected_email,
            tokens.refresh_token,
        )
        _emit_success(
            ctx,
            {
                "authenticated": True,
                "email": selected_email,
                "profile": runtime.profile,
                "storage": storage,
                "account_verified": bool(account is not None),
            },
            title="Login concluído",
        )

    _execute(ctx, operation)


@app.command("logout")
def logout_command(ctx: typer.Context) -> None:
    """Remove a sessão renovável salva para o perfil atual."""

    def operation() -> None:
        runtime = _runtime(ctx)
        if _environment_auth_configured():
            raise CommandError(
                "a autenticação vem do ambiente; remova HUBLA_REFRESH_TOKEN ou "
                "HUBLA_EMAIL/HUBLA_PASSWORD no processo que executa o CLI"
            )
        CredentialStore(profile=runtime.profile).delete()
        _emit_success(
            ctx,
            {"authenticated": False, "profile": runtime.profile},
            title="Logout concluído",
        )

    _execute(ctx, operation)


@app.command("status")
def status_command(ctx: typer.Context) -> None:
    """Confirma o perfil local e testa uma leitura da conta Hubla."""

    def operation() -> None:
        runtime = _runtime(ctx)
        source = "environment" if _environment_auth_configured() else "saved_profile"
        email = os.getenv("HUBLA_EMAIL") if source == "environment" else None
        if source == "saved_profile":
            credentials = CredentialStore(profile=runtime.profile).load()
            email = credentials.email if credentials else None
        client = get_client(runtime.profile)
        account = client.account.business()
        _emit_success(
            ctx,
            {
                "authenticated": True,
                "profile": runtime.profile,
                "email": email,
                "source": source,
                "account": account,
            },
            title="Status da conta",
        )

    _execute(ctx, operation)


@app.command("doctor")
def doctor_command(ctx: typer.Context) -> None:
    """Verifica Python, configuração pública, login e acesso à conta."""

    def operation() -> None:
        runtime = _runtime(ctx)
        checks: dict[str, Any] = {
            "python": {
                "ok": sys.version_info >= (3, 10),
                "version": ".".join(map(str, sys.version_info[:3])),
            },
            "firebase_public_config": {"ok": False},
            "credentials": {"ok": False, "profile": runtime.profile},
            "account": {"ok": False},
        }
        try:
            FirebaseConfigResolver().get_api_key()
            checks["firebase_public_config"]["ok"] = True
        except HublaError as exc:
            checks["firebase_public_config"]["error"] = str(exc)
        if _environment_auth_configured():
            checks["credentials"] = {
                "ok": True,
                "profile": runtime.profile,
                "source": "environment",
            }
            if os.getenv("HUBLA_EMAIL"):
                checks["credentials"]["email"] = os.getenv("HUBLA_EMAIL")
        else:
            try:
                credentials = CredentialStore(profile=runtime.profile).load()
                checks["credentials"]["ok"] = credentials is not None
                checks["credentials"]["source"] = "saved_profile"
                if credentials:
                    checks["credentials"]["email"] = credentials.email
            except HublaError as exc:
                checks["credentials"]["error"] = str(exc)

        if checks["credentials"]["ok"]:
            try:
                get_client(runtime.profile).account.business()
                checks["account"] = {"ok": True}
            except (HublaError, ValueError, OSError) as exc:
                checks["account"]["error"] = str(exc)

        checks["ok"] = all(
            item.get("ok", False) for key, item in checks.items() if key != "ok"
        )
        if checks["ok"]:
            _emit_success(ctx, checks, title="Diagnóstico")
            return

        runtime = _runtime(ctx)
        if runtime.json_output:
            typer.echo(
                json.dumps(
                    {
                        "ok": False,
                        "error": {
                            "type": "DoctorError",
                            "message": "uma ou mais verificações falharam",
                            "checks": checks,
                        },
                    },
                    ensure_ascii=False,
                )
            )
        else:
            render_data(runtime.console, checks, title="Diagnóstico")
            runtime.console.print(
                "[bold red]Uma ou mais verificações falharam.[/bold red]"
            )
        raise typer.Exit(code=2)

    _execute(ctx, operation)


@app.command("schema")
def schema_command(
    ctx: typer.Context,
    resource: str | None = typer.Argument(
        None,
        help="Recurso opcional, por exemplo: sales.",
    ),
    operation_name: str | None = typer.Argument(
        None,
        help="Operação opcional, por exemplo: list.",
    ),
) -> None:
    """Lista recursos, operações, parâmetros e risco em formato legível ou JSON."""

    def operation() -> None:
        catalog = build_catalog()
        data: Any = catalog
        if resource is not None:
            resource_data = catalog["resources"].get(resource)
            if resource_data is None:
                raise CommandError(f"recurso desconhecido: {resource}")
            data = resource_data
            if operation_name is not None:
                operation_data = resource_data["operations"].get(operation_name)
                if operation_data is None:
                    raise CommandError(
                        f"operação desconhecida: {resource}.{operation_name}"
                    )
                data = operation_data
        elif operation_name is not None:
            raise CommandError("informe o recurso antes da operação")
        _emit_success(ctx, data, title="Catálogo de comandos")

    _execute(ctx, operation)


@app.command("call")
def call_command(
    ctx: typer.Context,
    resource: str = typer.Argument(help="Grupo de recurso, como sales ou products."),
    operation_name: str = typer.Argument(help="Método público do recurso."),
    params: str = typer.Option(
        "{}",
        "--params",
        help="Parâmetros como um objeto JSON com nomes em snake_case.",
    ),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="Autoriza a operação mutável exata depois de revisar alvo e payload.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Arquivo para respostas binárias, como exportações.",
    ),
    force: bool = typer.Option(False, "--force", help="Substitui --output existente."),
) -> None:
    """Executa qualquer operação do catálogo público de recursos."""

    def operation() -> None:
        parsed = _parse_object(params, "--params")
        runtime = _runtime(ctx)
        operation_metadata = _catalog_operation(resource, operation_name)
        selected_output = output
        if operation_metadata["binary"]:
            selected_output = _preflight_binary_output(output, force=force)
        result = invoke_resource(
            get_client(runtime.profile),
            resource,
            operation_name,
            parsed,
            confirm=confirm,
        )
        result = _prepare_result(result, output=selected_output, force=force)
        _emit_success(ctx, result, title=f"{resource}.{operation_name}")

    _execute(ctx, operation)


@app.command("api")
def api_command(
    ctx: typer.Context,
    service: str = typer.Argument(help="Serviço oficial. Consulte `schema`."),
    method: str = typer.Argument(help="GET, POST, PUT, PATCH ou DELETE."),
    path: str = typer.Argument(help="Caminho relativo dentro do serviço Hubla."),
    params: str = typer.Option("{}", "--params", help="Query string em objeto JSON."),
    body: str = typer.Option("null", "--body", help="Corpo JSON da requisição."),
    bytes_output: bool = typer.Option(
        False,
        "--bytes",
        help="Trata a resposta como dados binários.",
    ),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="Obrigatório em toda chamada raw diferente de GET.",
    ),
    output: Path | None = typer.Option(None, "--output"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Faz uma chamada avançada a um BFF oficial, com hosts bloqueados."""

    def operation() -> None:
        runtime = _runtime(ctx)
        if service not in BASE_URLS:
            raise CommandError(f"serviço desconhecido: {service}")
        selected_method = method.upper()
        if selected_method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise CommandError(f"método HTTP inválido: {method}")
        parsed_params = _parse_object(params, "--params")
        try:
            parsed_body = json.loads(body)
        except json.JSONDecodeError as exc:
            raise CommandError("--body não contém JSON válido") from exc
        selected_output = output
        if bytes_output:
            selected_output = _preflight_binary_output(output, force=force)
        client = get_client(runtime.profile)
        response_type = "bytes" if bytes_output else "json"
        if selected_method == "GET":
            result = client.request(
                service,
                selected_method,
                path,
                params=parsed_params,
                json=parsed_body,
                response_type=response_type,
            )
        else:
            result = client.write(
                service,
                selected_method,
                path,
                params=parsed_params,
                json=parsed_body,
                response_type=response_type,
                confirm=confirm,
            )
        result = _prepare_result(result, output=selected_output, force=force)
        _emit_success(ctx, result, title=f"{selected_method} {path}")

    _execute(ctx, operation)


@app.command("tui")
def tui_command(ctx: typer.Context) -> None:
    """Abre a interface interativa e segura de consultas."""
    runtime = _runtime(ctx)
    _execute(ctx, lambda: run_tui(get_client(runtime.profile), console=runtime.console))


@skill_app.command("install")
def skill_install_command(
    ctx: typer.Context,
    agent: str = typer.Option(
        "auto",
        "--agent",
        help=(
            "auto, generic, claude, codex, hermes, openclaw, antigravity/agy, "
            "opencode, pi ou all."
        ),
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Substitui uma skill homônima não gerenciada pelo hubla-cli.",
    ),
) -> None:
    """Instala ou atualiza a skill Agent Skills no escopo do usuário."""

    def operation() -> None:
        result = install_skill(agent, force=force)
        conflicts = [item for item in result if item.get("status") == "conflict"]
        if conflicts:
            paths = ", ".join(str(item["path"]) for item in conflicts)
            raise CommandError(
                "skill existente não gerenciada; nada foi sobrescrito em: " + paths
            )
        _emit_success(ctx, result, title="Skill para agentes")

    _execute(ctx, operation)


@skill_app.command("status")
def skill_status_command(
    ctx: typer.Context,
    agent: str = typer.Option("auto", "--agent"),
) -> None:
    """Mostra onde a skill está instalada e se está atualizada."""

    def operation() -> None:
        _emit_success(
            ctx,
            skill_status(agent),
            title="Status da skill",
        )

    _execute(ctx, operation)


@sales_app.command("list")
def sales_list_command(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    status: list[str] | None = typer.Option(None, "--status"),
    sale_type: list[str] | None = typer.Option(None, "--type"),
    payment_method: list[str] | None = typer.Option(None, "--method"),
    search: str = typer.Option("", "--search"),
    offer_id: list[str] | None = typer.Option(None, "--offer-id"),
    all_offers: bool = typer.Option(False, "--all-offers"),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(25, "--page-size", min=1, max=500),
) -> None:
    """Lista e filtra vendas."""

    def operation() -> None:
        client = get_client(_runtime(ctx).profile)
        result = client.sales.list(
            start_date=start_date,
            end_date=end_date,
            statuses=status,
            types=sale_type,
            methods=payment_method,
            search=search,
            offer_ids=offer_id,
            has_selected_all=True if all_offers else None,
            page=page,
            page_size=page_size,
        )
        _emit_success(ctx, result, title="Vendas")

    _execute(ctx, operation)


@sales_app.command("get")
def sales_get_command(ctx: typer.Context, invoice_id: str) -> None:
    """Mostra uma venda por ID."""
    _execute(
        ctx,
        lambda: _emit_success(
            ctx,
            get_client(_runtime(ctx).profile).sales.get(invoice_id),
            title="Venda",
        ),
    )


@sales_app.command("summaries")
def sales_summaries_command(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    offer_id: list[str] | None = typer.Option(None, "--offer-id"),
) -> None:
    """Mostra os totais de vendas para o filtro informado."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).sales.summaries(
            start_date=start_date,
            end_date=end_date,
            offer_ids=offer_id,
        )
        _emit_success(ctx, result, title="Resumo de vendas")

    _execute(ctx, operation)


@sales_app.command("refund")
def sales_refund_command(
    ctx: typer.Context,
    invoice_id: str,
    confirm: bool = typer.Option(False, "--confirm"),
) -> None:
    """Reembolsa uma venda somente com confirmação explícita."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).sales.refund(
            invoice_id,
            confirm=confirm,
        )
        _emit_success(ctx, result, title="Reembolso")

    _execute(ctx, operation)


@refunds_app.command("list")
def refunds_list_command(
    ctx: typer.Context,
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(25, "--page-size", min=1, max=500),
) -> None:
    """Lista solicitações de reembolso do vendedor."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).refunds.list(
            page=page,
            page_size=page_size,
        )
        _emit_success(ctx, result, title="Solicitações de reembolso")

    _execute(ctx, operation)


@refunds_app.command("get")
def refunds_get_command(ctx: typer.Context, refund_id: str) -> None:
    """Mostra uma solicitação de reembolso."""
    _execute(
        ctx,
        lambda: _emit_success(
            ctx,
            get_client(_runtime(ctx).profile).refunds.get(refund_id),
            title="Solicitação de reembolso",
        ),
    )


def _refund_decision(
    ctx: typer.Context,
    refund_id: str,
    action: str,
    confirm: bool,
) -> None:
    def operation() -> None:
        resource = get_client(_runtime(ctx).profile).refunds
        result = getattr(resource, action)(refund_id, confirm=confirm)
        _emit_success(ctx, result, title="Reembolso atualizado")

    _execute(ctx, operation)


@refunds_app.command("accept")
def refunds_accept_command(
    ctx: typer.Context,
    refund_id: str,
    confirm: bool = typer.Option(False, "--confirm"),
) -> None:
    """Aceita uma solicitação somente com confirmação explícita."""
    _refund_decision(ctx, refund_id, "accept", confirm)


@refunds_app.command("reject")
def refunds_reject_command(
    ctx: typer.Context,
    refund_id: str,
    confirm: bool = typer.Option(False, "--confirm"),
) -> None:
    """Rejeita uma solicitação somente com confirmação explícita."""
    _refund_decision(ctx, refund_id, "reject", confirm)


@subscriptions_app.command("list")
def subscriptions_list_command(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    status: list[str] | None = typer.Option(None, "--status"),
    search: str = typer.Option("", "--search"),
    offer_id: list[str] | None = typer.Option(None, "--offer-id"),
    all_offers: bool = typer.Option(False, "--all-offers"),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(25, "--page-size", min=1, max=500),
) -> None:
    """Lista e filtra assinaturas."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).subscriptions.list(
            start_date=start_date,
            end_date=end_date,
            statuses=status,
            search=search,
            offer_ids=offer_id,
            has_selected_all=True if all_offers else None,
            page=page,
            page_size=page_size,
        )
        _emit_success(ctx, result, title="Assinaturas")

    _execute(ctx, operation)


@subscriptions_app.command("get")
def subscriptions_get_command(ctx: typer.Context, subscription_id: str) -> None:
    """Mostra uma assinatura por ID."""
    _execute(
        ctx,
        lambda: _emit_success(
            ctx,
            get_client(_runtime(ctx).profile).subscriptions.get(subscription_id),
            title="Assinatura",
        ),
    )


@products_app.command("list")
def products_list_command(
    ctx: typer.Context,
    product_type: list[str] | None = typer.Option(None, "--type"),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(100, "--page-size", min=1, max=500),
) -> None:
    """Lista produtos."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).products.list(
            types=product_type,
            page=page,
            page_size=page_size,
        )
        _emit_success(ctx, result, title="Produtos")

    _execute(ctx, operation)


@products_app.command("get")
def products_get_command(ctx: typer.Context, product_id: str) -> None:
    """Mostra um produto por ID."""
    _execute(
        ctx,
        lambda: _emit_success(
            ctx,
            get_client(_runtime(ctx).profile).products.get(product_id),
            title="Produto",
        ),
    )


@products_app.command("offers")
def products_offers_command(
    ctx: typer.Context,
    product_id: str,
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(100, "--page-size", min=1, max=500),
    archived: bool = typer.Option(False, "--archived"),
) -> None:
    """Lista as ofertas de um produto."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).products.list_offers(
            product_id,
            page=page,
            page_size=page_size,
            archived=archived,
        )
        _emit_success(ctx, result, title="Ofertas")

    _execute(ctx, operation)


@products_app.command("cohorts")
def products_cohorts_command(
    ctx: typer.Context,
    product_id: str,
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(100, "--page-size", min=1, max=500),
) -> None:
    """Lista as turmas de um produto."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).products.list_cohorts(
            product_id,
            page=page,
            page_size=page_size,
        )
        _emit_success(ctx, result, title="Turmas")

    _execute(ctx, operation)


@members_app.command("list")
def members_list_command(
    ctx: typer.Context,
    product_id: str | None = typer.Option(None, "--product-id"),
    search: str = typer.Option("", "--search"),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(25, "--page-size", min=1, max=500),
) -> None:
    """Lista membros ativos."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).members.active(
            product_id=product_id,
            search=search,
            page=page,
            page_size=page_size,
        )
        _emit_success(ctx, result, title="Membros ativos")

    _execute(ctx, operation)


@members_app.command("deactivated")
def members_deactivated_command(
    ctx: typer.Context,
    product_id: str | None = typer.Option(None, "--product-id"),
    search: str = typer.Option("", "--search"),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(25, "--page-size", min=1, max=500),
) -> None:
    """Lista membros desativados."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).members.deactivated(
            product_id=product_id,
            search=search,
            page=page,
            page_size=page_size,
        )
        _emit_success(ctx, result, title="Membros desativados")

    _execute(ctx, operation)


@members_app.command("pending")
def members_pending_command(ctx: typer.Context) -> None:
    """Lista convites pendentes."""
    _execute(
        ctx,
        lambda: _emit_success(
            ctx,
            get_client(_runtime(ctx).profile).members.pending_invites(),
            title="Convites pendentes",
        ),
    )


@analytics_app.command("get")
def analytics_get_command(
    ctx: typer.Context,
    metric: str = typer.Argument(
        help=(
            "net_revenue, sales, refunds, average_ticket, "
            "average_ticket_by_currency, conversion_rate ou abandoned_checkouts."
        )
    ),
    start_date: str = typer.Option(..., "--start-date"),
    end_date: str = typer.Option(..., "--end-date"),
    period: str | None = typer.Option(None, "--period"),
    offer_id: list[str] | None = typer.Option(None, "--offer-id"),
) -> None:
    """Consulta um indicador por período."""

    def operation() -> None:
        allowed = {
            "net_revenue",
            "sales",
            "refunds",
            "average_ticket",
            "average_ticket_by_currency",
            "conversion_rate",
            "abandoned_checkouts",
        }
        if metric not in allowed:
            raise CommandError(f"métrica desconhecida: {metric}")
        kwargs: dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "offer_ids": offer_id,
        }
        if metric == "net_revenue":
            if not period:
                raise CommandError("net_revenue exige --period")
            kwargs["period"] = period
        resource = get_client(_runtime(ctx).profile).analytics
        result = getattr(resource, metric)(**kwargs)
        _emit_success(ctx, result, title=f"Indicador: {metric}")

    _execute(ctx, operation)


@finance_app.command("forecast")
def finance_forecast_command(
    ctx: typer.Context,
    target_dates: list[str] | None = typer.Option(
        None,
        "--date",
        help=(
            "Data-alvo YYYY-MM-DD. Repita para comparar datas. Sem esta opção, "
            "usa o fim do mês atual e do próximo."
        ),
    ),
    currency: str = typer.Option("BRL", "--currency"),
    timezone: str = typer.Option(DEFAULT_FINANCE_TIMEZONE, "--timezone"),
) -> None:
    """Projeta o saldo sacável em datas futuras a partir do retrato atual."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).finance.availability_forecast(
            target_dates=target_dates,
            currency=currency,
            timezone=timezone,
        )
        _emit_success(ctx, result, title="Projeção de saldo para saque")

    _execute(ctx, operation)


@finance_app.command("balance")
def finance_balance_command(
    ctx: typer.Context,
    currency: str | None = typer.Option(None, "--currency"),
) -> None:
    """Mostra o saldo disponível."""
    _execute(
        ctx,
        lambda: _emit_success(
            ctx,
            get_client(_runtime(ctx).profile).finance.balance(currency),
            title="Saldo",
        ),
    )


@finance_app.command("statement")
def finance_statement_command(
    ctx: typer.Context,
    params: str = typer.Option("{}", "--params"),
) -> None:
    """Mostra o extrato financeiro."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).finance.account_statement(
            params=_parse_object(params, "--params")
        )
        _emit_success(ctx, result, title="Extrato")

    _execute(ctx, operation)


@finance_app.command("movements")
def finance_movements_command(
    ctx: typer.Context,
    params: str = typer.Option("{}", "--params"),
) -> None:
    """Lista movimentações financeiras."""

    def operation() -> None:
        result = get_client(_runtime(ctx).profile).finance.movements(
            params=_parse_object(params, "--params")
        )
        _emit_success(ctx, result, title="Movimentações")

    _execute(ctx, operation)


@account_app.command("show")
def account_show_command(ctx: typer.Context) -> None:
    """Mostra os dados do negócio conectado."""
    _execute(
        ctx,
        lambda: _emit_success(
            ctx,
            get_client(_runtime(ctx).profile).account.business(),
            title="Conta Hubla",
        ),
    )


@account_app.command("profile")
def account_profile_command(ctx: typer.Context) -> None:
    """Mostra o perfil do usuário conectado."""
    _execute(
        ctx,
        lambda: _emit_success(
            ctx,
            get_client(_runtime(ctx).profile).account.profile(),
            title="Perfil",
        ),
    )


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
