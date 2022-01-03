# モジュールの読み込み
## HTMLクローラー関連
#import requests
import urllib
from bs4.element import nonwhitespace_re
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
    デバッグ時にはChromeの動作を目視確認するために、options.add_argument行をコメントアウトする。
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

## cookieおよび_ncformingoを取得する
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

# 空き状況を検索ページに移動する。
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

# 空き予約情報を取得する
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

# ログインする
@reserve_tools.elapsed_time
def login_proc(cfg, driver, headers, userid, password, logger=None):
    """
    ログインする
    """
    global http_req_num
    # 利用者番号とパスワードを設定する
    _userid = userid
    _password = password
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10)
    # クローラーの初期化
    ( driver, mouse ) = setup_driver(headers)
    # 空き予約ページにアクセスし、cookieを取得する
    ( cookies , response )= selenium_get_cookie(driver, cfg, logger=logger)
    # 利用者番号とパスワードを入力する
    # 利用者番号フィールドが表示されるまで待機する
    f_userid = wait.until(EC.presence_of_element_located((By.NAME, "no")))
    # 利用者番号フィールドに入力されている値をクリアする
    f_userid.clear()
    # 利用者番号フィールドに利用者番号を入力する
    f_userid.send_keys(str(_userid))
    # パスワードフィールドが表示されるまで待機する
    f_password = wait.until(EC.presence_of_element_located((By.NAME, "password")))
    # パスワードフィールドに入力されている値をクリアする
    f_password.clear()
    # パスワードフィールドに利用者番号を入力する
    f_password.send_keys(str(_userid))
    # パスワードフィールドにパスワードを入力する
    f_password.send_keys(str(_password))
    # 「ログイン」ボタンをクリックする
    driver.find_element_by_xpath('//*[@id="pageTop"]/article/section[2]/div/form[1]/table/tbody/tr[3]/td/input[4]').click()
    http_req_num += 1
    assert 'ご利用者さまトップ｜八王子市施設予約システム>' in driver.title
    return driver, mouse

# 現在の予約済み情報を取得する。予約数の上限がないので実装しない(TBD)
#@reserve_tools.elapsed_time
#def get_current_reserves_list():
#    """
#    現在の予約情報を取得する
#    """

# メニュー画面から「随時予約・抽選申込」を選択し、「空き状況を検索」画面移動する
@reserve_tools.elapsed_time
def go_to_datesearch(driver, mouse, cfg, logger=None):
    """
    メニュー画面から「随時予約・抽選申込」を選択し、「空き状況を検索」画面移動する
    """
    global http_req_num
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10)
    # 検索ページがすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    # メニューバーの「随時予約・抽選申込」をクリックする
    driver.find_element_by_xpath('/html/body/div[1]/article/section[2]/ul/li[1]/form/a').click()
    #//*[@id="pageTop"]/article/section[2]/ul/li[1]/form/a
    #/html/body/div[1]/article/section[2]/ul/li[1]/form/a
    http_req_num += 1
    return driver, mouse

