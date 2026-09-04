"""Machine-readable operation catalog for people and AI agents."""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any

from hubla_cli.errors import CommandError
from hubla_cli.resources import (
    AccountResource,
    AffiliatesResource,
    AnalyticsResource,
    CouponsResource,
    FinanceResource,
    GroupsResource,
    IntegrationsResource,
    MembersAreaContentsResource,
    MembersResource,
    ProductsResource,
    RefundsResource,
    SalesResource,
    StorefrontsResource,
    SubscriptionsResource,
)

RESOURCE_CLASSES = {
    "account": AccountResource,
    "affiliates": AffiliatesResource,
    "analytics": AnalyticsResource,
    "coupons": CouponsResource,
    "finance": FinanceResource,
    "groups": GroupsResource,
    "integrations": IntegrationsResource,
    "members_area_contents": MembersAreaContentsResource,
    "members": MembersResource,
    "products": ProductsResource,
    "refunds": RefundsResource,
    "sales": SalesResource,
    "storefronts": StorefrontsResource,
    "subscriptions": SubscriptionsResource,
}


def _annotation_name(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty:
        return "any"
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__name__", str(annotation).replace("typing.", ""))


def _json_default(value: Any) -> Any:
    if value is inspect.Parameter.empty:
        return None
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
        return value
    return repr(value)


def _operation_schema(resource_class: type[Any], method_name: str) -> dict[str, Any]:
    method = getattr(resource_class, method_name)
    signature = inspect.signature(method)
    parameters: dict[str, dict[str, Any]] = {}
    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        entry: dict[str, Any] = {
            "type": _annotation_name(parameter.annotation),
            "required": parameter.default is inspect.Parameter.empty
            and parameter.kind
            not in {
                inspect.Parameter.VAR_KEYWORD,
                inspect.Parameter.VAR_POSITIONAL,
            },
            "kind": parameter.kind.name.lower(),
        }
        if parameter.default is not inspect.Parameter.empty:
            entry["default"] = _json_default(parameter.default)
        parameters[name] = entry
    description = inspect.getdoc(method) or method_name.replace("_", " ")
    return_type = _annotation_name(signature.return_annotation)
    return {
        "description": description.splitlines()[0],
        "mutating": "confirm" in signature.parameters,
        "binary": return_type == "bytes",
        "return_type": return_type,
        "parameters": parameters,
    }


def build_catalog() -> dict[str, Any]:
    """Describe every public resource operation and its Python parameters."""
    resources: dict[str, Any] = {}
    for resource_name, resource_class in RESOURCE_CLASSES.items():
        operations = {
            method_name: _operation_schema(resource_class, method_name)
            for method_name, method in inspect.getmembers(
                resource_class,
                predicate=inspect.isfunction,
            )
            if not method_name.startswith("_") and callable(method)
        }
        resources[resource_name] = {
            "description": (
                inspect.getdoc(resource_class) or resource_name
            ).splitlines()[0],
            "operations": operations,
        }
    return {
        "format": "hubla-cli.catalog.v1",
        "resources": resources,
    }


def invoke_resource(
    client: Any,
    resource_name: str,
    method_name: str,
    params: Mapping[str, Any],
    *,
    confirm: bool = False,
) -> Any:
    """Invoke an allowlisted high-level method with validated keyword arguments."""
    resource_class = RESOURCE_CLASSES.get(resource_name)
    if resource_class is None:
        raise CommandError(f"recurso desconhecido: {resource_name}")
    operation = build_catalog()["resources"][resource_name]["operations"].get(
        method_name
    )
    if operation is None:
        raise CommandError(
            f"operação desconhecida: {resource_name}.{method_name}; "
            "consulte hubla-cli schema"
        )
    if not isinstance(params, Mapping):
        raise CommandError("--params deve conter um objeto JSON")

    resource = getattr(client, resource_name)
    method = getattr(resource, method_name)
    kwargs = dict(params)
    kwargs.pop("confirm", None)
    if operation["mutating"]:
        kwargs["confirm"] = confirm
    try:
        inspect.signature(method).bind(**kwargs)
    except TypeError as exc:
        raise CommandError(
            f"parâmetros inválidos para {resource_name}.{method_name}: {exc}"
        ) from exc
    return method(**kwargs)
