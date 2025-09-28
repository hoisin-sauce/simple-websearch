import config
import webstorage
import time
import log
import threading
from subdomains import Subdomain
from typing import Any, Generator

db : None | webstorage.Database = None

def set_db(database: webstorage.Database):
    global db
    db = database

def pagerank() -> None:
    """
    Update database with values calculated from pagerank algorithm
    Using template from https://anvil.works/blog/search-engine-pagerank
    # TODO migrate this to something involving/based on the matrix implementation
    :return:
    """
    subdomain_count = db.execute(config.Config.GET_SUBDOMAIN_COUNT.value,
                                 is_file=True)[0]['subdomain_count']

    for subdomain in subdomain_generator():
        # get all links to subdomain
        params = [subdomain.domain, subdomain.extension]
        backlinks = db.execute(config.Config.GET_BACKLINKS_PAGERANK.value,
                               is_file=True, params=params)

        if config.Config.TRACK_PAGERANK_BACKLINKS.value:
            log.log(f"Backlinks to {subdomain} are {backlinks}")
        new_rank = calculate_new_pagerank(backlinks, subdomain_count=subdomain_count)

        params = {'url':subdomain.domain,
                  'extension':subdomain.extension,
                  'new_rank':new_rank}
        db.execute(config.Config.SET_TEMPORARY_SUBDOMAIN_RANK.value,
            params=params, is_file=True)

    db.execute(config.Config.MIGRATE_SUBDOMAIN_RANKS.value, is_file=True)

    if config.Config.LOG_TOTAL_PAGERANK.value:
        total_rank = db.execute(
            config.Config.GET_TOTAL_RANK.value, is_file=True)[0]['total_rank']
        log.log(f"Total rank: {total_rank}")

def calculate_new_pagerank(backlinks: list[dict[str, Any]],
                           subdomain_count : int = 1) -> float:
    new_rank = 0
    for backlink in backlinks:
        if backlink['origin_pagerank'] is None:
            backlink['origin_pagerank'] = 1/subdomain_count

        if backlink['forward_links'] == 0:
            backlink['forward_links'] = 1

        new_rank += (backlink['occurrences'] * backlink['origin_pagerank']
            / backlink['forward_links'])

    new_rank *= config.Config.PAGE_RANK_MULTIPLIER.value

    new_rank += (1 - config.Config.PAGE_RANK_MULTIPLIER.value) / subdomain_count
    return new_rank


def subdomain_generator() -> Generator[Subdomain, None, None]:
    """
    Returns generator which yields subdomains to prevent entire table from being loaded into memory
    :return: Subdomain generator
    """
    params = [config.Config.PAGE_RANK_MEMORY_ROWS.value, 0]
    while subdomains := db.execute(config.Config.GET_SUBDOMAINS.value,
            params=params, is_file=True):
        for subdomain in subdomains:
            url = "//" + subdomain["url"] + subdomain["extension"]
            yield Subdomain(url)
        params[1] += config.Config.PAGE_RANK_MEMORY_ROWS.value

# TODO make a method of storing all links that need to be processed when the program is terminated

def pagerank_daemon() -> None:
    """
    Daemon thread responsible for repeatedly running pagerank algorithm
    :return:
    """
    log.log("Starting pagerank daemon")

    # Check if enough idle cycles have occurred to finish iterations
    passes_since_last_update = 0
    while passes_since_last_update != config.Config.PAGE_RANK_ITERS_AFTER_LAST_CHANGE.value:
        log.log(f"pagerank starting")
        start = time.time()
        pagerank()
        end = time.time()
        if config.Config.TRACK_PAGERANK_TIMES.value:
            log.log(f"pagerank finished in {end - start} seconds")
        time.sleep(config.Config.PAGE_RANK_INTERVAL_SECONDS.value)

        # If last database update was done by this function iterate passes
        # to check if links are being updated
        if time.time() - db.last_change + 1 >= config.Config.PAGE_RANK_INTERVAL_SECONDS.value + end - start:
            passes_since_last_update += 1
        else:
            passes_since_last_update = 0

    if config.Config.PAGE_RANK_FINAL_CYCLES:
        log.log(f"pagerank starting final cycles")
        for i in range(config.Config.PAGE_RANK_FINAL_CYCLES.value):
            log.log(f"pagerank starting - post loop iteration: {i}")
            start = time.time()
            pagerank()
            end = time.time()
            log.log(f"pagerank finished in {end - start} seconds")

    if config.Config.ENABLE_LOGGING_PROFILER:
        log.log(f"pagerank daemon terminated")


def start_pagerank() -> None:
    threading.Thread(target=pagerank_daemon, daemon=True).start()