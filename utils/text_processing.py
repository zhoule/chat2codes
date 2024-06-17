
from urllib.parse import quote
def make_url_compatible(s: str) -> str:
    s_with_underscores = s.replace(" ", "_")
    return quote(s_with_underscores, safe="")
