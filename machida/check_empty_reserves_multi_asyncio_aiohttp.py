# モジュールの読み込み
## HTMLクローラー関連
from asyncio.locks import Semaphore
from aiohttp.client import request
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

import asyncio
import aiohttp
import async_timeout
from aiohttp import ClientError

# URLの'/'が問題になるためハッシュ化する
from hashlib import md5
from pathlib import Path

# ツールライブラリを読み込む
from reserve_tools import reserve_tools

http_req_num = 0

## 空き予約時間帯を検索する空き予約リストへの登録を排他制御する
class AsyncioLockReservesList:
    """
    スレッド処理に対応するため、排他制御で空きコート時間リストの登録を行う
    """
    lock = asyncio.Lock()
    def __init__(self):
        self.reserves_list = {}
    async def add_url(self, day, time, court_name):
        async with self.lock:
            await self.reserves_list[f'{day}'].setdefault(time, []).append(court_name)

# コートの空き予約を検索するためのリクエストオブジェクトのリストを作成する
#@reserve_tools.elapsed_time
def create_request_objs(cfg, date_list, cookies, form_datas, logger=None):
    """
    指定年月日のリストを引数として、その指定年月日の空き予約を検索するために、
    リクエストオブジェクトのリストを作成する
    """
    # cookies, form_datas のリストから同時実行数に応じたcookieとform_dataを取得するためのindexを定義する
    index = 0
    # 同時実行数を取得する
    threads = cfg['threads_num']
    # リクエストパラメータのリストを初期化する
    request_objs = []
    logger.debug(f'call get_empty_reserves start: ##############')
    # リファレンスヘッダーを定義する。これがないと検索できない
    #headers_day = { 'Referer': cfg['day_search_url'] }    # 今日の年月日を取得する
    ## タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    # 希望曜日リストを作成する
    _now = datetime.datetime.now(JST)
    _today = str(_now.year) + str(_now.month).zfill(2) + str(_now.day).zfill(2)
    for _day in date_list:
        # 奈良原公園とそれ以外で検索する
        for param_string in cfg['search_params']:
            #print(f'task {_day}:{param_string} start: -----------')
            # パラメータ文字列の日付部分を置換する
            _param = re.sub('_SEARCHPARAM_', param_string, param_day_string)
            _param = re.sub('_TODAYSTRING_', _today, _param)
            _param = re.sub('_DATESTRING_', _day, _param)
            # URLを生成する
            search_url =  cfg['day_search_url'] + _param
            #print(search_url)
            # デバッグ用ファイル名として保存するエンティティ名を生成する
            name = md5(search_url.encode('utf-8')).hexdigest()
            _entity = f'{_day}_{name}'
            # cookie と form_data を取り出す
            _index = index % threads
            cookie = cookies[_index]
            form_data = form_datas[_index]
            # リクエストパラメータを追加する
            request_objs.append([_day, _entity, search_url, headers_day, cookie, form_data])
            index += 1
    #print(json.dumps(request_objs, indent=2))
    return request_objs

