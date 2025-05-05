# モジュールの読み込み
## HTMLクローラー関連
#import requests
import urllib
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import exceptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from time import sleep

# 並列処理モジュール(threading)
from concurrent.futures import (
    ThreadPoolExecutor,
    Future,
    as_completed,
    wait
)

# スレッドロック
import threading

## カレンダー関連
import math
import datetime
import calendar
import time

## ファイルIO、ディレクトリ関連
import os

## HTML解析関連
from bs4 import BeautifulSoup
import re

## JSON関連
import json

# ツールライブラリを読み込む
import reserve_tools

# HTTPリクエスト数
http_req_num = 0

# クローラー
## Selenium関連
def setup_driver(headers):
    """
    seleniumを初期化する
    デバッグ時にはChromeの動作を目視確認するために、options.add_argi,emt行をコメントアウトする。
    ヘッドレスモードを利用する場合は、options.add_argument行のコメントアウトを外す。
    """
    # Chromeを指定する
    options = webdriver.ChromeOptions()
    #options.binary_location = '/usr/bin/chromium-browser'
    options.binary_location = '/usr/lib64/chromium-browser/headless_shell'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument(f'--user-agent={headers["User-Agent"]}')
    #driver = webdriver.Chrome('/usr/lib/chromium-browser/chromedriver', options=options)
    driver = webdriver.Chrome('/usr/lib64/chromium-browser/chromedriver', options=options)
    #driver.set_window_size('800', '600')
    mouse = webdriver.ActionChains(driver)
    return driver , mouse

@reserve_tools.elapsed_time
def selenium_get_cookie(driver, cfg, logger=None):
    """
    selenuimuで接続する
    cookieおよび_ncforminfoの値を取得する
    トップページにアクセスし、これらを取得する
    """
    global http_req_num
    # トップページにアクセスする
    #first_url = cfg['first_url']
    response = driver.get(cfg['first_url'])
    http_req_num += 1
    sleep(1)
    cookies = driver.get_cookies()
    #logger.debug(f'{cookies}')
    #logger.debug(type(response))
    #logger.debug(dir(response))
    # 画面のtitleを確認する
    assert '施設の空き状況や予約ができる 八王子市施設予約システム' in driver.title
    return cookies , response

@reserve_tools.elapsed_time
def selenium_go_to_search_menu(driver, mouse, cfg, cookies, logger=None):
    """
    空き状況を検索ページに移動する。
    「空き状況を検索」ボタンをクリックする
    """
    global http_req_num
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10)
    # 検索ページがすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    # 空き状況を検索 画面に移動するため、右上の「空き状況を検索」ボタンをクリックする
    #disp_search = driver.find_element_by_xpath('/html/body/div[1]/header/section/div/form/p/a').click().perform()
    driver.find_element_by_xpath('/html/body/div[1]/header/section/div/form/p/a').click()
    http_req_num += 1
    return None

@reserve_tools.elapsed_time
def selenium_post_conditions(driver, date_list, reserves_list, cfg, logger=None):
    """
    取得したcookieを設定して、空き予約情報を取得する
    """
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10)
    # 検索ページがすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    #sleep(5)
    #for key, value in input_data_list.item():
    # 検索日を指定して、空き予約を取得する
    for _date in date_list:
        #logger.debug(f'research: {key}: {value}')
        f_date = _date.replace('/', '')
        # 空き予約を検索する
        selenium_input_datas(driver, _date, logger=logger)
        # 検索結果をHTMLソースとしてオブジェクトに保存する
        _html = driver.page_source
        # デバッグ用にHTMLファイルを保存する
        #reserve_tools.save_result_html(_html, f'hachioji_empty_reserves_{f_date}.html')
        #sleep(1)
        # HTML解析を実行し、空き予約名リストを作成する
        #get_empty_court_time(cfg, reserves_list, _date, _html)
        get_empty_court_time(cfg, reserves_list, f_date, _html, logger=logger)
        # 条件をクリア ボタンをクリックして、次の検索の準備をする

    # 空き予約名リストを表示する
    #logger.debug(f'Court_Reserve_List:\n{reserves_list}')
    return reserves_list


