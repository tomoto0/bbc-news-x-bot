
import tweepy
import os

def post_tweet(tweet_text):
    consumer_key = os.environ.get("TWITTER_API_KEY")
    consumer_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("Error: X API keys are not set in environment variables.")
        return False

    try:
        # Authenticate with X API v1.1 for media upload (if needed, though not for this task)
        # and v2 for tweeting
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        response = client.create_tweet(text=tweet_text)
        print(f"Tweet posted successfully: {response.data["id"]}")
        return True
    except tweepy.TweepyException as e:
        print(f"Error posting tweet: {e}")
        return False

if __name__ == "__main__":
    # This part is for testing purposes. In the actual workflow, tweet_text will come from bbc_news_analyzer.py
    test_tweet = "これはテストツイートです。BBCニュース分析アプリからの投稿をシミュレートします。https://www.bbc.com/news/politics/12345678901234567890123"
    if post_tweet(test_tweet):
        print("Test tweet successful.")
    else:
        print("Test tweet failed.")