# クローラー
## Selenium関連
def setup_driver(headers):
    """
    seleniumを初期化する
    デバッグ時にはChromeの動作を目視確認するために、options.add_argument行をコメントアウトする。
    ヘッドレスモードを利用する場合は、options.add_argument行のコメントアウトを外す。
    """
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
    logger.debug(f'Top cookies:')    
    logger.debug((json.dumps(cookies, indent=2)))
    sleep(1)
    response = driver.get(cfg['first_url'])
    cookies = driver.get_cookies()
    logger.debug(f'First URL cookies:')    
    logger.debug((json.dumps(cookies, indent=2)))
    http_req_num += 1
    sleep(1)
    #cookies = driver.get_cookies()
    # デバック用
    _html = driver.page_source
    with open('dselect.html', mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(_html)
    # 空き検索ページにアクセスする
    response = driver.get(cfg['second_url'])
    http_req_num += 1
    cookies = driver.get_cookies()
    # デバック用
    _html = driver.page_source
    with open('Wp_TopMenu.html', mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(_html)
    logger.debug(f'Wp_TopMenu cookies:')
    #logger.debug(f'{cookies}')
    logger.debug((json.dumps(cookies, indent=2)))
    # 「空き照会」ボタンが表示されるまで待機する
    #elment = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id="wpManager_gwppnlLeftZone_btnShoukai"]")))
    elment = wait.until(EC.presence_of_all_elements_located)
    # 画面のtitleを確認する
    #assert '施設の空き状況や予約ができる 八王子市施設予約システム' in driver.title
    return cookies , _html

# トップページから空き予約検索ページに接続し、cookieとフォームデータのためのHTMLファイルを取得する
@reserve_tools.elapsed_time
def connect_to_get_cookies_and_html(cfg, logger=None):
    """
    トップページに接続し、cookieを取得する
    JavaScript未対応のブラウザの場合はワーニングページに飛ばされるため、WEBブラウザを使う
    Args:
        cfg ([type]): [description]
        logger ([type], optional): [description]. Defaults to None.

    Returns:
        [type]: [description]
    """
    global http_req_num
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
    } 
    # クローラーの初期化
    ( driver, mouse ) = setup_driver(headers)
    # 空き予約ページにアクセスし、cookieとフォームデータを取得する
    ( cookies , html )= selenium_get_cookie_and_html(driver, cfg, logger=logger)
    # 空き状況を検索するページに移動する
    #selenium_go_to_search_menu(driver, mouse, cfg, cookies, logger=logger)
    
    # session = requests.session()
    # response = session.get(cfg['first_url'], headers=headers)
    # # 文字コードが正しく設定されていない(shft_jisがISO-8859-1となっている)ので、下記の行を追加する
    # logger.debug(f'response_encoding: {response.encoding}')
    # response.encoding = response.apparent_encoding
    # http_req_num += 1
    # # デバッグ用
    # html = reserve_tools.save_html_to_filename(response, 'dselect.html')
    # # トップページではcookieを発行していなかった
    # #cookies = session.cookies
    # #logger.debug((json.dumps(cookies, indent=2)))
    # # 空き検索ページに接続し、cookieとPOSTリクエストのためのフォームデータを取得する
    # response = session.get(cfg['second_url'])
    # # 文字コードが正しく設定されていない(shft_jisがISO-8859-1となっている)ので、下記の行を追加する
    # response.encoding = response.apparent_encoding
    # http_req_num += 1
    # # デバッグ用
    # html = reserve_tools.save_html_to_filename(response, 'Wp_TopMenu.html')
    # cookies = session.cookies
    # logger.debug(f'Wp_TopMenu cookies:')
    # #logger.debug((json.dumps(cookies, indent=2)))
    # print(f'{cookies}')
    return cookies, html

# フォームデータを作成する
def create_form_data(cfg, html, logger=None):
    """[summary]
    空き予約検索ページのHTMLファイルからPOSTリクエストに使うフォームデータを生成する
    Args:
        cfg ([Dict]): 設定ファイルを読み込んだオブジェクト
        logger ([Object], optional): ロギングオブジェクト. Defaults to None.

    Returns:
        form_data [Dict]: POSTリクエストで使うフォームデータのオブジェクト。ベースとなる部分のみ生成する
    """
    # 初期化
    _form_data = {}
    soup =BeautifulSoup(html, "html.parser")
    _input_list = soup.find_all('input', type='hidden')
    #pprint.pprint(_input_list, indent=2)
    #exit()
    for _input in _input_list:
        _id = _input['id']
        _value = _input['value']
        _form_data[_id] = _value
    # 空き予約検索ページにおいて、利用者が入力するデータを追加する
    # カテゴリーから探す: 選択なし
    _form_data['wpManager$gwppnlLeftZone$cmbCategory'] = '-1'
    # 施設の分類: スポーツ施設
    _form_data['wpManager$gwppnlLeftZone$cmbSSDaiClass'] = '01'
    # 施設の種類: テニスコート
    _form_data['wpManager$gwppnlLeftZone$cmbSSClass'] = '06'
    # 使用目的分類: 選択なし
    _form_data['wpManager$gwppnlLeftZone$cmbPpsBunrui'] = '-1'
    # 付帯設備: 選択なし
    #_form_data[''] = ''
    # 施設名称から探す: 未記入
    _form_data['wpManager$gwppnlLeftZone$txtSSNameSearch'] = ''
    # 施設を選択する
    ## 町田中央公園テニスコート
    _form_data['wpManager$gwppnlLeftZone$dgSSSelect$ctl04$cbSSSelect'] = 'on'
    ## 鶴川中央公園テニスコート
    _form_data['wpManager$gwppnlLeftZone$dgSSSelect$ctl05$cbSSSelect'] = 'on'
    ## 鶴川第２中央公園テニスコート
    _form_data['wpManager$gwppnlLeftZone$dgSSSelect$ctl06$cbSSSelect'] = 'on'
    ## 鶴間公園テニスコート
    _form_data['wpManager$gwppnlLeftZone$dgSSSelect$ctl07$cbSSSelect'] = 'on'
    ## 野津田公園テニスコート
    _form_data['wpManager$gwppnlLeftZone$dgSSSelect$ctl08$cbSSSelect'] = 'on'
    ## 成瀬クリーンセンター
    _form_data['wpManager$gwppnlLeftZone$dgSSSelect$ctl09$cbSSSelect'] = 'on'
    ## 相原中央テニスコート
    _form_data['wpManager$gwppnlLeftZone$dgSSSelect$ctl10$cbSSSelect'] = 'on'
    # 開始日
    _form_data['wpManager$gwppnlLeftZone$ucTermSettings$txtDateFrom'] = ''
    # 期間
    _form_data['wpManager$gwppnlLeftZone$ucTermSettings$cmbTerm'] = '1日'
    # 時間帯
    _form_data['wpManager$gwppnlLeftZone$ucTermSettings$cmbTime'] = '全日'
    # 曜日
    #_form_data[''] = ''
    # 開始時間
    #_form_data['wpManager$gwppnlLeftZone$ucTermSettings$txtTimeFrom'] = ''
    # 終了時間
    #_form_data['wpManager$gwppnlLeftZone$ucTermSettings$txtTimeTo'] = ''
    # 利用者ID
    _form_data['wpManager$gwppnlMyMenu$txtID'] = ''
    # パスワード
    _form_data['wpManager$gwppnlMyMenu$txtPwd'] = ''
    # 空き照会
    _form_data['wpManager$gwppnlLeftZone$btnShoukai'] = '空き照会>>'
    # フォームデータを返す
    #logger.debug(json.dumps(_form_data, indent=2))
    return _form_data

# 空き予約検索を実行する
@reserve_tools.elapsed_time
#def get_empty_reserves_html(cfg, form_data, date_list,logger=None):
def get_empty_reserves_html(cfg, cookies, form_data, logger=None):
    """[summary]
    検索対象日を指定して、空き予約検索を実行する
    Args:
        cfg ([Dict]): 設定ファイルを読み込んだオブジェクト
        form_data ([Dict]): フォームデータ
        date ([type]): 検索対象日
        logger ([Object], optional): ロギングオブジェクト. Defaults to None.
    Returns:
        reserves[Dict]: 検索対象日の空き予約情報
    """
    global http_req_num
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Referer': 'https://www.pf489.com/machida/web/Wp_TopMenu.aspx',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'www.pf489.com',
        'Origin': 'https://www.pf489.com',
        'sec-ch-ua': '" Not A;Brand";v="90", "Chromium";v="90", "Google Chrome";v="90"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'authority': 'www.pf489.com',
        'method': 'POST',
        'path': '/machida/web/Wp_TopMenu.aspx',
        'scheme': 'https'
    } 
    # cookieを取得する
    # 検索対象日
    _date = '2022/01/28'
    # フォームデータの作成。日付部分のみ上書きする
    _form_data = form_data
    _form_data['wpManager$gwppnlLeftZone$ucTermSettings$txtDateFrom'] = str(_date)
    # cookiesを確認する
    logger.debug(f'receive cookies: {cookies}')
    # クッキーを初期化する
    _cookies = {}
    for cookie in cookies:
        _name = cookie['name']
        _value = cookie['value']
        logger.debug(f'_cookie: {_name} : {_value}')
        _cookies[f'{_name}'] = f'{_value}'
    logger.debug(f'generate _cookies: {_cookies}')
    # requestsモジュールで接続する
    #session = requests.Session()
    session = requests.session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])
    logger.debug(f'session.cookies: {session.cookies}')
    # seleniumのcookiesをrequestsで使えるように変換する
    # for cookie in cookies:
    #     for item in cookie:
    #         if type(cookie[item]) != str:
    #             cookie[item] = str(cookie[item])
    #         session.cookies.update(requests.cookies.cookiejar_from_dict(cookie))
    #response = session.post(cfg['third_url'], headers=headers, data=_params)
    #logger.debug(f'session cookies: {session.cookies}')
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    #_params = urllib.parse.urlencode(_form_data)
    #response = session.post(cfg['third_url'], headers=headers, data=_params)
    response = session.post(cfg['third_url'], headers=headers, data=_form_data)
    #response = requests.post(cfg['third_url'], headers=headers, cookies=_cookies, data=_form_data)
    #response = requests.post(cfg['third_url'], headers=headers, cookies=_cookies, data=_params)
    http_req_num += 1
    # 文字コードが正しく設定されていない(shft_jisがISO-8859-1となっている)ので、下記の行を追加する
    logger.debug(f'response_encoding: {response.encoding}')
    response.encoding = response.apparent_encoding
    # デバッグ用
    html = reserve_tools.save_html_to_filename(response, 'Wg_JikantaibetsuAkiJoukyou.html')
    # トップページではcookieを発行していなかった
    #_req_cookies = session.cookies
    _req_cookies = response.cookies
    logger.debug(f'Wg_JikantaibetsuAkiJoukyou cookies:')
    logger.debug(f'{_req_cookies}')
    #logger.debug(json.dumps(_req_cookies, indent=2))
    logger.debug(f'history:')
    logger.debug(f'{response.history}')
    return response

