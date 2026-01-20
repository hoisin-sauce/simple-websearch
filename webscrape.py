import datetime
import log
import threadmanager
import websearch
import webstorage
import threading
import config
import time
import requestmanager
from subdomains import Subdomain
import sitedatabasehandler
import sitehandler
import pagerank

db: None | webstorage.Database= None
db_handler: None | sitedatabasehandler.SiteDatabaseHandler = None

thread_manager: None | threadmanager.ThreadManager = threadmanager.ThreadManager()
queues: None | threadmanager.QueueContainer = None


def set_db(database: webstorage.Database):
    global db, db_handler, queues
    db = database
    db_handler = sitedatabasehandler.SiteDatabaseHandler(database)
    queues = threadmanager.QueueContainer(db_handler, sitehandler.SiteHandler)


def old_links_daemon() -> None:
    while True:
        try:
            urls_to_check = db.execute(config.Config.FIND_OLD_LINKS.value,
                                       is_file=True)

            urls_to_check = {
                Subdomain(subdomain["link"]): 0 for subdomain in urls_to_check}

            queues.queue_links(urls_to_check)

            time.sleep(config.Config.DAEMON_WAIT_TIME_SECONDS.value)
        except Exception as e:
            log.log(e)
            raise


def get_unprocessed_links() -> list[Subdomain]:
    subdomains: list[Subdomain] = list()
    urls = db.execute(config.Config.GET_UNCHECKED_LINKS.value, is_file=True)
    for url in urls:
        subdomains.append(Subdomain(url['url']))

    return subdomains


def start_scraping() -> None:
    log.log("Starting background")
    background_scraper = threading.Thread(target=old_links_daemon, daemon=True)
    background_scraper.start()

    log.log("Starting primary scraping")
    sites_to_scrape: dict[Subdomain, int] = dict()
    for site in config.Config.SCRAPING_SITES.value:
        log.log(f"Starting scraping for {site}")
        sites_to_scrape[Subdomain(site)] = 0

    log.log("Getting unprocessed links")
    unprocessed_links: dict[Subdomain, int] = dict()
    for subdomain in get_unprocessed_links():
        unprocessed_links[subdomain] = 0

    log.log("Queuing links")
    queues.queue_links(sites_to_scrape)
    queues.queue_links(unprocessed_links)


if __name__ == "__main__":
    _db = webstorage.Database(config.Config.DATABASE_NAME.value,
                              config.Config.INIT_SCRIPT.value,
                              script_directory=config.Config.SCRIPT_FOLDER.value,)

    requestmanager.RequestManager.set_default_period(
        datetime.timedelta(
            seconds=config.Config.SITE_REQUEST_INTERVAL_SECONDS.value),
        config.Config.SITE_REQUESTS_IN_INTERVAL.value,
    )

    requestmanager.RequestManager.set_global_period(
        config.Config.GLOBAL_REQUESTS_IN_INTERVAL.value,
        datetime.timedelta(
            seconds=config.Config.GLOBAL_REQUEST_INTERVAL_SECONDS.value),
    )

    set_db(_db)
    pagerank.set_db(_db)
    requestmanager.set_db(_db)
    websearch.set_db(_db)

    start_scraping()
    pagerank.start_pagerank()
