import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import argparse

def clean_input(text):
    """
    預處理輸入的字串，移除所有空白字元。
    """
    if isinstance(text, str):
        return text.strip().replace(' ', '').replace('　', '')
    return text

def get_ptt_articles(keywords, months, author=None, push_count=None, exclude_keywords=None, board_name='Stock'):
    """
    根據關鍵字、時間、作者、推文數及排除關鍵字，爬取 PTT 看板文章。

    Args:
        keywords (list): 必填。搜尋的關鍵字列表。
        months (int): 必填。從當前日期往回推算的月份數。
        author (str): 選填。作者名稱。
        push_count (int): 選填。文章推文數的門檻。
        exclude_keywords (list): 選填。排除的關鍵字列表。
        board_name (str): PTT 看板名稱，例如 'Stock'。
    """
    
    # 預處理輸入參數
    cleaned_keywords = [clean_input(kw) for kw in keywords] if keywords else []
    cleaned_exclude_keywords = [clean_input(kw) for kw in exclude_keywords] if exclude_keywords else []
    cleaned_author = clean_input(author)
    
    # 設定目標時間範圍
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    # 初始化爬蟲參數
    url = f'https://www.ptt.cc/bbs/{board_name}/index.html'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    all_articles = []
    page_count = 0
    
    print(f'正在爬取 PTT {board_name} 看板，搜尋符合以下條件的文章:')
    print(f'  - 關鍵字 (AND): {keywords}')
    print(f'  - 時間範圍: 過去 {months} 個月')
    if author:
        print(f'  - 作者: {author}')
    if push_count:
        print(f'  - 推文數 >= {push_count}')
    if exclude_keywords:
        print(f'  - 排除關鍵字 (OR): {exclude_keywords}')
    print('---')
    
    while True:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = soup.find_all('div', class_='r-ent')
            is_oldest_article_reached = False
            
            for article in articles:
                title_tag = article.find('div', class_='title')
                date_tag = article.find('div', class_='date')
                author_tag = article.find('div', class_='author')
                push_tag = article.find('div', class_='nrec')
                
                if not (title_tag and date_tag and author_tag and push_tag):
                    continue
                
                article_title = title_tag.a.text.strip() if title_tag.a else '無標題'
                article_link = 'https://www.ptt.cc' + title_tag.a['href'] if title_tag.a else None
                
                try:
                    article_date = datetime.strptime(date_tag.text.strip(), '%m/%d')
                    if article_date > datetime.now(): 
                        article_date = article_date.replace(year=datetime.now().year - 1)
                    else:
                        article_date = article_date.replace(year=datetime.now().year)
                except ValueError:
                    continue

                if article_date < start_date:
                    is_oldest_article_reached = True
                    break
                
                # 判斷是否符合所有關鍵字 (交集)
                title_cleaned = clean_input(article_title)
                if cleaned_keywords:
                    if not all(kw in title_cleaned for kw in cleaned_keywords):
                        continue
                
                # 判斷是否包含排除關鍵字 (聯集)
                if cleaned_exclude_keywords:
                    if any(kw in title_cleaned for kw in cleaned_exclude_keywords):
                        continue
                
                # 檢查是否符合作者條件 (如果作者參數有填寫)
                article_author = author_tag.text.strip()
                if cleaned_author and cleaned_author != clean_input(article_author):
                    continue
                
                # 檢查是否符合推文數條件 (如果推文數參數有填寫)
                article_push = push_tag.text.strip()
                article_push_count = 0
                if article_push == '爆':
                    article_push_count = 100
                elif article_push.isdigit():
                    article_push_count = int(article_push)
                elif article_push.startswith('X'):
                    remaining_str = article_push.replace('X', '')
                    if remaining_str.isdigit():
                        article_push_count = int(remaining_str) * 100
                    else:
                        article_push_count = 100
                
                if push_count and article_push_count < push_count:
                    continue
                
                # 如果所有條件都符合，抓取文章內文
                article_content, article_summary = get_article_content(article_link, article_author)
                
                # 將符合條件的文章資訊加入列表
                all_articles.append({
                    'title': article_title,
                    'link': article_link,
                    'date': article_date.strftime('%Y-%m-%d'),
                    'author': article_author,
                    'push_count': article_push_count,
                    'content': article_content,
                    'summary': article_summary
                })
                
                print(f'找到一篇文章: {article_title} (作者: {article_author}, 推文: {article_push_count})')
                
            if is_oldest_article_reached or page_count > 500:
                print('已達到時間範圍邊界，或已爬取大量頁面，停止爬取。')
                break
                
            prev_page_link = soup.find('a', class_='btn wide', string='‹ 上頁')
            if prev_page_link:
                url = 'https://www.ptt.cc' + prev_page_link['href']
                page_count += 1
            else:
                print('找不到上一頁連結，停止爬取。')
                break

        except requests.exceptions.RequestException as e:
            print(f"爬取失敗: {e}")
            break
            
    return all_articles

def get_article_content(url, author):
    """
    抓取單篇文章的內文和摘要。
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        main_content = soup.find(id='main-content')
        if not main_content:
            return "內容抓取失敗", "摘要抓取失敗"

        for tag in main_content.find_all('span', class_='f2'):
            tag.extract()
            
        for meta in main_content.find_all('div', class_='article-meta-value'):
            meta.extract()
            
        for push in main_content.find_all('div', class_='push'):
            push.extract()
        
        full_text = main_content.text.strip()
        
        summary = full_text.split('\n')[0][:50] + '...' if len(full_text) > 50 else full_text
        
        return full_text, summary

    except requests.exceptions.RequestException as e:
        print(f"內文爬取失敗: {e}")
        return "內容抓取失敗", "摘要抓取失敗"
        
if __name__ == '__main__':
    # 使用 argparse 來處理指令列參數
    parser = argparse.ArgumentParser(description='PTT 看板文章爬蟲工具')
    parser.add_argument('--keyword', type=str, required=False, help='搜尋的關鍵字，多個關鍵字請用逗號分隔 (ex: "台積電,情報")')
    parser.add_argument('--months', type=int, required=True, help='從當前日期往回推算的月份數')
    parser.add_argument('--author', type=str, required=False, help='作者名稱 (選填)')
    parser.add_argument('--push_count', type=int, required=False, help='推文數門檻 (選填)')
    parser.add_argument('--exclude', type=str, required=False, help='排除的關鍵字，多個關鍵字請用逗號分隔 (ex: "新聞,處份")')
    
    args = parser.parse_args()

    # 解析逗號分隔的關鍵字字串
    keywords = args.keyword.split(',') if args.keyword else []
    exclude_keywords = args.exclude.split(',') if args.exclude else []
    
    # 呼叫爬蟲函式，並傳入解析後的參數
    results = get_ptt_articles(
        keywords=keywords,
        months=args.months,
        author=args.author,
        push_count=args.push_count,
        exclude_keywords=exclude_keywords
    )
    
    # 顯示結果
    print('\n' + '='*50)
    print(f'共找到 {len(results)} 篇符合條件的文章。')
    print('='*50)
    
    for i, article in enumerate(results):
        print(f'文章 {i+1}:')
        print(f'  標題: {article["title"]}')
        print(f'  連結: {article["link"]}')
        print(f'  作者: {article["author"]}')
        print(f'  推文數: {article["push_count"]}')
        print(f'  摘要: {article["summary"]}')
        print('-' * 20)
        
    if not results:
        print('沒有找到符合條件的文章。')