############
# 非同期処理 開始

# コルーチンを生成する
#@reserve_tools.elapsed_time
async def coroutine(req_obj, response):
    return req_obj, response.status, await response.text()

#@reserve_tools.elapsed_time
async def get_request_fetch(session, coro, req_obj, cfg):
    """
    HTTPリソースからデータを取得しコルーチンを呼び出す
    """
    # 検索対象日のリストを設定する
    date_list = req_obj
    # トップメニューのURLを設定する
    top_url = cfg['first_url']
    # 空き検索ページのURLを設定する
    search_url = cfg['second_url']
    
    async with async_timeout.timeout(20):
        try:
            response = await session.get(req_obj[2], headers=req_obj[3], cookies=req_obj[4])
        except ClientError as e:
            print(e)
            response = None
    return await coro(req_obj, response)

#@reserve_tools.elapsed_time
async def bound_get_request_fetch(semaphore, session, coro, req_obj, cfg):
    """
    並列処理数を制限しながらHTTPリソースを取得するコルーチン
    """
    async with semaphore:
        return await get_request_fetch(session, coro, req_obj, cfg)

# 検索対象年月日の空きコートを取得する
@reserve_tools.elapsed_time
async def get_request_courts(split_date_lists, coro, limit, cfg):
    """
    並列処理数を制限しながらHTTPリソースを取得するコルーチン
    """
    global http_req_num
    tasks = []
    semaphore = asyncio.Semaphore(limit)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for req_obj in split_date_lists:
            http_req_num += 1
            task = asyncio.ensure_future(bound_get_request_fetch(semaphore, session, coro, req_obj, cfg))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)
        return responses

