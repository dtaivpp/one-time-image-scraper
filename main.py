import sys
import scrape
import logging

if __name__=="__main__":
    args = sys.argv[1:]

    if len(args) > 1:
        worker = scrape.Scraper(int(args[0]), last_link_index=int(args[1]), last_page_index=(args[2]))
    else: 
        worker = scrape.Scraper(int(args[0]))
        #worker = scrape.WireScraper(8, 18, 1)

    worker.main()