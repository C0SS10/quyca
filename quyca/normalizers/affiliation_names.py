def get_affiliation_name(names: list[dict], preferred_langs: tuple[str, ...] = ("es", "en")) -> str:
    if not names:
        return ""
    for lang in preferred_langs:
        for item in names:
            if item.get("lang") == lang and item.get("name"):
                return item["name"]
    return next((n["name"] for n in names if n.get("name")), "")
