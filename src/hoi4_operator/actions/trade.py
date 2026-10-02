"""Small semantic trade catalog; factory commitments rather than GUI slider units."""

RESOURCES = {"steel": {"display": "钢", "supported_countries": ["SWE"]}}
COUNTRIES = {"SWE": {"display": "瑞典"}}
SUPPORTED_FACTORIES = (0, 1, 2)


def target(view):
    imports = view["imports"]
    if len(imports) != 1:
        raise ValueError("unexpected scoped trade observation")
    item = imports[0]
    return (item["resource"], item["country"], item["civilian_factories"], item["requested_amount"])
