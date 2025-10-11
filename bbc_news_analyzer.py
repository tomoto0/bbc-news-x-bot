
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import unicodedata
import re

def get_latest_bbc_news():
    url = "https://www.bbc.com/news/politics"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # HTTPエラーがあれば例外を発生させる
    except requests.exceptions.RequestException as e:
        print(f"Error fetching BBC News: {e}")
        return None, None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    latest_article_title = None
    latest_article_link = None
    
    # ニュース記事のブロックを特定するためのセレクタ
    # BBCのニュースページでは、記事がgs-c-promoクラスを持つdiv要素内に配置されていることが多い
    # または、gel-layout__itemクラスを持つdiv要素内に配置されていることもある
    article_blocks = soup.select('div.gs-c-promo, div.gel-layout__item')
    
    # 記事ブロックをループして、タイトルとリンク、そして時間情報を取得
    for block in article_blocks:
        link_tag = block.select_one('h3.gs-c-promo-heading a.gs-c-promo-heading__link, h3 a')
        time_tag = block.select_one('span.gs-c-promo-meta__time')
        
        if link_tag and link_tag.has_attr('href'):
            title = link_tag.get_text(strip=True)
            href = link_tag['href']
            if href.startswith('/'):
                link = "https://www.bbc.com" + href
            else:
                link = href
            
            # 時間情報があれば、最新の記事を判断するのに役立つ
            if time_tag:
                time_text = time_tag.get_text(strip=True)
                # ここでは単純に最初に見つかった有効な記事を最新とみなす
                # より厳密な時間比較を行うことも可能だが、まずは記事が見つかることを優先
                latest_article_title = title
                latest_article_link = link
                print(f"Found potential article: {title} - {link} ({time_text})")
                break # 最初に見つかった記事を最新とみなして終了
            elif not latest_article_title: # 時間情報がない場合でも、最初の記事を確保
                latest_article_title = title
                latest_article_link = link
                print(f"Found potential article (no time info): {title} - {link}")
                # 時間情報がない場合は、より下位のセレクタでより新しい記事が見つかる可能性があるのでbreakしない

    if latest_article_title and latest_article_link:
        print(f"Selected latest article: {latest_article_title} - {latest_article_link}")
        return latest_article_title, latest_article_link
    else:
        print("Could not find a suitable article on BBC News Politics page.")
        return None, None

def get_char_width(text):
    """全角・半角を考慮した文字幅を計算する"""
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ('F', 'W', 'A'): # Full-width, Wide, Ambiguous
            width += 2
        else:
            width += 1
    return width

def analyze_news_with_gemini(article_title, article_url):
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        print("Error: GEMINI_API_KEY is not set in environment variables.")
        return None

    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-pro')

    # URLは全角23文字としてカウント
    url_counted_width = 23
    # ツイート本文の最大文字幅 (全角140文字)
    max_tweet_width = 140 * 2 # 全角1文字を2幅として計算
    # URLとスペースの分を引いた分析コメントの最大文字幅
    max_analysis_width = max_tweet_width - url_counted_width - get_char_width(' ') # スペース1文字分

    prompt = f"""
以下のBBCニュース記事のタイトルとURLを元に、政治家や専門家が関心を持つような分析コメントを日本語で作成してください。
コメントは全角換算で{max_analysis_width // 2}文字以内に収めてください。記事のURLはコメントの最後に含めてください。

タイトル: {article_title}
URL: {article_url}

分析コメント:
"""
    
    try:
        response = model.generate_content(prompt)
        analysis = response.text.strip()
        
        # Geminiからの応答が指定文字数を超過している可能性があるので、再度調整
        current_analysis_width = get_char_width(analysis)
        if current_analysis_width > max_analysis_width:
            # 幅で切り詰めるため、文字単位で調整
            truncated_analysis = ""
            current_width = 0
            for char in analysis:
                char_width = get_char_width(char)
                if current_width + char_width <= max_analysis_width:
                    truncated_analysis += char
                    current_width += char_width
                else:
                    break
            analysis = truncated_analysis

        final_tweet_text = f"{analysis} {article_url}"
        
        # 最終的な文字数チェック（デバッグ用）
        print(f"Final tweet text: {final_tweet_text}")
        print(f"Final tweet width: {get_char_width(final_tweet_text)} (should be <= {max_tweet_width})")
        
        return final_tweet_text
    except Exception as e:
        print(f"Error generating content with Gemini API: {e}")
        return None

if __name__ == "__main__":
    # 環境変数が設定されていることを確認 (テスト用)
    # os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY" # 実際のキーに置き換えるか、環境変数として設定
    
    title, url = get_latest_bbc_news()
    if title and url:
        tweet_text = analyze_news_with_gemini(title, url)
        if tweet_text:
            print("Generated Tweet:")
            print(tweet_text)
            print(f"Tweet character width: {get_char_width(tweet_text)}")
    else:
        print("Failed to get BBC news or analyze it.")