# 空きコートの空き時間帯を取得する
@reserve_tools.elapsed_time
async def get_request_time(cfg, cookies, court_link_list, coro, limit=1):
    """
    並列処理数を制限しながらHTTPリソースを取得するコルーチン
    """
    global http_req_num
    # cookies リストから同時実行数分のcookieを取得するため、indexを定義する
    index = 0
    tasks = []
    # リファレンスヘッダーを定義する。これがないと検索できない
    headers_court = { 'Referer': cfg['court_search_url'] }
    semaphore = asyncio.Semaphore(limit)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for _day, _link_list in court_link_list.items():
            for _link in _link_list:
                search_url = cfg['court_search_url'] + re.sub('^\.\/ykr31103\.aspx', '', _link)
                # デバッグ用ファイル名として保存するエンティティ名を生成する
                name = md5(search_url.encode('utf-8')).hexdigest()
                _entity = f'{_day}_{name}'
                # cookies リストからcookieを取得する
                _index = index % limit
                # urlrリストオブジェクトを作成する
                req_obj = [ _day, _entity, search_url, headers_court, cookies[_index] ]
                http_req_num += 1
                task = asyncio.ensure_future(bound_get_request_fetch(semaphore, session, coro, req_obj))
                tasks.append(task)
                index += 1
        responses = await asyncio.gather(*tasks)
        return responses


    # cookieの取得
    ## トップページに接続する
    #( cookies ) = connect_top_menu(cfg, date_list)
    ## 
    ## 空き予約検索ページの接続とページソースの取得
    #( cookies, form_data ) = get_search_
    ## 空き予約検索ページの解析と検索のためのPOSTリクエストフォームの作成
    ## 空き予約検索ページへの検索条件の入力と検索の実行
    ## 空き予約検索結果のページソースの取得
    # (選択１)空き予約検索結果ページの解析と空き予約結果リストへの登録(排他制御処理)
    # 非同期処理の終了

