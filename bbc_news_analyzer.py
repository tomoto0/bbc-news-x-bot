import os
import re
import unicodedata
from html import unescape
from xml.etree import ElementTree as ET

import google.generativeai as genai
import requests
from bs4 import BeautifulSoup


def get_latest_bbc_news():
    """Return the latest BBC News article title and URL.

    BBC's homepage markup is unstable and often changes without notice, so the
    scraper is intentionally resilient: prefer the official RSS feed, then fall
    back to a generic homepage scan if needed.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def parse_rss_feed(feed_url):
        try:
            response = requests.get(feed_url, headers=headers, timeout=20)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            print(f"Error fetching BBC RSS feed: {exc}")
            return None, None

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            print(f"Error parsing BBC RSS feed: {exc}")
            return None, None

        item = root.find("./channel/item")
        if item is None:
            print("Could not find any article in BBC News RSS feed.")
            return None, None

        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()

        if not title or not link:
            print("BBC RSS item is missing a title or link.")
            return None, None

        title = BeautifulSoup(unescape(title), "html.parser").get_text(strip=True)
        print(f"Found article via RSS: {title} - {link}")
        return title, link

    def parse_homepage(url):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            print(f"Error fetching BBC News homepage: {exc}")
            return None, None

        soup = BeautifulSoup(response.content, "html.parser")
        main_content = soup.find("main") or soup.find("article") or soup

        for link in main_content.find_all("a", href=True):
            href = link["href"]
            if re.match(r"^(https?://)?(www\.)?bbc\.(com|co\.uk)/news/.*", href):
                title = link.get_text(" ", strip=True)
                if not title:
                    title = link.get("aria-label") or ""
                if title:
                    normalized_link = href if href.startswith("http") else f"https://www.bbc.com{href}"
                    print(f"Found article via homepage fallback: {title} - {normalized_link}")
                    return title, normalized_link

        print("Could not find a suitable article on BBC News homepage.")
        return None, None

    rss_title, rss_link = parse_rss_feed("https://feeds.bbci.co.uk/news/rss.xml")
    if rss_title and rss_link:
        return rss_title, rss_link

    return parse_homepage("https://www.bbc.com/news")


def get_char_width(text):
    """全角・半角を考慮した文字幅を計算する"""
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ("F", "W", "A"):  # Full-width, Wide, Ambiguous
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

    # 利用可能なモデルをリストし、適切なモデルを選択
    model_name = None
    available_models = []
    try:
        for m in genai.list_models():
            available_models.append(m.name)
            if "generateContent" in m.supported_generation_methods:
                if "gemini-2.5-flash" in m.name:
                    model_name = m.name
                    break
    except Exception as e:
        print(f"Error listing Gemini models: {e}")
        print(f"Available models (if any were listed before error): {available_models}")
        return None

    print(f"All available models: {available_models}")
    print(f"Selected model: {model_name}")

    if not model_name:
        print("Error: No suitable Gemini model found that supports generateContent.")
        return None

    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Error initializing Gemini model {model_name}: {e}")
        return None

    # URLは全角23文字としてカウント
    url_counted_width = 23
    # ツイート本文の最大文字幅 (全角140文字)
    max_tweet_width = 140 * 2  # 全角1文字を2幅として計算
    # URLとスペースの分を引いた分析コメントの最大文字幅
    max_analysis_width = max_tweet_width - url_counted_width - get_char_width(" ")  # スペース1文字分

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
