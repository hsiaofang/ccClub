#selenium 爬網頁
import os
import sys
import logging
import pandas as pd
import time
import random
import requests
import xlsxwriter
import urllib3 #https會有警告跳出來>去警告訊息用
from bs4 import BeautifulSoup, Comment
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import date

#不想被當機器人，設定等待時間 0.5秒～3秒 
#wait_time = random.randint(0.5,3)


query_name_list = ['法官李小芬', '法官林秋宜','法官陳柏宇',  '法官廖建傑', '法官解怡蕙', '法官林孟皇']
#'法官林虹翔', '法官黃博偉' >>>這兩個人案件數量太少
query_cause_list = ['殺人','傷害' ,'重傷', '妨害自由']

#爬取網頁幾頁
page_limit = 5 #最大25

#原本的def first_query_page(crime, place, path)
def first_query_page(query_name,query_cause):
    path = '/Users/rubysun/PythonProj/'
    opt = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=opt)
    url = 'https://judgment.judicial.gov.tw/FJUD/Default_AD.aspx'
    driver.get(url)
    time.sleep(random.uniform(1,3))
    #案件類別：刑事
    xpath_1 = "/html/body/form[@id='form1']/div[@id='center']/div[@class='main']/div[@class='search-area']/div[@id='advQuery']/div[@class='col-sm-9']/table[@class='search-table']/tbody/tr[1]/td/label[@id='vtype_M']/input"
    driver.find_element(By.XPATH,xpath_1).click()

    #裁判法院：台北地方法院
    xpath_2 = "/html/body/form[@id='form1']/div[@id='center']/div[@class='main']/div[@class='search-area']/div[@id='advQuery']/div[@class='col-sm-3']/div[@id='CourtContent']/select[@id='jud_court']/option[19]"
    driver.find_element(By.XPATH,xpath_2).click()
    time.sleep(random.uniform(0.5,3))

    #裁判案由(搜尋案由)cause_text
    cause = driver.find_element(By.NAME,"jud_title")
    #想搜尋什麼都打到content，目前輸入法官姓名
    cause.send_keys(query_cause)
    time.sleep(random.uniform(0.5,3))

    #全文內容(搜尋法官姓名)
    content = driver.find_element(By.NAME,"jud_kw")
    #想搜尋什麼都打到content，目前輸入法官姓名
    content.send_keys(query_name+' '+'刑事判決')
    time.sleep(random.uniform(0.5,3))
    query_name = query_name.replace('法官','')

    #送出查詢
    driver.find_element(By.ID, "btnQry").click()
    #driver.find_element(By.NAME,"ctl00$cp_content$btnQry").click()
    time.sleep(random.uniform(3,4))

    iframe = driver.find_element(By.TAG_NAME,'iframe')
    page_url = iframe.get_attribute("src")

    #印出到底查到幾個#但一頁不會有共幾筆的欄位
    xpath_span = '//*[@id="result-count"]/ul/li/a'
    span = driver.find_element(By.XPATH,xpath_span)
    span = BeautifulSoup(span.text, "html.parser")
    span_text = ''.join(span)
    span_text = span_text[4:].strip()
    span_text = f'{query_name}用案由:{query_cause}搜尋到{span_text}筆資料。（若超過500筆僅會擷取前500筆）'
    print(span_text)
    return page_url,query_name

#將網址解析的動作
def get_bs4_content(url):
    page_url = requests.get(url, verify=False)
    soup = BeautifulSoup(page_url.text, "html.parser")
    return soup

#取得全文
def get_full_text(content):
    nodes = content.find("body").find_all("td")
    full_text = ",".join([node.text for node in nodes])
    return full_text

