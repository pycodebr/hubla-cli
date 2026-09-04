"""High-level Hubla resource groups."""

from hubla_cli.resources.account import AccountResource
from hubla_cli.resources.affiliates import AffiliatesResource
from hubla_cli.resources.analytics import AnalyticsResource
from hubla_cli.resources.coupons import CouponsResource
from hubla_cli.resources.finance import FinanceResource
from hubla_cli.resources.integrations import IntegrationsResource
from hubla_cli.resources.member_contents import (
    MemberContentsResource,
    MembersAreaContentsResource,
)
from hubla_cli.resources.members import GroupsResource, MembersResource
from hubla_cli.resources.products import ProductsResource
from hubla_cli.resources.refunds import RefundsResource
from hubla_cli.resources.sales import SalesResource
from hubla_cli.resources.storefronts import StorefrontsResource
from hubla_cli.resources.subscriptions import SubscriptionsResource

__all__ = [
    "AccountResource",
    "AffiliatesResource",
    "AnalyticsResource",
    "CouponsResource",
    "FinanceResource",
    "GroupsResource",
    "IntegrationsResource",
    "MemberContentsResource",
    "MembersAreaContentsResource",
    "MembersResource",
    "ProductsResource",
    "RefundsResource",
    "SalesResource",
    "StorefrontsResource",
    "SubscriptionsResource",
]
