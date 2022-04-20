import nltk
import snscrape.modules.twitter as twitter
import googlesearch
from googlesearch import search
import inflect
from newspaper import Article, ArticleException
from tweet_scraper.util import clean_text, user_serializer, tweet_serializer
from tqdm import tqdm
from datetime import datetime, timedelta
import urllib
from dataclasses import dataclass, field
from typing import List
from twython import TwythonRateLimitError, Twython
import time

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')

class TweetsScraper():

  def __init__(
      self,
      num_news, 
      since,
      until,
      APP_SECRET,
      APP_KEY,
      max_tweets=1000,
      statements=None,
      urls=False, 
      queries=None,
      inflect_func=None,
      url_search=False,
      keywords_from_urls=False,
      keywords_from_statement=False,
      get_related_news_keywords_from_statement=False,
      get_related_news_urls_from_statement=False,
      get_related_news_keywords_from_urls=False,
      get_related_news_urls_from_urls=False,
      fetch_retweets = False,
      fetch_replies = False,
      fetch_quotes = False,
      exclude_keywords = [],
      exclude_urls = [],
  ):
    self.statements = statements
    self.urls = urls
    self.num_news = num_news
    self.since = since
    self.until = until
    self.inflect_func = inflect_func
    self.queries = queries
    self.max_tweets = max_tweets

    self.twython_twitter = Twython(APP_KEY, APP_SECRET, oauth_version=2)
    ACCESS_TOKEN = self.twython_twitter.obtain_access_token()
    self.twython_twitter = Twython(APP_KEY, access_token=ACCESS_TOKEN)

    self.url_search = url_search
    self.keywords_from_urls = keywords_from_urls
    self.keywords_from_statement = keywords_from_statement
    self.get_related_news_keywords_from_statement = get_related_news_keywords_from_statement
    self.get_related_news_urls_from_statement = get_related_news_urls_from_statement
    self.get_related_news_keywords_from_urls = get_related_news_keywords_from_urls
    self.get_related_news_urls_from_urls = get_related_news_urls_from_urls

    self.exclude_keywords = exclude_keywords
    self.exclude_urls = exclude_urls

    self.fetch_retweets = fetch_retweets
    self.fetch_replies = fetch_replies
    self.fetch_quotes = fetch_quotes

    self.parent_dict = {}
    self.tweets = []
    self.quotes = []
    self.replies = []
    self.tweet_ids = set()
    self.retweets = {}

    if self.inflect_func is None:
      p = inflect.engine()
      self.inflect_func = p.plural

  def get_queries_from_statement(self, s):
    q = []
    for i,j in nltk.pos_tag(clean_text(s).split()):
      if j in ['NNP', 'NNS', 'NNPS', 'NN', 'FW', 'CD']:
        q.append(f"({i} OR {self.inflect_func(i)})")

    return " ".join(q)

  def set_parent(self, child, parent):
    if child not in self.parent_dict:
      self.parent_dict[child] = set()
    self.parent_dict[child].add(parent)

  def get_queries(self):
    queries = set()

    if self.exclude_urls is None:
      self.exclude_urls = []

    # Build query from statement
    if self.keywords_from_statement:
      for s in self.statements:
        
        self.set_parent(s, "statements")

        s = clean_text(s)
        q = self.get_queries_from_statement(s)
        queries.add(q)

    # Build query from urls
    headlines = set()
    if self.url_search or self.keywords_from_urls or self.get_related_news_keywords_from_urls or self.get_related_news_urls_from_urls:
      for i in self.urls:

        self.set_parent(i, "url")

        if urllib.parse.urlparse(i).netloc not in self.exclude_urls:
          if self.url_search:
            q = f"url:{i}"

            self.set_parent(q, i)

            queries.add(q)

          if self.keywords_from_urls or self.get_related_news_keywords_from_urls or self.get_related_news_urls_from_urls:
            article = Article(i)
            article.download()
            try:
              article.parse()
              if article.title:
                title = clean_text(article.title)
                if self.get_related_news_keywords_from_urls or self.get_related_news_urls_from_urls:
                  
                  self.set_parent(title, i)
                  
                  headlines.add(title)

                if self.keywords_from_urls:
                  q = self.get_queries_from_statement(title)

                  self.set_parent(q, title)

                  queries.add(q)
            except ArticleException:
              continue

    # Get relevant news article using urls
    if self.get_related_news_keywords_from_urls or self.get_related_news_urls_from_urls:
      # d_min = datetime.strptime(f"{self.since}", '%Y-%m-%d') - timedelta(days=10)
      # d_max = datetime.strptime(f"{self.until}", '%Y-%m-%d')
      # tbs = googlesearch.get_tbs(d_min, d_max)

      for headline in headlines:
        news_cnt = 0
        for i in search(headline, tld="co.in", num=10, stop=None, pause=2):
          if news_cnt == self.num_news:
            break

          self.set_parent(i, headline)    

          if urllib.parse.urlparse(i).netloc not in self.exclude_urls:
            news_cnt += 1
            if self.get_related_news_urls_from_urls:
              q = f"url:{i}"

              self.set_parent(q, i)

              queries.add(q)
            if self.get_related_news_keywords_from_urls:
              try:
                a = Article(i, language="en")
                a.download()
                a.parse()
                title = clean_text(a.title)
                self.set_parent(title, i)
                q = self.get_queries_from_statement(title)
                self.set_parent(q, title)
                queries.add(q)
              except ArticleException:
                continue

    # Get relevant news article using statement
    if self.get_related_news_keywords_from_statement or self.get_related_news_urls_from_statement:
      # d_min = datetime.strptime(f"{self.since}", '%Y-%m-%d') - timedelta(days=30)
      # d_max = datetime.strptime(f"{self.until}", '%Y-%m-%d')
      # tbs = googlesearch.get_tbs(d_min, d_max)

      for s in self.statements:
        s = clean_text(s)
        self.set_parent(s, "statements")
        news_cnt = 0
        for i in search(s, tld="co.in", num=10, stop=None, pause=2):
          if news_cnt == self.num_news:
            break
          self.set_parent(i, s)
          if urllib.parse.urlparse(i).netloc not in self.exclude_urls:
            news_cnt += 1
            if self.get_related_news_urls_from_statement:
              q = f"url:{i}"
              self.set_parent(q, i)
              queries.add(q)
            if self.get_related_news_keywords_from_statement:
              try:
                a = Article(i, language="en")
                a.download()
                a.parse()
                title = clean_text(a.title)
                self.set_parent(title, i)
                q = self.get_queries_from_statement(title)
                self.set_parent(q, title)
                queries.add(q)
              except ArticleException:
                continue

    return queries

  def get_query_tweets(self, query):
    for i,tweet in enumerate(twitter.TwitterSearchScraper(f'{query} -{self.exclude_keywords} since:{self.since} until:{self.until}').get_items()):
      if i > self.max_tweets:
        break
      if str(tweet.id) not in self.tweet_ids:
        tweet = tweet_serializer(tweet)
        self.tweets.append(tweet)
        self.tweet_ids.add(tweet["id_str"])

  def get_base_tweets(self):
    if self.queries is None:
      start = time.perf_counter()
      self.queries = self.get_queries()
      end = time.perf_counter()
      print(f"Built {len(self.queries)} queries in {end-start} seconds")

    start = time.perf_counter()
    for query in self.queries:
      self.get_query_tweets(query)
    end = time.perf_counter()
    print(f"Built {len(self.tweets)} tweets in {end-start} seconds")

  def get_retweets(self):
    tweet_ids = list(self.tweet_ids)
    ind = 0
    while ind < len(tweet_ids):
      try:
        self.retweets[tweet_ids[ind]] = self.twython_twitter.get_retweets(id=tweet_ids[ind], count=100)
        ind += 1
      except TwythonRateLimitError as e:
        time.sleep((int(e.retry_after) - time.time()) + 1)

  def get_quotes(self):
    for tweet_id in self.tweet_ids:
      for i,quote in enumerate(twitter.TwitterSearchScraper(f'https://twitter.com/i/web/status/{tweet_id}').get_items()):
        if str(quote.id) not in self.tweet_ids:
          quote = tweet_serializer(quote)
          self.quotes.append(quote)

  def get_replies(self):
    for tweet_id in self.tweet_ids:
      for i,reply in enumerate(twitter.TwitterTweetScraper(tweet_id, mode=twitter.TwitterTweetScraperMode.SINGLE).get_items()):
        if str(reply.id) not in self.tweet_ids:
          reply = tweet_serializer(reply)
          self.replies.append(reply)

  def get_twitter_data(self):
    self.get_base_tweets()

    if self.fetch_retweets:
      print("Fetching Retweets")
      start = time.perf_counter()
      self.get_retweets()
      end = time.perf_counter()
      print(f"Fetched {sum([len(i) for i in self.retweets.values()])} retweets in {end-start} seconds")

    if self.fetch_quotes:
      print("Fetching Quotes")
      start = time.perf_counter()
      self.get_quotes()
      end = time.perf_counter()
      print(f"Fetched {len(self.quotes)} quotes in {end-start} seconds")
    
    if self.fetch_replies:
      print("Fetching Replies")
      start = time.perf_counter()
      self.get_replies()
      end = time.perf_counter()
      print(f"Fetched {len(self.replies)} replies in {end-start} seconds")

    return {
      "tweets": self.tweets,
      "retweets": self.retweets,
      "quotes": self.quotes,
      "replies": self.replies
    }
    
    