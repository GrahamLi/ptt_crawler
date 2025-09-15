import requests
from bs4 import BeautifulSoup

def get_ptt_articles(board_name='Stock'):
    """
    爬取指定 PTT 看板的第一頁文章列表。

    Args:
        board_name (str): PTT 看板名稱，例如 'Stock'。

    Returns:
        list: 包含每篇文章標題和連結的列表。
    """
    url = f'https://www.ptt.cc/bbs/{board_name}/index.html'
    
    # 確保 PTT 伺服器會接受我們的請求，需要加上 User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f'正在爬取 {url}...')
    
    try:
        # 發送 HTTP GET 請求
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 如果請求失敗，會拋出 HTTPError
        
        # 使用 BeautifulSoup 解析 HTML 內容
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找所有 class 為 'r-ent' 的 div 標籤，這些標籤包含了文章資訊
        articles = soup.find_all('div', class_='r-ent')
        
        article_list = []
        for article in articles:
            # 尋找每篇文章的標題和連結
            title_tag = article.find('div', class_='title')
            
            # 確保文章標題存在，因為有些文章可能已被刪除
            if title_tag and title_tag.a:
                title = title_tag.a.text.strip()
                link = 'https://www.ptt.cc' + title_tag.a['href']
                article_list.append({'title': title, 'link': link})
                
        return article_list
        
    except requests.exceptions.RequestException as e:
        print(f"爬取失敗: {e}")
        return []

if __name__ == '__main__':
    articles = get_ptt_articles('Stock')
    if articles:
        print('\nPTT Stock 版最新文章：')
        for i, article in enumerate(articles):
            print(f'{i+1}. 標題：{article["title"]}')
            print(f'   連結：{article["link"]}')
            print('-' * 20)
    else:
        print('沒有找到文章。')