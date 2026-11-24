from quyca.exceptions import InvalidParamException

GEO_TYPES = ("city", "state")


def validate_sort(sort: str | None) -> None:
    """`sort` must be `<field>_<direction>`, e.g. citations_desc (see base_repository.set_sort)."""
    if sort and len(sort.split("_")) != 2:
        raise InvalidParamException(f"Invalid sort '{sort}'. Expected <field>_<asc|desc>, e.g. citations_desc")


def validate_years(years: str | None) -> None:
    if not years:
        return
    try:
        for year in years.split(","):
            int(year)
    except ValueError as e:
        raise InvalidParamException(f"Invalid years '{years}'. Expected comma separated years, e.g. 2020,2024") from e


def validate_geo_type(geo_type: str) -> None:
    if geo_type not in GEO_TYPES:
        raise InvalidParamException("Invalid geo_type. Allowed values: city, state")
