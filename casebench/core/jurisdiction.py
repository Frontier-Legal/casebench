"""Jurisdiction codes: ISO 3166 for countries and their parts, `EU` for the Union (0036)."""

import re
from typing import Annotated

from pydantic import AfterValidator

# ISO 3166-1 alpha-2 codes officially assigned, from Unicode CLDR 48.2.3 (Unicode License 3.0),
# supplemental/codeMappings.json: two-letter regions with a numeric and an alpha-3 code, less
# CLDR's private-use, deprecated (aliases.json) and grouping codes. Taken on 2026-10-13: 249.
# fmt: off
COUNTRIES = frozenset((
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ",
    "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS",
    "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
    "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE",
    "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF",
    "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
    "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", "JE", "JM",
    "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC",
    "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK",
    "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA",
    "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG",
    "PH", "PK", "PL", "PM", "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW",
    "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS",
    "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO",
    "TR", "TT", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
    "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
))
# fmt: on
EU = "EU"
# The European Case Law Identifier writes these two outside ISO 3166-1.
ALIASES = {"UK": "GB", "EL": "GR"}
_PART = re.compile(r"[A-Z0-9]{1,3}")


class UnknownJurisdiction(ValueError):
    """A jurisdiction written in a way Casebench does not read."""


def code(value: str) -> str:
    """The one code for a jurisdiction: upper case, aliases replaced, `country-part` for a
    part of a country (ISO 3166-2). Anything else is refused, naming the expected form."""
    text = value.strip().upper()
    country, dash, part = text.partition("-")
    country = ALIASES.get(country, country)
    if country == EU and not dash:
        return EU
    if country not in COUNTRIES or (dash and not _PART.fullmatch(part)):
        raise UnknownJurisdiction(
            f"{value!r} is not a jurisdiction code; write ISO 3166-1 alpha-2 such as NO or TR, "
            "ISO 3166-2 such as US-CA, or EU"
        )
    return f"{country}-{part}" if dash else country


Jurisdiction = Annotated[str, AfterValidator(code)]
