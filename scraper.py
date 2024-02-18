import re
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from tokenizer.PartA import tokenizeString, computeWordFrequencies, removeStopwords
from globals import longestPage, totalWordFrequency, uniquePages, icsUciEdu, allPages

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    if resp.status == 200 and canCrawl(resp.url):
        validLinks = list()
        # Get raw content and turn into BeautifulSoup object to work with
        soup = BeautifulSoup(resp.raw_response.content, "html.parser", from_encoding="iso-8859-1")
        text = soup.get_text()

        # Add page to list of unique pages
        uniquePages.add(resp.url)

        # Add to all pages
        allPages.append(resp.url)

        # Tokenize text and check for longest page contender
        tokens = tokenizeString(text)
        if len(tokens) > longestPage[1]:
            longestPage[0] = resp.url
            longestPage[1] = len(tokens)

        # Remove stopwords and compute word frequency
        tokens = removeStopwords(tokens)
        wordFrequency = computeWordFrequencies(tokens)
        for word in wordFrequency:
            if word in totalWordFrequency:
                totalWordFrequency[word] += wordFrequency[word]
            else:
                totalWordFrequency[word] = wordFrequency[word]

        # Get all links to other pages
        aTags = soup.find_all('a', href = True)
        # If relative path then turn into absolute path
        aTags = [urljoin(resp.url, a.get('href')) for a in aTags]

        # Remove the inclusion of fragments in link (turn all into the same link)
        for index in range(len(aTags)):
            if "#" in aTags[index]:
                aTags[index] = aTags[index][:aTags[index].index("#")]

        # Remove the inclusion of queries in link
        for index in range(len(aTags)):
            if "?" in aTags[index]:
                aTags[index] = aTags[index][:aTags[index].index("?")]


        # Check if domain is ics.uci.edu for report
        if "ics.uci.edu" in resp.url:
            # Get subdomain
            sub = resp.url[resp.url.index("//")+2:resp.url.index(".")]
            if sub in icsUciEdu:
                icsUciEdu[sub] += len(aTags)
            else:
                icsUciEdu[sub] = len(aTags)

        # Links to be returned to frontier if not already visited
        for tag in aTags:
            if str(tag) not in uniquePages:
                validLinks.append(str(tag))

        return validLinks
    return list()

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        # Check if domain contains any of the provided valid domains
        netLocation = parsed.netloc
        if not (".ics.uci.edu" in netLocation or ".cs.uci.edu" in netLocation or ".informatics.uci.edu" in netLocation or ".stat.uci.edu" in netLocation):
            return False
        
        # Check if invalid format
        invalidPaths = "(css|js|bmp|gif|jpe?g|ico|png|tiff?|mid|mp2|mp3|mp4|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1|thmx|mso|arff|rtf|jar|csv|rm|smil|wmv|swf|wma|zip|rar|gz)$"
        invalidPaths = invalidPaths.split('|')
        for invalid in invalidPaths:
            if invalid in parsed.path.lower() or invalid in parsed.query.lower():
                return False

        # This checks for repeated paths
        pathOnly = parsed.path.split('.')[0]
        pathList = pathOnly.split('/')
        if len(pathList) >= len(set(pathList)) + 2:
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def canCrawl(url):
    # Convert url to robots.txt url
    domain = urlparse(url).netloc
    robotsURL = "http://" + domain + "/robots.txt"
    
    # Request the robots.txt file
    # If robots.txt file DNE, crawl it
    try:
        response = requests.get(robotsURL)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        return True
    
    # Parse the robots.txt file
    lines = response.text.split('\n')

    # Find all User-agent: * entries
    ruleStart = lines.index("User-agent: *")
    lines = lines[ruleStart:]
    ruleEnd = lines.index('')
    userAgentRules = lines[1:ruleEnd]

    # If url contains a bad path, return false
    for rule in userAgentRules:
        if "Disallow:" in rule:
            badPath = rule[(rule.index(":") + 2):]
            if badPath in url:
                return False
    
    # If no rule specifically allows or disallows the URL, default to allowing
    return True