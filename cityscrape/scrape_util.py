import os
import time
import requests
from datetime import datetime
from typing import Dict, List

import bs4
import urllib.parse


def scrape_text(soup):
    '''
    Scrapes text from body of a City of Chicago web page, tokenizes, filters
    out characters that are not words stopwords. Returns all words in a list.
    Inputs:
        - soup (bs4 Object): soup from a web html page
    Outputs:
        - cleaned_words (list of strings): list of all tokenized words
    '''
    text = ''
    try:
        text_tags = soup.find_all('p')
        for text_tag in text_tags:
            text += text_tag.text + ' '
    except Exception as e:
        print(e)
    text = text.replace('\n', ' ')
    return text


def request_to_soup(request, url):
    '''
    Takes a request and returns a BeautifulSoup object.

    Input:
        - request (req object) the request for which html will be stored

    Returns: soup (bs4 object) the html soup
    '''

    html = read_request(request, url)
    soup = bs4.BeautifulSoup(html, 'html5lib')
    return soup


def unique_url_domains(outside):
    unique_domains = set()
    for url in outside:
        parsed_url = urllib.parse.urlparse(url)
        netloc = parsed_url.netloc
        if 'www' in netloc:
            netloc = netloc[4:]
        unique_domains.add(netloc)
    return unique_domains


def count_pdfs(urls):
    pdf_urls = []
    for url in urls:
        parsed_url = urllib.parse.urlparse(url)
        filename, ext = os.path.splitext(parsed_url.path)
        if ext == '.pdf':
            pdf_urls.append(url)

    return pdf_urls, len(pdf_urls)


def clean_and_queue_urls(soup,
                         page_counter: int,
                         curr_url: str,
                         true_url: str,
                         tovisit_q,
                         writeto_q,
                         pdflink_q,
                         visited_qs,
                         tovisit_qs,
                         ignore,
                         lmt_doma: str = '',
                         lmt_path: str = '',
                         class_ = None):
    '''
    Takes a list of urls from the current page being visited and adds
    them to the queue of urls to be visited by the scraper if they
    have not been visited already.

    Inputs:
        - urls: (list of strings) list of urls from the current page.
        - true_url: (string) url of the page currently being visited.
        - limiting_domain: (string) domain to filter out urls not belonging
        to the same domain.
        - queue: (Queue object) queue holding urls to visit in first-in-first
        out order.
        - scraped_data: (dict of lists) list of urls that have been visited.

    Returns: None - the function will add to the any url not visited before.
    '''
    urls = get_urls(soup, class_)

    for url in urls:

        url = remove_fragment(url)

        if not link_filter(url):
            continue

        url = convert_if_relative_url(true_url, url)

        if '.pdf' in url:
            pdflink_q.put(url)

        if (is_url_ok_to_follow(url,
                               lmt_doma,
                               lmt_path,
                               ignore) and
            not check_ifin_queue(tovisit_qs, url) and
            not check_ifin_queue(visited_qs, url)):

            try:
                tovisit_q.put((page_counter, url))

            except:
                continue


def add_to_queue_set(queue, url):
    '''
    Helper function to handle updates to a set within a Queue object.
    '''
    s = queue.get()
    s.add(url)
    queue.put(s)
    return queue


def check_ifin_queue(queue, url):
    '''
    Helper function to check whether a URL is already in the set within a Queue
    '''
    if queue.qsize() == 0:
        return False
    s = queue.get()
    if url in s:
        queue.put(s)
        return True
    queue.put(s)
    return False


def link_filter(url):
    '''
    Helper function to filter out links that aren't URLs
    '''
    if url == '':
        return None
    if "mailto:" in url:
        return None
    if "javascript:" in url:
        return None
    if "@" in url:
        return None
    return url


def site_prefix(url, limiting_domain):
    '''
    Helper function to handle URLs with the same domain but with leading prefix
    '''
    parsed_url = urllib.parse.urlparse(url)
    loc = parsed_url.netloc
    loc_len = len(loc) - 4
    lim_len = len(limiting_domain)
    if (limiting_domain in loc) and (loc_len != lim_len):
        return url


def get_urls(soup, limit_to_section = None):
    '''
    Takes an html page's soup and returns all anchor links on the page.

    Input:
        - soup (bs4 object): the page to be scraped
        - limit_to_section (string): if you wish to limit the scrape to a
        subsection of the page, set limit_to_section to the appropriate
        html class of the div tag type.

    Returns: urls (list of strings) all url strings on the page
    '''
    if limit_to_section:
        try:
            soup = soup.find_all('div', class_ = limit_to_section)[0]
        except:
            pass

    url_soup = soup.find_all('a')
    urls = []
    for url in url_soup:
        try:
            urls.append(url['href'])
        except:
            continue

    return urls


