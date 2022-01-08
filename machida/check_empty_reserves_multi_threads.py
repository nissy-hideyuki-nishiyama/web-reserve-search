# モジュールの読み込み
## HTMLクローラー関連
from requests.exceptions import (
    Timeout,
    RequestException,
    ConnectionError,
    HTTPError,
    URLRequired,
    TooManyRedirects
)
import requests
import urllib
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import exceptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome import service as fs

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
from time import sleep
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
import pprint

# URLの'/'が問題になるためハッシュ化する
from hashlib import md5
from pathlib import Path

# ツールライブラリを読み込む
from reserve_tools import reserve_tools

http_req_num = 0

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

# クローラー
## Selenium関連
def setup_driver():
    """
    seleniumを初期化する
    デバッグ時にはChromeの動作を目視確認するために、options.add_argument行をコメントアウトする。
    ヘッドレスモードを利用する場合は、options.add_argument行のコメントアウトを外す。
    """
    # WEB request header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
    }
    # Chromeを指定する
    chromedriver_location = '/usr/lib64/chromium-browser/chromedriver'
    chrome_service = fs.Service(executable_path=chromedriver_location)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument(f'--user-agent={headers["User-Agent"]}')
    options.binary_location = '/usr/lib64/chromium-browser/headless_shell'
    # GUIによるデバッグ用。GUIでデバックする場合はこちらを選択する
    #options.binary_location = '/usr/bin/chromium-browser'
    driver = webdriver.Chrome(service=chrome_service, options=options)
    #driver.set_window_size('800', '600')
    mouse = webdriver.ActionChains(driver)
    return driver , mouse

## cookieおよび_ncformingoを取得する
@reserve_tools.elapsed_time
def selenium_get_cookie_and_html(driver, cfg, logger=None):
    """
    selenuimuで接続する
    cookieおよび_ncforminfoの値を取得する
    トップページにアクセスし、これらを取得する
    """
    global http_req_num
    wait = WebDriverWait(driver, 10, 2)
    # トップページにアクセスする
    response = driver.get(cfg['top_url'])
    http_req_num += 1
    cookies = driver.get_cookies()
    # logger.debug(f'Top cookies:')
    # logger.debug((json.dumps(cookies, indent=2)))
    sleep(1)
    # メニューページにアクセスする
    response = driver.get(cfg['first_url'])
    cookies = driver.get_cookies()
    # logger.debug(f'First URL cookies:')
    # logger.debug((json.dumps(cookies, indent=2)))
    http_req_num += 1
    sleep(1)
    #cookies = driver.get_cookies()
    # デバック用
    _html = driver.page_source
    with open('dselect.html', mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(_html)
    # 空き予約検索ページにアクセスする
    response = driver.get(cfg['second_url'])
    http_req_num += 1
    cookies = driver.get_cookies()
    # デバック用
    _html = driver.page_source
    with open('Wp_TopMenu.html', mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(_html)
    # logger.debug(f'Wp_TopMenu cookies:')
    # logger.debug((json.dumps(cookies, indent=2)))
    # 「空き照会」ボタンが表示されるまで待機する
    #elment = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id="wpManager_gwppnlLeftZone_btnShoukai"]")))
    elment = wait.until(EC.presence_of_all_elements_located)
    # 画面のtitleを確認する
    #assert '施設の空き状況や予約ができる 八王子市施設予約システム' in driver.title
    return driver

# トップページから空き予約検索ページに接続し、cookieとフォームデータのためのHTMLファイルを取得する
@reserve_tools.elapsed_time
def connect_to_top_and_menu(cfg, logger=None):
    """
    トップページから空き予約検索ページに接続し、cookieとフォームデータのためのHTMLファイルを取得する
    JavaScript未対応のブラウザの場合はワーニングページに飛ばされるため、WEBブラウザを使う
    Args:
        cfg ([type]): [description]
        logger ([type], optional): [description]. Defaults to None.
    Returns:
        [type]: [description]
    """
    global http_req_num
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
    } 
    # クローラーの初期化
    ( driver, mouse ) = setup_driver()
    # トップページから空き予約検索ページに接続し、cookieとフォームデータのためのHTMLファイルを取得する
    ( driver )= selenium_get_cookie_and_html(driver, cfg, logger=logger)
    return driver

# 条件を指定して、空き予約を検索し、空き予約を取得する
@reserve_tools.elapsed_time
def selenium_post_conditions(driver, date_list, reserves_list, cfg, logger=None):
    """
    空き予約情報を取得する
    """
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10, 2)
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
        get_empty_court_time(cfg, reserves_list, f_date, _html, logger=logger)
        # 「メニューへ」ボタンをクリックする
        # 「クリアー」ボタンを押して、検索条件をクリアーする
        go_to_search_reserves_page(driver, logger=logger)
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
    SSDaiClass = '01' # スポーツ施設
    SSClass = '06' # テニスコート
    Term = '1日'
    Time = '全日'
    # DOM上に表示されるまで待機する
    # 検索フォームのフィールド設定
    wait = WebDriverWait(driver, 10, 2)
    # 施設の分類
    f_SSDaiClass = wait.until(EC.presence_of_element_located((By.ID, "wpManager_gwppnlLeftZone_cmbSSDaiClass")))
    Select(f_SSDaiClass).select_by_value(f'{SSDaiClass}')
    # 施設の種類
    f_SSClass = wait.until(EC.presence_of_element_located((By.ID, "wpManager_gwppnlLeftZone_cmbSSClass")))
    Select(f_SSClass).select_by_value(f'{SSClass}')
    # 開始日
    f_Date = wait.until(EC.presence_of_element_located((By.ID, "wpManager_gwppnlLeftZone_ucTermSettings_txtDateFrom")))
    # 開始日フィールドに入力されている値をクリアする
    f_Date.clear()
    # 開始日フィールドに指定日を入力する
    f_Date.send_keys(str(input_date))
    # 期間
    f_Term = wait.until(EC.presence_of_element_located((By.ID, "wpManager_gwppnlLeftZone_ucTermSettings_cmbTerm")))
    Select(f_Term).select_by_value(f'{Term}')
    # 時間帯
    f_Time = wait.until(EC.presence_of_element_located((By.ID, "wpManager_gwppnlLeftZone_ucTermSettings_cmbTime")))
    Select(f_Term).select_by_value(f'{Time}')
    f_shisetsu = wait.until(EC.presence_of_element_located((By.ID, "shisetsu")))
    # 画面を最下行までスクロールさせ、全ページを表示する
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    # 「空き照会>>」ボタンをクリックする
    driver.find_element(By.XPATH, ".//input[@type='button'][@value='検索する'][@class='btnSearch js_recaptcha_submit']").click()
    #sleep(30)
    # 検索結果がすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    sleep(1)
    # 最下行までスクロールする
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    http_req_num += 1
    # 画面のtitleを確認する
    #assert '空き状況を検索｜八王子市施設予約システム' in driver.title
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

