import sys

from integrations import Scraper

if sys.argv[1] == '-yt':
    scraper = Scraper()
    method = 0
    for par in sys.argv[2:]:
        if par.isdigit():
            method = par
            continue
        scraper.youtube(par, method)