# 空き状況を検索するため、検索条件を入力して、空きコートを表示する
@reserve_tools.elapsed_time
def display_target_reserve(driver, mouse, date, facility_id, court_id, logger=None):
    """
    年月日、分類、施設名、ご利用目的、開始日、指定開始日のみを指定して、対象の空きコートを表示する
    """
    global http_req_num
    # selectタイプの指定値
    shisetsuId = 2 # テニスコート
    # DOM上に表示されるまで待機する
    # 検索フォームのフィールド設定
    wait = WebDriverWait(driver, 10)
    f_shisetsu = wait.until(EC.presence_of_element_located((By.NAME, "class")))
    # 分類フィールドで施設を選択する
    f_shisetsu.clear()
    Select(f_shisetsu).select_by_value(shisetsuId)
    # 施設名フィールドで、「施設名」を選択する
    f_facility = wait.until(EC.presence_of_element_located((By.NAME, "facility_id")))
    f_facility.clear()
    Select(f_facility).select_by_value(facility_id)
    # 場所（面）フィールドで、「コート」を選択する
    f_place= wait.until(EC.presence_of_element_located((By.NAME, "field_group_id")))
    f_place.clear()
    Select(f_place).select_by_value(court_id)
    # 開始日フィールドが表示されるまで待機後、指定する
    f_date = wait.until(EC.presence_of_element_located((By.NAME, "date")))
    # 開始日フィールドに入力されている値をクリアする
    f_date.clear()
    # 開始日フィールドに指定日を入力する
    f_date.send_keys(str(date))
    # 期間ラジオボタンで「指定開始日のみ」を指定する
    f_period = driver.find_element_by_xpath('//*[@id="pageTop"]/article/section[2]/div/form/table/tbody/tr[4]/td/table/tbody/tr[2]/td/div/label[1]')
    # 期間ラジオボタンで「指定開始日のみ」をクリックする
    f_period.click()
    # 画面を最下行までスクロールさせ、全ページを表示する
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    # 検索ボタンをクリックする
    driver.find_element_by_xpath('//*[@id="pageTop"]/article/section[2]/div/form/table/tbody/tr[5]/td/input[2]').click()
    # 検索結果がすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    sleep(1)
    # 最下行までスクロールする
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    http_req_num += 1
    # 画面のtitleを確認する
    assert '空き状況を検索｜八王子市施設予約システム' in driver.title
    #return cookie, ncforminfo_value
    return driver, mouse

# 表示された空きコートの空き時間帯を選択し、予約登録画面に移動する
@reserve_tools.elapsed_time
def select_empty_court_and_time(driver, mouse, cfg, logger=None):
    """
    表示された空きコートを選択する
    """
    global http_req_num
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10)
    # 検索ページがすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    # 検索結果をHTMLソースとしてオブジェクトに保存する
    html = driver.page_source
    # 表示された空きコートの空き時間帯と空き状況カレンダーの空き時間帯の行数を取得する
    ( _time , _row_num) = get_empty_time_and_row_number(html, cfg, logger=None)
    # 空きコートの空き時間帯のリンクをクリックする
    _xpath=f'//*[@id="pageTop"]/article/section[3]/article/section[2]/div[2]/div/table/tbody/tr[{_row_num}]/td[2]/form/a'
    driver.find_element_by_xpath(f'_xpath').click()
    http_req_num += 1
    # 画面のtitleが予約登録画面であることを確認する
    assert '随時予約（確認）｜八王子市施設予約システム' in driver.title
    return driver, mouse

# 検索した空きコートの空き時間帯を取得し、希望時間帯であるかを確認する
@reserve_tools.elapsed_time
def get_empty_time_and_row_number(html, cfg, logger=None):
    """
    検索結果から空き時間帯を取得し、希望時間帯であるか確認する
    Returns:
        _time[string]: 空き時間帯
        _row_num[int]: 表の行数
        [type]: [description]
    """
    # 空き時間帯と表の行数
    soup = BeautifulSoup(html, features='html.parser')
    # 空き状況カレンダーのテーブルを取得する
    _table = soup.find('table', _class="calTable")
    _tbody = _table.tbody
    # 空き時間帯と表の行数を取得する
    _row_num = 0
    for _tr in _tbody.contents:
        _row_num += 1
        _time = _tr.contents[0].string
        _status = _tr.contents[1].string
        # 空き時間帯でないなら次の時間帯に移動する
        if str(_status) == '×':
            logger.debug(f'not empty time: {_time}')
            continue
        # 空き予約の時間帯が希望時間帯リストに含まれているか確認する
        if _time in cfg['want_hour_list']:
            # 希望時間帯リストに含まれている場合は終了する
            logger.debug(f'found emtpy time: {_time}')
            break
    # 空き時間帯と空き状況カレンダーの行数を返す
    return _time, _row_num

