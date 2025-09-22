import tokens
import webstorage
import config
from tokens import TokenContainer
from typing import Any

db : webstorage.Database | None = None

def set_db(database: webstorage.Database):
    global db
    db = database

def search_for(query: str) -> list[str]:
    query_tokens = tokens.get_tokens(query)
    subdomains = get_subdomains_featuring(query_tokens,
        config.Config.RESULTS_PER_SEARCH.value)
    apply_token_rating(subdomains, query_tokens)
    sorted_subdomains = sorted(subdomains, key=lambda subdomain: subdomain['query_ranking'] , reverse=True)
    just_subdomains = [subdomain['url'] + subdomain['extension']
                       for subdomain in sorted_subdomains]
    return just_subdomains

def get_subdomains_featuring(query_tokens: TokenContainer,
                             pagerank_cutoff_count: int) -> list[dict[str, Any]]:
    # possibly expensive
    params: list[Any] = list(query_tokens.token_names()) # + [pagerank_cutoff_count,]

    sql_query = db.get_script(config.Config.GET_QUERY_SUBDOMAINS.value)

    sql_query = sql_query.format(
        token_amount = ",".join(["?"] * len(query_tokens)),
    )

    subdomains = db.execute(sql_query,
        params=params, is_file=False)

    return subdomains

def apply_token_rating(subdomains: list[dict[str, Any]],
                       query_tokens: TokenContainer) -> None:
    total_tokens = query_tokens.total_tokens()

    for i, subdomain in enumerate(subdomains):
        token_rank = 0
        page_tokens = get_subdomain_tokens(subdomain)
        for token, count in page_tokens.items():
            if token not in query_tokens:
                continue
            token_rank += count * query_tokens.get_count(token)
        token_rank /= total_tokens
        subdomains[i]['query_ranking'] = token_rank * (1 + (subdomain['pagerank'] - 1) * config.Config.PAGE_RANK_STRENGTH.value)

def get_subdomain_tokens(subdomain: dict[str, Any]) -> dict[str, int]:
    params = {
        "url": subdomain["url"],
        "extension": subdomain["extension"],
    }

    token_list = db.execute(config.Config.GET_SUBDOMAIN_TOKENS.value, params=params,
               is_file=True)

    return {token["token"]: token["occurrences"] for token in token_list}


def search_loop():
    while True:
        print(search_for(input("Search query: ")))