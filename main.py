
import os
import sys
from bbc_news_analyzer import get_latest_bbc_news, analyze_news_with_gemini
from tweet_poster import post_tweet

def main():
    print("Starting BBC News Analysis and X Post App...")

    # 1. BBCニュースの取得
    article_title, article_url = get_latest_bbc_news()
    if not article_title or not article_url:
        print("Failed to retrieve latest BBC News. Exiting.")
        sys.exit(1)

    # 2. Geminiによる分析コメントの生成
    tweet_text = analyze_news_with_gemini(article_title, article_url)
    if not tweet_text:
        print("Failed to generate analysis with Gemini. Exiting.")
        sys.exit(1)

    print(f"Generated Tweet Text: {tweet_text}")
    print(f"Tweet Text Length (full-width count): {len(tweet_text)}") # Pythonのlen()は半角全角区別しないため注意

    # 3. Xへの投稿
    if os.environ.get("POST_TO_X", "false").lower() == "true":
        print("Attempting to post to X...")
        if post_tweet(tweet_text):
            print("Tweet posted successfully!")
        else:
            print("Failed to post tweet to X.")
            sys.exit(1)
    else:
        print("Skipping X post as POST_TO_X environment variable is not set to 'true'.")
        print("To enable posting, set POST_TO_X=true in your environment variables or GitHub Actions secrets.")

    print("App finished.")

if __name__ == "__main__":
    main()