# 予約登録画面で利用目的を選択し、申込むボタンをクリックし、予約する
@reserve_tools.elapsed_time
def entry_reserve(driver, mouse, logger=None):
    """
    空きコートを申し込む
    """
    global http_req_num
    # 利用目的を「硬式テニス」とする
    # 硬式テニスの値
    _purpose = 150 
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10)
    # 検索ページがすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    # 利用目的を選択する
    f_purpose = driver.find_element_by_xpath('//*[@id="purpose"]')
    # 利用目的フィールドに
    f_purpose.select_by_value(_purpose)
    # 「申込」ボタンをクリックする
    driver.find_element_by_xpath('//*[@id="pageTop"]/article/section/form[1]/table/tbody/tr[7]/td/input[4]').click()
    http_req_num += 1
    # 随時予約（完了）画面であることを確認する
    assert '随時予約（完了）｜八王子市施設予約システム' in driver.title
    return driver, mouse

# 空き状況の検索ページへ戻る
@reserve_tools.elapsed_time
def return_to_datesearch(driver, mouse, cfg, logger=None):
    """
    「空き状況の検索へ」リンクをクリックして「空き状況を検索」画面移動する
    """
    global http_req_num
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10)
    # 検索ページがすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    # メニューバーの「随時予約・抽選申込」をクリックする
    driver.find_element_by_xpath('//*[@id="pageTop"]/article/section/form/nav/a').click()
    http_req_num += 1
    return driver, mouse

