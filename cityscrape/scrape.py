import os
import re
import sys
import csv
import time
import traceback
from typing import Dict, List
from datetime import datetime

import urllib.parse
import requests
import bs4
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
import pandas as pd

import cityscrape.scrape_util as su

class WebScrape(object):
    '''
    Class for instantiating a webscraper. Use the scrape method to start
    scraping.

    Inputs:
        - start_url (str): URL from which to start the scrape
        - tovisit_q: mp.Queue() object to store URLs to be visited
        - writeto_q: mp.Queue() object to store data that is to be written
        - faildrd_q: mp.Queue() object to store URLs with failed reads
        - pdflink_q: mp.Queue() object to store PDF URLs to be scraped
        - visited_qs: mp.Queue() object to store set of links that have been
          visited
        - tovisit_qs: mp.Queue() obect to track the URLs that are in the queue
          and already will be visited
        - lmt_doma (str): domain to restrict the scrape to
        - lmt_path (str): used to limit the scrape to URLs with string in path
        - mqueue: TO BE DELETED
    '''
    def __init__(self,
                 start_url: str,
                 tovisit_q,
                 writeto_q,
                 faildrd_q,
                 pdflink_q,
                 visited_qs,
                 tovisit_qs,
                 lmt_doma: str = '',
                 lmt_path: str = '',
                 mqueue = None):

        self.start_url = start_url
        self.lmt_doma = lmt_doma
        self.lmt_path = lmt_path
        self.tovisit_q = tovisit_q
        self.writeto_q = writeto_q
        self.faildrd_q = faildrd_q
        self.pdflink_q = pdflink_q
        self.visited_qs = visited_qs
        self.tovisit_qs = tovisit_qs
        self.class_ = None # DELETE

    def scrape(self,
               num_pages_to_crawl: int,
               ignore: List[str] = []):

        start = time.time()
        failed_reads = []
        page_counter = 0
        self.tovisit_q.put((0, self.start_url))

        while page_counter < num_pages_to_crawl:

            if page_counter != 0 and self.tovisit_q.qsize == 0:
                break
            else:
                next_url = self.tovisit_q.get()

            from_url, curr_url = next_url[0], next_url[1]

            try:
                request = su.get_request(curr_url)
                true_url = su.get_true_url(request)

            except Exception as e:
                print(e)
                self.faildrd_q.put([from_url, curr_url])
                continue


            if su.check_ifin_queue(self.visited_qs, true_url):
                continue
            elif su.check_ifin_queue(self.visited_qs, curr_url):
                continue
            elif su.check_ifin_queue(self.tovisit_qs, true_url):
                continue
            elif su.check_ifin_queue(self.tovisit_qs, curr_url):
                continue


            su.add_to_queue_set(self.visited_qs, true_url)
            su.add_to_queue_set(self.visited_qs, curr_url)
            su.add_to_queue_set(self.tovisit_qs, true_url)
            su.add_to_queue_set(self.tovisit_qs, curr_url)

            soup = su.request_to_soup(request)

            try:
                su.clean_and_queue_urls(soup,
                                        page_counter,
                                        curr_url,
                                        true_url,
                                        self.tovisit_q,
                                        self.writeto_q,
                                        self.pdflink_q,
                                        self.visited_qs,
                                        self.tovisit_qs,
                                        ignore,
                                        self.lmt_doma,
                                        self.lmt_path,
                                        self.class_)
            except Exception as e:
                print(e)
                print("FAILED")
            page_counter += 1
            print(curr_url, self.tovisit_q.qsize())



        while not self.tovisit_q.empty():
            self.tovisit_q.get()
        print("tovisit_q is EMPTY.")

        while not self.writeto_q.empty():
            self.writeto_q.get()
        print("writeto_q is EMPTY.")

        while not self.visited_qs.empty():
            self.visited_qs.get()
        print("visted_qs is EMPTY.")

        while not self.tovisit_qs.empty():
            self.tovisit_qs.get()
        print("tovisit_qs is EMPTY.")

        while not self.faildrd_q.empty():
            self.faildrd_q.get()
        print("faildrd_q is EMPTY")


        self.tovisit_q.close()
        self.writeto_q.close()
        self.pdflink_q.close()
        self.visited_qs.close()
        self.tovisit_qs.close()
        self.faildrd_q.close()



