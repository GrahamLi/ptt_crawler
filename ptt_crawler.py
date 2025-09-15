import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import argparse
import time # 新增這一行
import random # 新增這一行

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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
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
            # 隨機等待 1 到 3 秒，降低被偵測為機器人的風險
            time.sleep(random.uniform(1, 3)) 
            
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
                    # 補上年份
                    current_year = datetime.now().year
                    if article_date.month > datetime.now().month or \
                       (article_date.month == datetime.now().month and article_date.day > datetime.now().day):
                        # 如果文章月份或日期晚於當前月份日期，可能是去年文章
                        article_date = article_date.replace(year=current_year - 1)
                    else:
                        article_date = article_date.replace(year=current_year)
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
                        article_push_count = int(remaining_str) * 100 # X1 = 100, X2 = 200
                    else:
                        article_push_count = 100 # 單純的 'X' 也視為 100 推
                
                if push_count and article_push_count < push_count:
                    continue
                
                # 如果所有條件都符合，抓取文章內文
                article_content, article_summary = get_article_content(article_link, article_author)
                
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
                
            if is_oldest_article_reached or page_count > 500: # 增加頁數上限以防萬一
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
            print(f"爬取頁面失敗: {url} - {e}")
            print("等待一段時間後重試...")
            time.sleep(random.uniform(5, 10)) # 遇到錯誤時等待更久
            # 不直接中斷，讓它有機會重試
            
    return all_articles

def get_article_content(url, author, retries=3):
    """
    抓取單篇文章的內文和摘要，並加入重試機制。
    """
    for i in range(retries):
        try:
            time.sleep(random.uniform(0.5, 1.5)) # 抓取內文前也稍作等待
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            main_content = soup.find(id='main-content')
            if not main_content:
                print(f"文章內文區塊未找到: {url}")
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
            if i < retries - 1:
                print(f"內文爬取失敗 (第 {i+1} 次重試): {url} - {e}")
                time.sleep(random.uniform(3, 7)) # 重試前等待
            else:
                print(f"內文爬取失敗 (已達最大重試次數): {url} - {e}")
                return "內容抓取失敗", "摘要抓取失敗"
    return "內容抓取失敗", "摘要抓取失敗" # 萬一迴圈結束都沒成功

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PTT 看板文章爬蟲工具')
    parser.add_argument('--keyword', type=str, required=False, help='搜尋的關鍵字，多個關鍵字請用逗號分隔 (ex: "台積電,情報")')
    parser.add_argument('--months', type=int, required=True, help='從當前日期往回推算的月份數')
    parser.add_argument('--author', type=str, required=False, help='作者名稱 (選填)')
    parser.add_argument('--push_count', type=int, required=False, help='推文數門檻 (選填)')
    parser.add_argument('--exclude', type=str, required=False, help='排除的關鍵字，多個關鍵字請用逗號分隔 (ex: "新聞,處份")')
    
    args = parser.parse_args()

    # 解析逗號分隔的關鍵字字串
    keyword_list = args.keyword.split(',') if args.keyword else []
    exclude_keyword_list = args.exclude.split(',') if args.exclude else []
    
    # 呼叫爬蟲函式，並傳入解析後的參數
    results = get_ptt_articles(
        keywords=keyword_list,
        months=args.months,
        author=args.author,
        push_count=args.push_count,
        exclude_keywords=exclude_keyword_list
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