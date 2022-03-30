def clean_text(s):
  st = ''.join([i if ord(i) < 128 else ' ' for i in s])
  st = st.replace('"', '')
  st = st.replace('.', '')
  st = st.replace(')', '').replace('(', '')
  st = st.replace(",", '')
  return st.strip()

def user_serializer(user):
    user_dict = {}
    user_dict['id_str'] = str(user.id)
    user_dict['created_at'] = user.created.strftime("%a %b %d %H:%M:%S +0000 %Y")
    user_dict['followers_count'] = user.followersCount
    user_dict['friends_count'] = user.friendsCount
    user_dict['name'] = user.displayname
    user_dict['screen_name'] = user.username

    return user_dict

def tweet_serializer(tweet):
    tweet_dict = {}
    tweet_dict['created_at'] = tweet.date.strftime("%a %b %d %H:%M:%S +0000 %Y")
    tweet_dict['text'] = tweet.content
    tweet_dict['id_str'] = str(tweet.id)
    tweet_dict['in_reply_to_status_id_str'] = str(tweet.inReplyToTweetId) if tweet.inReplyToTweetId else None
    tweet_dict['in_reply_to_user_id_str'] = str(tweet.inReplyToUser.id) if tweet.inReplyToUser else None
    tweet_dict['is_quote_status'] = tweet.quotedTweet == None
    tweet_dict['retweet_count'] = tweet.retweetCount
    tweet_dict['favorite_count'] = tweet.likeCount
    tweet_dict['user'] = user_serializer(tweet.user)
    tweet_dict['entities'] = {
      'hastags': tweet.hashtags,
      'urls': [{
        'expanded_url': url
      } for url in tweet.outlinks] if tweet.outlinks else [], 
      'user_mentions': [{
        'id_str': str(tweet.user.id),
        'name': tweet.user.displayname,
        'screen_name': tweet.user.username
      } for user in tweet.mentionedUsers] if tweet.mentionedUsers else []
    }

    if tweet.quotedTweet is not None:
      tweet_dict['quoted_status'] = tweet_serializer(tweet.quotedTweet)

    if tweet.retweetedTweet is not None:
      tweet_dict['retweeted_status'] = tweet_serializer(tweet.retweetedTweet)
    
    return tweet_dict