#取得主文
def get_main_text(content):
    raw_text = content.find("body").find(
        "div", {"class": "text-pre text-pre-in"})
    sentences = raw_text.find_all(
        text=lambda text: isinstance(text, Comment))
    full_main_text = ",".join(sentences)
    #if 裁判referee >>>> 裁判類別：[裁定] =ruling / 裁判類別：[判決] =judgments
    #if 原因：[未成年子] =have_minor
    #主文：
    main_index = full_main_text.index('主文：')
    main_text = full_main_text[main_index:]

    #裁判種類
    if '裁判類別：[裁定]' in full_main_text:
        referee = '裁定'
    else:
        referee = '判決'

    #有無未成年子女
    if '原因：[未成年子]' in full_main_text:
        have_minor = 'Y'
    else:
        have_minor = 'N'

    return main_text,referee,have_minor

#裁判案由
def get_cause(content):
    #ＣＳＳ選擇器路徑：jud > div:nth-child(3) > div.col-td
    css_path ='#jud > div:nth-child(3) > div.col-td'
    #print(css_path)
    cause_text = content.select(css_path)[0]
    cause_text = cause_text.get_text().strip()
    return cause_text


#去掉警告
# InsecureRequestWarning: Unverified HTTPS request is being made to host 'judgment.judicial.gov.tw'. 
urllib3.disable_warnings()


page_urls =[]

for name in query_name_list:
    for cause in query_cause_list:
        page_urls.append(first_query_page(name,cause))

print(page_urls)

time.sleep(random.uniform(0.5,3))


article_data = pd.DataFrame()
num = 1

try:
    for url in page_urls:
        page_content = get_bs4_content(url[0])
        name = url[1]
        print('法官',name,'的案件開始爬！')
        page_num = 1
        print('進入while page_num少於',page_limit,'頁判斷 line 148')
        while True:
            if page_num <= page_limit:
                print('while page_num <= page_limit ==True  line 151')
                time.sleep(random.uniform(0.5,3))
                # get all links of articles of the page
                print('get all links of articles of the page line 154')
                article_urls = [
                    f'https://judgment.judicial.gov.tw/FJUD/{node.get("href")}'
                    for node in page_content.find_all("a", {"id": "hlTitle"})
                ]
                time.sleep(random.uniform(0.5,3))
                for article_url in article_urls:
                    print('每個網址輪流bs4,開始爬')
                    start_time = time.time()
                    content = get_bs4_content(url=article_url)
                    full_text = get_full_text(content=content)
                    main_text,referee,have_minor = get_main_text(content=content)
                    cause_text = get_cause(content=content)
                    if referee =='裁定':
                        continue
                    else: #判決才要寫入
                        print('寫入第',num,'筆資料中')
                        row = pd.DataFrame({
                            "num": num,
                            "page_num": page_num,
                            "url": article_url,
                            "referee":referee,
                            "have_minor":have_minor,
                            "name":name,
                            "cause_text":cause_text,
                            "main_text":main_text,
                            "full_text": full_text
                        }, index=[0])
                        print('row append __ok')
                        article_data = article_data.append(row, ignore_index=True)
                        time.sleep(random.uniform(0.5,3))
                        end_time = time.time()
                        logging.info(
                            f'page: {num}, url: {article_url}, Time consumption: {(end_time - start_time):.2f} seconds')
                        num += 1

                print('get next_page_url and assign to page_url')
                try:
                    next_page_qurl = page_content.find(
                        "a", {"class": "page", "id": "hlNext"}).get("href")
                    page_url = f'https://judgment.judicial.gov.tw{next_page_qurl} & ot = in'
                    
                    page_num += 1
                    logging.info(f'There are {len(article_data)} articles so far.')
                except AttributeError as e:
                        logging.error(f'error message: {e}. No next_page. Stop iterating')
                        break
            else:
                logging.error(f'if else message: page_num > page_limit')
                break

except AttributeError as e:
    logging.error(f'error message: {e}. No next_articles. Stop iterating')
    




project_dir = os.path.abspath(os.path.dirname(sys.argv[0]) or ".")
query_date = date.today().strftime("%Y%m%d")
file_prefix = 'ccClub2022fall'
data_path = '/Users/rubysun/PythonProj/2022fall.xlsx'


with pd.ExcelWriter(data_path) as writer:
        article_data.to_excel(writer, index=False, header=True, encoding="utf_8_sig", engine="xlsxwriter")


print('article_data.save')