# 非同期処理 終了
##################


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
def main_search_empty_reserves(cfg, date_list, coro, limit=4, logger=None):
    """
    初期化処理
    """
    # 初期化処理(主に非同期並列処理のための変数の作成)
    # HTTPリクエスト数
    global http_req_num
    # 実行時間を測定する
    start = time.time()
    # 検索対象日をスレッド数に応じたリストに分割する
    split_date_lists = reserve_tools.split_date_list_by_threads(cfg, date_list, logger=logger)
    #request_objs = create_request_objs(cfg, date_list, cookies, form_datas, logger=logger)
    #return None
    ( cookies, shtml )= connect_to_get_cookies_and_html(cfg, logger=logger)
    # フォームデータを作成する
    ( form_data ) = create_form_data(cfg, shtml, logger=logger)
    # 空き予約検索を実行する
    ( reserves ) =  get_empty_reserves_html(cfg, cookies, form_data, logger=logger)
    # 非同期処理の開始
    # 非同期IO処理のaiohttpのためにイベントループを作成する
    #loop = asyncio.get_event_loop()
    ## 検索のためのリクエストオブジェクトを作成する
    #results = loop.run_until_complete(get_request_courts(split_date_lists, coro, limit, cfg))
    # デバッグ用(HTTPリクエスト回数を表示する)
    logger.debug(f'HTTP リクエスト数: {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - start
    logger.debug(f'main() duration time: {elapsed_time} sec')
    # 非同期処理の終了
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

    # 非同期ロック
    async_lock_reserves = AsyncioLockReservesList()
    reserves_list = async_lock_reserves.reserves_list
    # 事前準備
    ( cfg, logger, date_list ) = prepare_serch_empty_reserves(cfg_filename="cfg.json")
    logger.info(f'starting to search empty reserve.')
    # 同時実行数
    threads = cfg['threads_num']
    #( cookies, form_datas ) = get_cookie(cfg)
    # 空き予約検索データを作成する
    #request_objs = create_request_objs(cfg, date_list, cookies, form_datas, logger=logger)
    # 検索対象年月日を指定して、空き年月日のHTMLボディを取得する
    #results = main(request_objs, coro=coroutine, limit=threads, logger=logger)
    results = main_search_empty_reserves(cfg, date_list, coro=coroutine, limit=threads, logger=logger)
    # 空きコートのリンクを作成する
    # for url, status, body in results:
    #     get_empty_court(body, cfg, url[0], court_link_list, logger=logger)
    # logger.debug(f'')
    # logger.debug(f'#### Analyzed Link End : ####')
    # logger.debug(f'')
    #print(json.dumps(court_link_list, indent=2))
    # 実行時間を表示する
    # elapsed_time = time.time() - _start
    # logger.debug(f'search empty court link duration time: {elapsed_time} sec')
    #print(json.dumps(reserves_list, indent=2, ensure_ascii=False))
    # 空き予約リストを昇順にソートする
    # sorted_reserves_list = reserve_tools.sort_reserves_list(reserves_list)
    # # LINEにメッセージを送信する
    # postproc(reserves_list, logger=logger)
    # logger.info(f'finished to search empty reserve.')
    # # 空き予約リストに値があるかないかを判断し、予約処理を開始する
    # #print(f'reserves_list: {threadsafe_list.reserves_list}')
    # if len(reserves_list) == 0:
    #     logger.info(f'stop do reserve because no empty reserve.')
    # else:
    #     logger.info(f'starting reserve process.')
    #     reserve_result = main3(cfg, sorted_reserves_list, want_date_list, logger=logger)
    #     #return None
    # 空き検索処理の事後処理
    #postproc_search_empty_reserves(logger=logger)
    
    # デバッグ用(HTTPリクエスト回数を表示する)
    logger.info(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - _start
    logger.info(f'whole() duration time: {elapsed_time} sec')
    
    exit()