def request_to_soup(request):
    '''
    Takes a request and returns a BeautifulSoup object.

    Input:
        - request (req object) the request for which html will be stored

    Returns: soup (bs4 object) the html soup
    '''

    html = read_request(request)
    soup = bs4.BeautifulSoup(html, 'html5lib')
    return soup


def get_request(url):
    '''
    Open a connection to the specified URL and if successful
    read the data.

    Inputs:
        url: must be an absolute URL

    Outputs:
        request object or None

    Examples:
        get_request("http://www.cs.uchicago.edu")
    '''

    if is_absolute_url(url):
        try:
            r = requests.get(url)
            if r.status_code == 404 or r.status_code == 403:
                r = None
        except Exception:
            # fail on any kind of error
            r = None
    else:
        r = None

    return r


def read_request(request):
    '''
    Return data from request object.  Returns result or "" if the read
    fails..
    '''

    try:
        return request.text.encode('utf8')
    except:
        if request == None:
            print("***request failed: " + url)
            return ""
        # elif request.url:
        #     print("***read failed: " + request.url)
        #     return ""


def get_true_url(request):
    '''
    Extract true URL from the request
    '''
    return request.url


def is_absolute_url(url):
    '''
    Is url an absolute URL?
    '''
    if url == "":
        return False
    return urllib.parse.urlparse(url).netloc != ""


def remove_fragment(url):
    '''remove the fragment from a url'''
    (url, frag) = urllib.parse.urldefrag(url)
    return url


def convert_if_relative_url(current_url, new_url):
    '''
    Attempt to determine whether new_url is a relative URL and if so,
    use current_url to determine the path and create a new absolute
    URL.  Will add the protocol, if that is all that is missing.

    Inputs:
        current_url: absolute URL
        new_url:

    Outputs:
        new absolute URL or None, if cannot determine that
        new_url is a relative URL.

    Examples:
        convert_if_relative_url("http://cs.uchicago.edu", "pa/pa1.html") yields
            'http://cs.uchicago.edu/pa/pa.html'

        convert_if_relative_url("http://cs.uchicago.edu", "foo.edu/pa.html")
            yields 'http://foo.edu/pa.html'
    '''
    if new_url == "" or not is_absolute_url(current_url):
        return None
    if is_absolute_url(new_url):
        return new_url

    parsed_url = urllib.parse.urlparse(new_url)
    path_parts = parsed_url.path.split("/")

    if len(path_parts) == 0:
        return None
    ext = path_parts[0][-4:]
    if ext in [".edu", ".org", ".com", ".net"]:
        return "http://" + new_url
    elif new_url[:3] == "www":
        return "http://" + new_url
    else:
        return urllib.parse.urljoin(current_url, new_url)


def is_url_ok_to_follow(url, limiting_domain, limiting_path = None, ignore = None):
    '''
    Inputs:
        url: absolute URL
        limiting domain: domain name

    Outputs:
        Returns True if the protocol for the URL is HTTP, the domain
        is in the limiting domain, and the path is either a directory
        or a file that has no extension or ends in .html. URLs
        that include an "@" are not OK to follow.

    Examples:
        is_url_ok_to_follow("http://cs.uchicago.edu/pa/pa1", "cs.uchicago.edu")
            yields True

        is_url_ok_to_follow("http://cs.cornell.edu/pa/pa1", "cs.uchicago.edu")
            yields False
    '''
    if is_outside_domain(url, limiting_domain):
        return False
    if ignore:
        for word in ignore:
            if word in url:
                return False
    if limiting_path not in url:
        return False
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme != "http" and parsed_url.scheme != "https":
        return False
    (filename, ext) = os.path.splitext(parsed_url.path)
    return (ext == "" or ext == ".html")
    # does it have the right extension


def is_url(url):
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme != "http" and parsed_url.scheme != "https":
        return False
    if parsed_url.netloc == "":
        return False
    if parsed_url.fragment != "":
        return False
    return True


def is_outside_domain(url, limiting_domain):
    parsed_url = urllib.parse.urlparse(url)
    loc = parsed_url.netloc
    ld = len(limiting_domain)
    trunc_loc = loc[-(ld+1):]
    if not (limiting_domain == loc or (trunc_loc == "." + limiting_domain)):
        return True