# メニューボタンで空き予約検索ページに戻る
def go_to_search_reserves_page(driver, logger=None):
    """[summary]

    Args:
        driver ([type]): [description]
        logger ([type], optional): [description]. Defaults to logger.

    Returns:
        [type]: [description]
    """
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10, 2)
    # 検索ページがすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    # 「メニューへ」ボタンをクリックする
    f_MenuBtn = wait.until(EC.element_to_be_clickable((By.ID, "ucPCFooter_btnToMenu")))
    f_MenuBtn.click()
    # 空き予約検索ページに移動する
    sleep(1)
    # 「クリアー」ボタンを押して、検索条件をクリアーする
    f_ClearBtn = wait.until(EC.element_to_be_clickable((By.ID, "wpManager_gwppnlLeftZone_btnClear")))
    f_ClearBtn.click()
    # 
    return driver

# webdriver初期化から空き予約検索、webdriver終了の一連の動作をする
@reserve_tools.elapsed_time
def date_search(cfg, date_list, threadsafe_list, logger=None):
    """
    トップページ、メニューページに接続し、検索に必要なcookieなどを取得する
    空き情報を検索するページに移動する
    条件を指定して空き予約を取得する
    排他制御で空き予約リストにレコードを登録する
    webdriverを終了する
    """
    # トップページ、メニューページに接続し、検索に必要なcookieなどを取得する
    ( driver )= connect_to_top_and_menu(cfg, logger=logger)
    # 条件を指定して、空き予約を検索し、空き予約を取得する
    threadsafe_list = selenium_post_conditions(driver, date_list, threadsafe_list, cfg, logger=logger)
    driver.quit()
    return threadsafe_list