# メインルーチン
@reserve_tools.elapsed_time
def main_search_empty_reserves():
    """
    メインルーチン
    """
    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 空き予約リストの初期化
    #reserves_list = {}
    threadsafe_list = ThreadSafeReservesList()
    # 送信メッセージリストの初期化
    message_bodies = []
    # WEB request header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
    }

    # 処理の開始
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    reserve_tools.set_public_holiday('public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = reserve_tools.read_json_cfg('cfg2.json')
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
    logger.debug(json.dumps(threadsafe_list.reserves_list, indent=2, ensure_ascii=False))
    #exit()
    # LINEにメッセージを送信する
    ## メッセージ本体を作成する
    reserve_tools.create_message_body(threadsafe_list.reserves_list, message_bodies, cfg, logger=logger)
    ## LINEに空き予約情報を送信する
    reserve_tools.send_line_notify(message_bodies, cfg, logger=logger)
    #exit()
    return cfg, logger, threadsafe_list.reserves_list, target_months_list, public_holiday, headers

# 予約処理のメインルーチン
@reserve_tools.elapsed_time
def main_reserve_proc(cfg, logger, reserves_list, target_months_list, public_holiday, headers):
    """
    予約処理のメインルーチン
    """
    # 予約できた件数
    reserved_num = 0
    # 1回の最大予約件数
    max_reserved_num = cfg['reserved_limit_at_onetime']
    # 空き予約リストに値があるかないかを判断し、予約処理を開始する
    if len(reserves_list) == 0:
        logger.info(f'stop do reserve because no empty reserve.')
        return logger
    # 予約希望日リストを作成する
    want_date_list = reserve_tools.create_want_date_list(target_months_list, public_holiday, cfg, logger=logger)
    logger.debug(f'want_date_list: {want_date_list}')
    # 希望時間帯を取得する
    want_hour_list = cfg['want_hour_list']
    # 希望施設名を取得する
    want_location_list = cfg['want_location_list']
    # 予約処理対象の希望日、希望時間帯のリストを作成する
    # 空き予約リストを昇順にソートする
    sorted_reserves_list = reserve_tools.sort_reserves_list(reserves_list)
    # 空き予約リストから、空き予約日と時間帯を取得する
    target_reserves_list = reserve_tools.create_target_reserves_list_hachioji(sorted_reserves_list, want_date_list, want_hour_list, want_location_list, logger=logger)
    # 希望日+希望時間帯+希望コートのDictを出力する
    logger.info(f'target_reserves_list: {target_reserves_list}')
    # 希望日+希望時間帯のリストが空の場合は予約処理を中止する
    if bool(target_reserves_list) == False:
        logger.info(f'reserve process stopped. because empty reserves is not wanted.')
        return logger
    # menu_map.jsonを読み込み、Dictに保存する
    menu_map = reserve_tools.read_json_cfg('menu_map.json')
    # クローラーの初期化
    ( driver, mouse ) = setup_driver(headers)
    # 空き予約ページにアクセスし、cookieを取得する
    ( cookies , response )= selenium_get_cookie(driver, cfg)
    # 複数IDに対応する
    userauth = cfg['userauth']
    # タイプ毎のID:PASSリストを取得する
    for _type, _type_list in userauth.items():
        # 予約できた件数が1回の最大予約件数を超えていたら終了する
        if reserved_num >= max_reserved_num:
            logger.info(f'exceeded reserved number at onetime.')
            break
        # タイプ別のID:PASSリストが空の場合は次のタイプに移る
        if not bool(_type_list):
            logger.info(f'{_type} type users list is empty.')
            continue 
        # 利用者ID毎に予約処理を開始する
        ## IDとパスワードを取得する
        for _userid, _credential in _type_list.items():
            # 予約できた件数が1回の最大予約件数を超えていたら終了する
            if reserved_num >= max_reserved_num:
                logger.info(f'exceeded reserved number at onetime.')
                break
            _password = _credential['password']
            logger.info(f'UserID:{_userid}, PASS:{_password} is logined.')
            # ログインIDを使ってログインする
            ( driver, mouse ) = login_proc(cfg, driver, headers, _userid, _password, logger=None)
            # 予約処理を開始する
            # メニュー画面から「随時予約・抽選申込」を選択し、「空き状況を検索」画面移動する
            ( driver, mouse ) = go_to_datesearch(driver, mouse, cfg, logger=None)
            # 希望日+希望時間帯+希望コートのリストから検索条件を取得する
            for _date in target_reserves_list:
                for _time, _court_list in target_reserves_list[_date].items():
                    for _court in _court_list:
                        # 予約できた件数が1回の最大予約件数を超えていたら終了する
                        if reserved_num >= max_reserved_num:
                            logger.info(f'exceeded reserved number at onetime.')
                            break
                        _facility_name = _court.split(' ')[0]
                        _court_name = _court.split(' ')[1]
                        _facility_id = menu_map['facility_id'][_facility_name]
                        _court_id = menu__map['field_group_id'][_facility_name][_court_name]
                        logger.debug(f'input data for search: {_date} {_facility_id} {_court_id}')
                        # 空き状況を検索するため、検索条件を入力して、空きコートを表示する
                        ( driver, mouse ) = display_target_reserve(driver, mouse, cfg, _date, _facility_id, _court_id, logger=None)
                        # 表示された空きコートの空き時間帯を選択し、予約登録画面に移動する
                        ( driver, mouse ) = select_empty_court_and_time(driver, mouse, cfg, logger=None)
                        # 予約登録画面で利用目的を選択し、申込むボタンをクリックし、予約する
                        ( driver, mouse ) = entry_reserve(driver, mouse, logger=None)
                        logger.debug(f'registed reserve: {_date} {_time} {_court}')
                        reserved_num += 1
                        # 空き状況の検索ページへ戻る
                        ( driver, mouse ) = return_to_datesearch(driver, mouse, cfg, logger=None)
    return logger

if __name__ == '__main__':
    # 実行時間を測定する
    start = time.time()
    # 空き予約を検索する
    ( cfg, logger, reserves_list, target_months_list, public_holiday, headers) = main_search_empty_reserves()
    # 予約処理を実施する
    main_reserve_proc(cfg, logger, reserves_list, target_months_list, public_holiday, headers)
    # デバッグ用(HTTPリクエスト回数を表示する)
    logger.debug(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - start
    logger.debug(f'whole() duration time: {elapsed_time} sec')
    exit()