# 検索ページに検索条件を入力して、検索を結果を取得する
@reserve_tools.elapsed_time
def selenium_input_datas(driver, input_date, logger=None):
    """
    検索条件を入力し、空き予約を検索し、検索結果を取得する
    """
    global http_req_num
    # selectタイプの指定値
    shisetsuId = 2 # テニスコート
    periodId = 1 # 指定日のみ
    # DOM上に表示されるまで待機する
    # 検索フォームのフィールド設定
    wait = WebDriverWait(driver, 10)
    f_shisetsu = wait.until(EC.presence_of_element_located((By.ID, "shisetsu")))
    # 分類フィールドで施設を選択する
    Select(f_shisetsu).select_by_index(shisetsuId)
    # 開始日フィールドが表示されるまで待機後、指定する
    f_date = wait.until(EC.presence_of_element_located((By.NAME, "date")))
    # 開始日フィールドに入力されている値をクリアする
    f_date.clear()
    # 開始日フィールドに指定日を入力する
    f_date.send_keys(str(input_date))
    # 期間ラジオボタンで指定開始日のみを選択する
    # クリックできる状態まで待機する
    #wait.until(EC.element_to_be_clickable((By.NAME, "disp_type")))
    #wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "btnSearch js_recaptcha_submit")))
    # 期間ラジオボタンで「指定開始日のみ」を指定する
    f_period = driver.find_element_by_xpath("/html/body/div[1]/article/section[2]/div/form/table/tbody/tr[4]/td/table/tbody/tr[2]/td/div/label[1]")
    # 期間ラジオボタンで「指定開始日のみ」をクリックする
    f_period.click()
    # 画面を最下行までスクロールさせ、全ページを表示する
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    # 検索ボタンをクリックする
    driver.find_element_by_xpath(".//input[@type='button'][@value='検索する'][@class='btnSearch js_recaptcha_submit']").click()
    #sleep(30)
    # 検索結果がすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    sleep(1)
    # 最下行までスクロールする
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    http_req_num += 1
    # 画面のtitleを確認する
    assert '空き状況を検索｜八王子市施設予約システム' in driver.title
    #return cookie, ncforminfo_value
    return None

# 指定した年月日のコート空き予約ページから空き予約の時間帯を取得する
@reserve_tools.elapsed_time
#def get_empty_court_time(cfg, reserves_list, date, html):
def get_empty_court_time(cfg, threadsafe_list, date, html, logger=None):
    """
    空き予約日のコート番号と時間帯を取得する
    """
    # 検索結果のHTMLオブジェクトを入力とする
    soup = BeautifulSoup(html, features='html.parser')
    # 空き予約があるフォームタグを取得する
    _form = soup.find_all('form', method="post", action=re.compile("/reserve/register"))
    # formタグから空き予約の時間帯やコート名をさかのぼって取得する
    for _tag in _form:
        # 登録フラグを初期化する。0なら登録対象とする
        _regist_flag = 0
        # 空き予約の時間帯を取得する
        _time = _tag.parent.previous_sibling.string
        #logger.debug(f'time: {_time}')
        # 空き予約のコート名を取得する
        _court = _tag.find_parent("section").find("h4").contents[1]
        #logger.debug(f'court: {_court}')
        # 空き予約の時間帯とコートの両方が除外リストに含まれていない場合のみ空き予約リストに登録する
        # 除外時間帯か確認する
        #_exclude_time_count = len(cfg['exclude_times'])
        for _exclude_time in cfg['exclude_times']:
            if _time == _exclude_time:
                #logger.debug(f'matched exclude time: {_court} {_time}')
                _regist_flag = 1
                break
        # 除外コートか確認する
        #_exclude_court_count = len(cfg['exclude_courts'])
        for _exclude_court in cfg['exclude_courts']:
            # 除外コートの文字列が含まれているか確認する
            if _exclude_court in _court:
                #logger.debug(f'matched exclude court: {_court} {_time}')
                _regist_flag = 1
                break
        # 空き予約リストに登録する
        # 空き予約リストに発見した日がない場合はその日をキーとして登録する
        if _regist_flag == 0:
            #if f'{date}' not in threadsafe_list.reserves_list:
                #reserves_list[f'{date}'] = {}
                #reserves_list[f'{date}'].setdefault(_time, []).append(_court)
                # スレッドセーフな空き予約リストに追加する
            threadsafe_list.add_reserves(date, _time, _court, logger=logger)
    #logger.debug(json.dumps(threadsafe_list.reserves_list, indent=2, ensure_ascii=False))
    return None

# スレッド数に応じて、検索対象年月日を分割する
def split_date_list(date_list, threads_num=1, logger=None):
    """
    スレッド数に応じて、検索対象年月日を分割する
    """
    # スレッド数に応じて、検索対象年月日を格納するリストを初期化する
    # [ [], [], [] , ... ]のリストになる
    date_list_threads = []
    for _empty_list in range(threads_num):
        date_list_threads.append([])
    #logger.debug(f'date_list_threads: {date_list_threads}')
    # date_list_threads のインデックスを初期化する
    _th_index = 0
    # 分割する
    for _date in date_list:
        _index = int(_th_index) % int(threads_num)
        date_list_threads[_index].append(_date)
        _th_index += 1
    #logger.info(f'date_list_threads: {date_list_threads}')
    return date_list_threads

# webdriver初期化から空き予約検索、webdriver終了の一連の動作をする
@reserve_tools.elapsed_time
def date_search(cfg, headers, date_list, threadsafe_list, logger=None):
    """
    webdriverを初期化する
    cookieを取得する
    空き情報を検索するページに移動する
    条件を指定して空き予約を取得する
    排他制御で空き予約リストにレコードを登録する
    webdriverを終了する
    """
    # クローラーの初期化
    ( driver, mouse ) = setup_driver(headers)
    # 空き予約ページにアクセスし、cookieを取得する
    ( cookies , response )= selenium_get_cookie(driver, cfg, logger=logger)
    # 空き状況を検索するページに移動する
    selenium_go_to_search_menu(driver, mouse, cfg, cookies, logger=logger)
    # 条件を指定して、空き予約を取得する
    threadsafe_list = selenium_post_conditions(driver, date_list, threadsafe_list, cfg, logger=logger)
    driver.quit()
    return threadsafe_list

