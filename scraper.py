import pandas as pd
import nltk
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
import snscrape.modules.twitter as twitter
import googlesearch
from googlesearch import search
import inflect
import urllib
from newspaper import Article
from datetime import datetime

class TweetsScraper():

    def __init__(
        self,
        statement,
        num_news,
        since,
        until,
        inflect_func=None,
        statement_keywords=False,
        related_urls=False,
        google_keywords=False,
        google_urls=False,
        exclude_keywords=[],
        exclude_urls=[],
    ):
        self.statement = statement
        self.num_news = num_news
        self.since = since
        self.until = until
        self.inflect_func = inflect_func
        self.statement_keywords = statement_keywords
        self.related_urls = related_urls
        self.google_keywords = google_keywords
        self.google_urls = google_urls
        self.exclude_keywords = " ".join(exclude_keywords)
        self.exclude_urls = exclude_urls
        self.queries = None

        if self.inflect_func is None:
            p = inflect.engine()
            self.inflect_func = p.plural

    def get_queries_from_statement(self, s):
        q = []
        for i, j in nltk.pos_tag(clean_text(s).split()):
            if j in ['NNP', 'NNS', 'NNPS', 'NN', 'FW']:
                q.append(f"({i} OR {self.inflect_func(i)})")
            elif j == 'CD':
                q.append(i)

        return " ".join(q)

    def get_queries(self):
        s = clean_text(self.statement)
        queries = {}

        if self.exclude_urls is None:
            self.exclude_urls = ["www.politifact.com"]

        # Get relevant news article using Google search articles
        if self.google_urls or self.google_keywords:
            d_min = datetime.strptime(f"{self.since}", '%b-%d-%Y')
            d_max = datetime.strptime(f"{self.until}", '%b-%d-%Y')
            tbs = googlesearch.get_tbs(d_min, d_max)
            cnt = 0
            for i in search(s, tld="co.in", num=self.num_news, stop=None, pause=2, tbs=tbs):
                if cnt > 9:
                    break
                if urllib.parse.urlparse(i).netloc not in self.exclude_urls:
                    cnt += 1
                    if self.google_urls:
                        q = f"url:{i}"
                        queries[q] = queries.get(q, []) + ['google_urls']
                    if self.google_keywords:
                        a = Article(i, language="en")
                        a.download()
                        a.parse()
                        title = clean_text(a.title)
                        q = self.get_queries_from_statement(title)
                        queries[q] = queries.get(q, []) + ['google_keywords']

        # Build query from statement
        if self.statement_keywords:
            q = self.get_queries_from_statement(s)
            queries[q] = queries.get(q, []) + ['statement_keywords']

        # Build query from related_urls
        if self.related_urls:
            for i in self.related_urls:
                if urllib.parse.urlparse(i).netloc not in self.exclude_urls:
                    q = f"url:{i}"
                    queries[q] = queries.get(q, []) + ['related_urls']

        return queries

    def get_query_tweets(self, query, max_tweets):
        tweets = []
        for i, tweet in enumerate(twitter.TwitterSearchScraper(f'{query} -{self.exclude_keywords} since:{self.since} until:{self.until}').get_items()):
            if i > max_tweets-1:
                break
            tweets.append(tweet)
        return tweets

    def get_tweets(self, max_tweets, mode="ids"):
        self.queries = self.get_queries()
        if len(self.queries) == 0:
            raise Exception("No queries could be built for this statement")

        ids = set()
        tweets_all = []
        for query in self.queries:
            tweets = self.get_query_tweets(query, max_tweets)
            if mode == "ids":
                ids.update([tweet.id for tweet in tweets])
            elif mode == "stats":
                tweets_all.append({
                    'query': query,
                    'source': self.queries[query],
                    'tweets': [{
                        'id': tweet.id,
                        'date': tweet.date,
                        'content': tweet.content,
                        'url': tweet.url,
                    } for tweet in tweets]
                })

        if mode == "ids":
            return ids
        elif mode == "stats":
            return tweets_all