# マルチスレッドで、空き予約を検索する
@reserve_tools.elapsed_time
def multi_thread_datesearch(cfg, date_list_threads, threadsafe_list, threads_num=1, logger=None):
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
            future = executor.submit(date_search, cfg, date_list, threadsafe_list, logger=logger)
            futures.append(future)
        for future in as_completed(futures):
            future.result()
        return threadsafe_list

# 空き予約の検索処理の事前準備
@reserve_tools.elapsed_time
def prepare_serch_empty_reserves(cfg_filename="cfg.json"):
    """
    初期化処理
    - 設定ファイル、祝日ファイルの読み込み
    - ロギング設定
    検索対象日の生成
    """
    # 初期化処理
    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    reserve_tools.set_public_holiday('public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    #cfg = reserve_tools.read_json_cfg('cfg.json')
    cfg = reserve_tools.read_json_cfg(cfg_filename)
    # ロギングを設定する
    logger = reserve_tools.mylogger(cfg)
    # 検索対象日の生成
    ## 検索対象月を取得する
    target_months_list = reserve_tools.create_month_list(cfg, logger=logger)
    ## 検索対象月リストと祝日リストから検索対象年月日リストを作成する
    date_list = reserve_tools.create_want_date_list(target_months_list, public_holiday, cfg)
    logger.debug(f'date_list: {date_list}')
    # (予約処理を追加した場合に追加する)予約希望日リストを作成する
    #want_date_list = reserve_tools.create_want_date_list(target_months_list, public_holiday, cfg, logger=logger)
    #logger.debug(f'want_date_list: {want_date_list}')
    return cfg, logger, date_list

# 空き予約の検索処理のメイン
@reserve_tools.elapsed_time
def main_search_empty_reserves(cfg, date_list, threads_num=1, logger=None):
    """
    初期化処理
    """
    # 初期化処理(主に非同期並列処理のための変数の作成)
    # HTTPリクエスト数
    global http_req_num
    # 空き予約リストの初期化
    threadsafe_list = ThreadSafeReservesList()
    # 実行時間を測定する
    start = time.time()
    # 検索対象日をスレッド数に応じたリストに分割する
    split_date_lists = reserve_tools.split_date_list_by_threads(cfg, date_list, logger=logger)
    #request_objs = create_request_objs(cfg, date_list, cookies, form_datas, logger=logger)
    #return None
    #( cookies, shtml )= connect_to_get_cookies_and_html(cfg, logger=logger)
    # フォームデータを作成する
    #( form_data ) = create_form_data(cfg, shtml, logger=logger)
    # 空き予約検索を実行する
    #( reserves ) =  get_empty_reserves_html_by_chrome(cfg, cookies, form_data, logger=logger)
    
    # マルチスレッドで呼び出す
    threadsafe_list = multi_thread_datesearch(cfg, split_date_lists, threadsafe_list, threads_num=threads_num, logger=logger)
    logger.debug(json.dumps(threadsafe_list.reserves_list, indent=2, ensure_ascii=False))
    
    # 実行時間を表示する
    elapsed_time = time.time() - start
    logger.info(f'main_search_empty_reserves() duration time: {elapsed_time} sec')
    
    return None

# 空き予約の検索処理の事後処理
@reserve_tools.elapsed_time
def postproc_search_empty_reserves():
    """
    
    """
    # (選択２)空き予約検索結果ページの解析と空き予約結果リストへの登録
    # 空き予約結果リストを昇順にソートする
    # 空き予約結果リストの通知メッセージ文の作成
    # 空き予約結果リストのLINE通知

if __name__ == '__main__':
    # 実行時間を測定する
    _start = time.time()
    # 事前準備
    ( cfg, logger, date_list ) = prepare_serch_empty_reserves(cfg_filename="cfg.json")
    logger.info(f'starting to search empty reserve.')
    # 同時実行数
    threads = cfg['threads_num']
    # 検索対象年月日を指定して、空き年月日のHTMLボディを取得する
    results = main_search_empty_reserves(cfg, date_list, threads_num=threads, logger=logger)
    # 空き検索処理の事後処理
    #postproc_search_empty_reserves(logger=logger)
    # デバッグ用(HTTPリクエスト回数を表示する)
    logger.info(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - _start
    logger.info(f'whole() duration time: {elapsed_time} sec')
    
    exit()