# マルチスレッドで、空き予約を検索する
@reserve_tools.elapsed_time
def multi_thread_datesearch(cfg, headers, date_list_threads, threadsafe_list, threads_num=1, logger=None):
    """
    マルチスレッドで次のことを実施する
    webdriverを初期化する
    cookieを取得する
    空き情報を検索するページに移動する
    条件を指定して空き予約を取得する
    排他制御で空き予約リストにレコードを登録する
    webdriverを終了する
    """
    # 実行結果を入れるオブジェクトの初期化
    futures = []
    #logger.debug(f'スレッド数: {threads}')
    with ThreadPoolExecutor(max_workers=threads_num) as executor:
        #_index = 0
        for date_list in date_list_threads:
            # スレッド数に応じて分割した検索対象年月日リストを受け取って、検索する
            future = executor.submit(date_search, cfg, headers, date_list, threadsafe_list, logger=logger)
            futures.append(future)
        for future in as_completed(futures):
            future.result()
        return threadsafe_list

# スレッドセーフな空き予約リスト
class ThreadSafeReservesList:
    lock = threading.Lock()
    def __init__(self):
        self.reserves_list = {}
    def add_reserves(self, _date, _time, _locate_court, logger=None):
        with self.lock:
            # 空き予約リストに追加する
            # 空き予約リストに発見した日がなければ、年月日をキーとして初期化する
            if _date not in self.reserves_list:
                self.reserves_list[_date] = {}
                self.reserves_list[_date].setdefault(_time, []).append(_locate_court)
            # 空き予約リストに発見した日が登録されていた場合
            else:
                # 空き予約リストに発見した時間帯がなければ、時間をキーとしてリストを初期化する
                if _time not in self.reserves_list[_date]:
                    self.reserves_list[_date][_time] = []
                self.reserves_list[_date][_time].append(_locate_court)
            #logger.debug(f'{self.reserves_list}')

# メインルーチン
def main():
    """
    メインルーチン
    """
    # 空き予約リストの初期化
    threadsafe_list = ThreadSafeReservesList()
    # 送信メッセージリストの初期化
    message_bodies = []
    # WEB request header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko Chrome/85.0.4183.83 Safari/537.36'
    }

    # 処理の開始
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    public_holiday = reserve_tools.set_public_holiday('public_holiday.json')
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = reserve_tools.read_json_cfg('cfg.json')
    # ロギングを設定する
    logger = reserve_tools.mylogger(cfg)
    # スレッド数を設定する
    threads_num = cfg['threads_num']
    # 検索リストを作成する
    target_months_list = reserve_tools.create_month_list(cfg, logger=logger)
    logger.debug(f'target months: {target_months_list}')
    date_list = reserve_tools.create_date_list_hachioji(target_months_list, public_holiday, cfg, logger=logger)
    logger.debug(f'date list: {date_list}')
    # スレッド数に応じて、date_listを分割する
    date_list_threads = split_date_list(date_list, threads_num, logger=logger)
    logger.debug(f'splited date list: {date_list_threads}')
    #return logger

    # マルチスレッド化する
    ##  ここから
    # クローラーの初期化
    #( driver, mouse ) = setup_driver(headers)
    # 空き予約ページにアクセスし、cookieを取得する
    #( cookies , response )= get_cookie(cfg)
    #( cookies , response )= selenium_get_cookie(driver, cfg)
    # 空き状況を検索するページに移動する
    #selenium_go_to_search_menu(driver, mouse, cfg, cookies)
    # 条件を指定して、空き予約を取得する
    #reserves_list = selenium_post_conditions(driver, date_list, reserves_list, cfg)
    #logger.debug(type(reserves_list))
    #logger.debug(dir(reserves_list))
    # seleniumを終了する
    #driver.quit()
    ## ここまで
    # マルチスレッドで呼び出す
    threadsafe_list = multi_thread_datesearch(cfg, headers, date_list_threads, threadsafe_list, threads_num=threads_num, logger=logger)

    logger.info(json.dumps(threadsafe_list.reserves_list, indent=2, ensure_ascii=False))
    #exit()
    # LINEにメッセージを送信する
    ## メッセージ本体を作成する
    reserve_tools.create_message_body(threadsafe_list.reserves_list, message_bodies, cfg, logger=logger)
    ## LINEに空き予約情報を送信する
    reserve_tools.send_line_notify(message_bodies, cfg, logger=logger)
    #exit()
    return logger
    
if __name__ == '__main__':
    # 実行時間を測定する
    start = time.time()
    logger = main()
    # デバッグ用(HTTPリクエスト回数を表示する)
    logger.debug(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - start
    logger.debug(f'whole() duration time: {elapsed_time} sec')
    exit()

