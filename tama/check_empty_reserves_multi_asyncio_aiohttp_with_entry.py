#
# check_empty_reserves_multi_asyncio_aiohttp7.pyの目的
# - 某サイトのasyncioの処理フローを導入する
# - 指定日から空きコートのリンクを取得する部分と、指定日の空きコートから空き時間帯を取得する部分を分ける
# 
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
from time import sleep

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

import asyncio
import aiohttp
import async_timeout
from aiohttp import ClientError

# URLの'/'が問題になるためハッシュ化する
from hashlib import md5
from pathlib import Path

# ツールライブラリを読み込む
import reserve_tools

http_req_num = 0

# クローラー
## cookieを取得するため、トップページにアクセスする
@reserve_tools.elapsed_time
def get_cookie(cfg):
    """
    検索時に必要なcookieとフォームデータを同時実行数分だけ取得する
    """
    # 変数の初期化する
    cookies = []
    form_datas = []
    global http_req_num
    # 同時実行数を取得する
    threads = cfg['threads_num']
    # 同時実行数分のcookieとフォームデータを取得する
    for index in range(threads):
        # セッションを開始する
        session = requests.session()
        response = session.get(cfg['first_url'])
        http_req_num += 1
        #response.raise_for_status()
        # cookieオブジェクトを取得する
        cookie_sessionid = session.cookies.get(cfg['cookie_sessionid'])
        cookie_starturl = session.cookies.get(cfg['cookie_starturl'])
        cookies.append({ cfg['cookie_sessionid']: cookie_sessionid, cfg['cookie_starturl']: cookie_starturl })
        #print(f'{cookie_sessionid}:{cookie_starturl}')
        # フォームデータを取得する
        form_datas.append(get_formdata(response))
    #print(json.dumps(cookies, indent=2, ensure_ascii=False))
    #print(json.dumps(form_datas, indent=2, ensure_ascii=False))
    return cookies , form_datas

## フォームデータを取得する
#@reserve_tools.elapsed_time
def get_formdata(response):
    """
    ページからフォームデータを取得する
    """
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # formデータ中の__VIEWSTATE, __VIEWSTATEGENERATOR, __EVENTVALIDATIONを取得する
    _viewstate = soup.find("input", id="__VIEWSTATE")
    _viewstategenerator = soup.find("input", id="__VIEWSTATEGENERATOR")
    _eventvalidation = soup.find("input", id="__EVENTVALIDATION")
    form_data = {
        '__VIEWSTATE': _viewstate.get("value"),
        '__VIEWSTATEGENERATOR': _viewstate.get("value"),
        '__EVENTVALIDATION': _eventvalidation.get("value")
    }
    return form_data

#@reserve_tools.elapsed_time
def get_empty_court(response, cfg, day, court_link_list):
    """
    年月日指定の空き予約検索結果ページから空きコートのリンクを取得する
    空きコートリンクのリストは次のdict型となる
    court_link_list['day'] = [ url0, url1, ... ]
    """
    # 空き予約結果ページを検索したときの指定年月日を設定する
    _day = day
    #print(f'analyze get_court : {_day}')
    # 登録済みリンクを初期化する
    registerd_link = ''
    ## レスポンスオブジェクトをHTML化する
    html = str(response)
    soup = BeautifulSoup(html, features='html.parser')
    # aタグのhref属性を持つタグを抽出する
    for atag in soup.find_all('a'):
        # 空きの文字列をもつaタグのみ抽出する
        if atag.string == '空き':
            # 空きコートリンクのリストに追加する
            # 同じコードで空き予約が間欠的に発生した場合、同じリンクが複数表示されるため、二重登録を防ぐ
            # 前と同じリンクか確認し、異なる場合のみ追加する
            if registerd_link != atag['href']:
                # 除外コートのリンクは追加しないため、リンクに除外コートのコート番号を確認する
                # 除外コートのリスト数を超えたら登録する
                _exclude_court_count = len(cfg['exclude_courts'])
                _match_count = 0
                for _exclude_court in cfg['exclude_courts']:
                    if _exclude_court in atag['href']:
                        #print(f'found exclude court: {_exclude_court}')
                        break
                    else:
                        # 除外コートリストにマッチしなかったのでカウントアップする
                        _match_count += 1
                        # マッチしなかった回数がリスト数以上になれば登録する
                        if _match_count >= _exclude_court_count:
                            _link_day = str(atag['href'][82:90])
                            if f'{_link_day}' not in court_link_list:
                                court_link_list[f'{_link_day}'] = []
                            #court_link_list[f'{_link_day}'].append(atag['href'])
                            if f'{_day}' !=  f'{_link_day}':
                                print(f'## Different Input: {_day} / Link: {_link_day}')
                            #async with lock:
                                #th_lock_urls.add_url(_link_day, atag['href'])
                                #async_lock_urls.add_url(_link_day, atag['href'])
                            # 空きコートリンクを登録する
                            court_link_list[f'{_link_day}'].append(atag['href'])
                            # 登録済みリンクとして代入する。これによって二重登録を防止する
                            registerd_link = atag['href']
    # 検索リストを表示する
    #print(court_link_list)
    # 終わる
    return court_link_list
    #return None

# 指定した年月日のコート空き予約ページから空き予約の時間帯を取得する
#@reserve_tools.elapsed_time
def get_empty_reserves(response, cfg, day, reserves_list):
    """
    空き予約の時間帯を取得する
    """
    #print(reserves_list['day'])
    #print(f'get_empty_time: {day}')
    # レスポンスオブジェクトをHTML化する
    ## 空のレスポンスオブジェクトの場合はHTTPリクエストが失敗しているので、解析しないで returnを返す
    #print(type(response))
    #print(dir(response))
    #if response.status != 200:
    #    return None
    ## レスポンスオブジェクトをHTML化する
    html = str(response)
    soup = BeautifulSoup(html, features='html.parser')
    # コート名を取得する
    court_table = soup.find(class_='table-vertical table-timeselect-sisetu')
    court_string = court_table.tr.td.next_sibling.next_sibling.stripped_strings
    for name in court_string:
        court_name = re.sub('庭球場（奈良原以外）\s+', '', name)
        court_name = re.sub('^奈良原公園庭球場\s+', '', court_name)
        # '※午後８時閉場　緊急事態宣言期間中　'の文字列があった場合は削除する
        court_name = re.sub('※午後８時閉場　緊急事態宣言期間中　', '', court_name)
        #print(court_name)
    # 空き予約時間帯を取得する
    ## 空き予約時間のテーブル
    empty_table = soup.find(class_='table-vertical table-timeselect')
    #print(empty_table)
    ## 空き予約時間のタグのみ抽出する
    for empty in empty_table.find_all(class_='aki_empty_left'):
        empty_string = empty.div.label.string
        # 文字列の？を削除する
        reserve = re.sub('^\D+', '', empty_string)
        # 一桁の時間帯の文字列に0を入れる
        reserve = re.sub('^(\d):', r'0\1:', reserve)
        reserve = re.sub('～\s(\d):', r'～0\1:', reserve)
        # 空き予約の除外時間帯かを確認し、除外時間帯以外を登録する
        _match_count = 0
        _exclude_time_count = len(cfg['exclude_times'])
        for _exclude_time in cfg['exclude_times']:
            if reserve == _exclude_time:
                print(f'matched exclude time: {court_name} {day} {reserve}')
                break
            else:
                # 除外時間帯にマッチしなかったので、カウントアップする
                _match_count += 1
                # マッチしなかった回数がリスト回数以上になれば登録する
                if _match_count >= _exclude_time_count:
                    # 空き予約リストに追加する
                    ## 空き予約リストに月日のKeyがあるか確認する
                    if f'{day}' not in reserves_list:
                        reserves_list[f'{day}'] = {}
                    reserves_list[f'{day}'].setdefault(reserve, []).append(court_name)
    #print(reserves_list)
    return reserves_list

# コートの空き予約を検索するためのリクエストオブジェクトのリストを作成する
#@reserve_tools.elapsed_time
def create_request_objs(cfg, date_list, cookies, form_datas):
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
    print(f'call get_empty_reserves start: ##############')
    # リファレンスヘッダーを定義する。これがないと検索できない
    headers_day = { 'Referer': cfg['day_search_url'] }
    #headers_court = { 'Referer': cfg['court_search_url'] }
    # 検索URL用のパラメータ部分のURLを定義する
    param_day_string = '?PSPARAM=Dt::0:1:205::::_TODAYSTRING_:1,2,3,4,5,6,7,10:_DATESTRING_:False:_SEARCHPARAM_:0:0&PYSC=0:1:205::::_TODAYSTRING_:1,2,3,4,5,6,7,10&PYP=:::0:0:0:0:True::False::0:0:0:0::0:0'
    # 今日の年月日を取得する
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

############
# 非同期処理 開始

## 空き予約時間帯を検索するURLリストへの登録を排他制御する
class AsyncioLockUrlsList:
    """
    スレッド処理に対応するため、排他制御で検索対象URLリストの登録を行う
    """
    lock = asyncio.Lock()
    def __init__(self):
        self.court_link_list = {}
    async def add_url(self, day, url):
        async with self.lock:
            #print(f'get url : {day} {url}')
            #print(f'########')
            await self.court_link_list.setdefault(day, []).append(url)

## 空き予約時間帯を検索するURLリストへの登録を排他制御する
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

# コルーチンを生成する
#@reserve_tools.elapsed_time
async def coroutine(req_obj, response):
    return req_obj, response.status, await response.text()

#@reserve_tools.elapsed_time
async def get_request_fetch(session, coro, req_obj):
    """
    HTTPリソースからデータを取得しコルーチンを呼び出す
    """
    async with async_timeout.timeout(20):
        try:
            response = await session.get(req_obj[2], headers=req_obj[3], cookies=req_obj[4])
        except ClientError as e:
            print(e)
            response = None
    return await coro(req_obj, response)

#@reserve_tools.elapsed_time
async def bound_get_request_fetch(semaphore, session, coro, req_obj):
    """
    並列処理数を制限しながらHTTPリソースを取得するコルーチン
    """
    async with semaphore:
        return await get_request_fetch(session, coro, req_obj)

# 検索対象年月日の空きコートを取得する
@reserve_tools.elapsed_time
async def get_request_courts(request_objs, coro, limit):
    """
    並列処理数を制限しながらHTTPリソースを取得するコルーチン
    """
    global http_req_num
    tasks = []
    semaphore = asyncio.Semaphore(limit)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for req_obj in request_objs:
            http_req_num += 1
            task = asyncio.ensure_future(bound_get_request_fetch(semaphore, session, coro, req_obj))
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

# 非同期処理 終了
##################

# 事前準備
@reserve_tools.elapsed_time
def prepare():
    """
    変数の初期化などの事前準備
    """
    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    reserve_tools.set_public_holiday('public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = reserve_tools.read_json_cfg('cfg.json')
    # 検索リストを作成する
    ## 検索対象月を取得する
    target_months_list = reserve_tools.create_month_list(cfg)
    ## 検索対象月リストと祝日リストから検索対象年月日リストを作成する
    date_list = reserve_tools.create_date_list(target_months_list, public_holiday, cfg)
    # 予約希望日リストを作成する
    want_date_list = reserve_tools.create_want_date_list(target_months_list, public_holiday, cfg)
    return cfg, date_list, want_date_list

# 検索対象年月日を指定して、空き予約コートがある年月日と空きコートリンクのリストを取得する
@reserve_tools.elapsed_time
def main(request_objs, coro, limit=4):
    """
    検索対象年月日を指定して、空き予約コートがある年月日と空きコートリンクのリストを取得する
    """
    # 実行時間を測定する
    start = time.time()
    # HTTPリクエスト数
    global http_req_num
    # 非同期IO処理のaiohttpのためにイベントループを作成する
    loop = asyncio.get_event_loop()
    # 空き予約検索を開始する
    ## 検索のためのリクエストオブジェクトを作成する
    results = loop.run_until_complete(get_request_courts(request_objs, coro, limit))
    # デバッグ用(HTTPリクエスト回数を表示する)
    print(f'HTTP リクエスト数: {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - start
    print(f'main() duration time: {elapsed_time} sec')
    print(f'####################################')
    return results

# 空き予約日と空きコートリンクのリストから空き予約時間帯を取得し、空き予約コートリストを作成する
@reserve_tools.elapsed_time
def main2(cfg, cookies, court_link_list, coro, limit=4):
    """
    空き予約日と空きコートリンクのリストから空き予約時間帯を取得し、空き予約コートリストを作成する
    """
    # 実行時間を測定する
    start = time.time()
    # HTTPリクエスト数
    global http_req_num
    # 非同期IO処理のaiohttpのためにイベントループを作成する
    loop = asyncio.get_event_loop()
    # 空き予約検索を開始する
    ## 検索のためのリクエストオブジェクトを作成する
    results = loop.run_until_complete(get_request_time(cfg, cookies, court_link_list, coro, limit))
    # デバッグ用(HTTPリクエスト回数を表示する)
    print(f'HTTP リクエスト数: {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - start
    print(f'main2() duration time: {elapsed_time} sec')
    print(f'####################################')
    return results

# 事前準備作業
def prepare_proc_for_reserve(cfg, headers):
    """
    事前準備作業をする
    """
    #ヘッダー情報
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
    }
    # トップページに接続する
    #( cookies ) = get_cookie_request(cfg, headers)
    # ログインIDとパスワードを入力し、ログインし、ログイン後のcookieを取得する
    #( cookies ) = do_login_and_get_cookie(cfg, headers, cookies)
    # seleniumを初期化
    ( driver, mouse ) = setup_driver(headers)
    # トップページに接続し、ログイン画面で利用者IDとパスワードを入力する
    ( cookies , reserved_list, reserved_num ) = selenium_get_cookie(driver, cfg)
    # cookie、既存予約リスト、予約済み数を返す
    return cookies, reserved_list, reserved_num

# Selenium初期化
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

# 利用者IDとパスワードでログインし、認証後のcookieを取得する 
@reserve_tools.elapsed_time
def selenium_get_cookie(driver, cfg):
    """
    selenuimuで接続する
    cookieを取得する
    トップページにアクセスし、ログインをクリックする
    ログインボタンでjavascriptを実行するため、ログインまではseleniumを利用する
    """
    global http_req_num
    # トップページにアクセスする
    response = driver.get(cfg['first_url'])
    http_req_num += 1
    sleep(1)
    cookies = driver.get_cookies()
    # 画面のtitleを確認する
    assert '多摩市 施設予約トップページ' in driver.title
    # 予約の確認をクリックして、認証画面を表示させる
    driver.find_element_by_xpath("//*[@id='ykr00001c_CheckImgButton']").click()
    # ログインをクリックして、認証画面に進む
    # response = driver.get(cfg['login_url'])
    http_req_num += 1
    assert '多摩市 ログイン' in driver.title
    # DOM上に表示されるまで待機する
    wait = WebDriverWait(driver, 10)
    #  利用者IDとパスワード、ログインボタンが表示されるまで待機する
    #f_userid = wait.until(EC.presence_of_element_located((By.ID, "LoginInputUC$UserIdTextBox")))
    #f_password = wait.until(EC.presence_of_element_located((By.ID, "LoginInputUC$PasswordTextBox")))
    #f_login=wait.until(EC.presence_of_element_located((By.ID, "LoginInputUC$LoginImgButton")))
    # 利用者IDとパスワードを入力し、ログインボタンをクリックする
    f_userid = driver.find_element_by_xpath("//*[@id='LoginInputUC_UserIdTextBox']")
    f_password = driver.find_element_by_xpath("//*[@id='LoginInputUC_PasswordTextBox']")
    # 利用者IDフィールドに入力する
    f_userid.send_keys(str(cfg['userid']))
    # パスワードフィールドに入力する
    f_password.send_keys(str(cfg['password']))
    # ログインボタンをクリックする
    driver.find_element_by_xpath("//*[@id='LoginInputUC_LoginImgButton']").click()
    http_req_num += 1
    # すべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    #sleep(1)
    # トップページに戻っているか確認する
    # 申込内容一覧ページが表示されているか確認する
    assert '多摩市 申込内容一覧' in driver.title
    # 認証後のcookieを取得する
    cookies = driver.get_cookies()
    # cookiesをrequestsで扱えるよにdict型に変換する
    _cookies = {}
    for _dict in cookies:
        _cookies[f'{_dict["name"]}'] = f'{_dict["value"]}'
    # 現在、表示されているページのソースコードを取得する
    response = driver.page_source
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = f'reserved_list.html'
    #with open(_file_name, 'w', encoding='utf-8') as file:
    #    file.write(response)
    # 既存予約を取得する
    ( reserved_list, reserved_num ) = get_current_reserved_list(response)
    # seleniumを終了する
    driver.quit()
    return _cookies, reserved_list, reserved_num

# フォームデータを解析する
def get_common_formdata(response):
    """
    ログイン画面のフォームデータを取得する
    """
    # フォームデータ(dict型)を初期化する
    _form_data = {}
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    _form = soup.find_all('form')[0]
    # フォームデータを取得する
    _input_tags = _form.find_all('input')
    for _tag in _input_tags:
        # name属性の値があるタグを対象とする
        if _tag.get('name') is not None:
            # value属性値がない場合はNullを入れる
            if _tag.get('value'):
                _form_data[_tag['name']] = _tag['value']
            else:
                _form_data[_tag['name']] = ""
    # フォームデータを返す
    #print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    return _form_data

# フォームデータを解析して既存予約リストと予約件数を取得する
def get_current_reserved_list(response):
    """
    予約の確認をクリックして、予約済みリストと予約件数を取得する
    """
    # html解析
    soup = BeautifulSoup(response, 'html.parser')
    # 予約情報部分のみ抽出する
    _form = soup.find_all('form')[0]
    _table = _form.find('table', id='ykr11001c_YoyakuListGridView')
    _td = _table.find_all('td', class_='table-cell-name')
    # 予約情報と予約件数を初期化する
    reserved_list = {}
    reserved_num = 0
    # 予約情報を取得する
    for _tag in _td:
        #print(_tag.contents)
        # 年月日時間部分を取得
        _datetime = _tag.contents[0]
        # コート名を取得
        _court = _tag.contents[2]
        # 不要な文字列を削除
        _datetime = _datetime.replace('\n', '').replace('\t', '').replace('\xa0', '').replace('令', '')
        # 年月日を取得
        _date = _datetime.split('\u3000')[0]
        # 時間を取得
        _time = _datetime.split('\u3000')[1]
        # 曜日を削除
        _date = re.sub('\(\w\)', '', _date)
        _year = str(int(_date.split('.')[0]) + 2018)
        _month = str(_date.split('.')[1]).zfill(2)
        _day = str(_date.split('.')[2]).zfill(2)
        __date = _year + _month + _day
        # コート名のみ抽出する
        _court = _court.replace('\n', '').replace('\t', '').replace('\u3000※午後８時閉場\u3000緊急事態宣言期間中\u3000', '').replace('庭球場（奈良原以外）','').replace('奈良原公園庭球場','')
        #print(f'{__date} {_time}')
        #print(_court)
        if __date not in reserved_list:
            reserved_list[__date] = {}
        reserved_list[__date].setdefault(_time, []).append(_court)
        reserved_num += 1
    print(json.dumps(reserved_list, indent=2, ensure_ascii=False))
    print(f'reserved_num: {reserved_num}')
    return reserved_list, reserved_num

# 空き予約をする
@reserve_tools.elapsed_time
def do_reserve(cfg, court_map, cookies, date, time, court):
    """
    予約する
    """
    #ヘッダー情報
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
        'Referer' : cfg['day_search_url']
    }
    # コートIDを取得する
    court_id = court_map[court]
    location_id = court_id.split(':')[0]
    print(f'{court_id} , {location_id}')
    # 検索URL用のパラメータ部分のURLを定義する
    param_day_string = '?PSPARAM=Ic::0:1:205::::_DATESTRING_:1,2,3,4,5,6,7,10:_COURTID_:101:::_DATESTRING_:0:0&PYSC=0:1:205::::_DATESTRING_:1,2,3,4,5,6,7,10&PYP=:::0:0:0:0:True::False::0:0:0:0::0:0'
    # 今日の年月日を取得する
    ## タイムゾーンを設定する
    #JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    #_now = datetime.datetime.now(JST)
    #_today = str(_now.year) + str(_now.month).zfill(2) + str(_now.day).zfill(2)
    # パラメータ文字列の日付部分を置換する
    _param = re.sub('_LOCATIONID_', location_id, param_day_string)
    _param = re.sub('_COURTID_', court_id, _param)
    #_param = re.sub('_TODAYSTRING_', _today, _param)
    _param = re.sub('_DATESTRING_', str(date), _param)
    print(f'query_param: {_param}')
    # 指定年月日のコートの空き状況ページに移動する
    response = go_to_date_court(cfg, headers, cookies, _param)
    # 予約にチェックし、予約申込のページに移動する
    response = go_to_reserve(cfg, headers, cookies, time, response)
    # 利用者数を入力し、予約カゴに登録をクリックする
    response = go_to_input_reserve(cfg, headers, cookies, response)
    # 前のページに戻り、申込に進むをクリックする
    response = go_to_confirm_reserve(cfg, headers, cookies, response)
    # 予約申込画面で、予約するをクリックする
    response = done_reserve(cfg, headers, cookies, response)
    # 予約番号を取得する
    reserved_number = get_reserved_number(response)
    # 予約情報を作る
    reserve = {}
    reserve[f'{date}'] = {}
    reserve[f'{date}'][time] = [ court ]
    # 予約番号と予約した日時とコートを返す
    print(f'reserved number: {reserved_number}')
    print(f'reserve datetime and court: {reserve}')
    return reserved_number, reserve

# 指定年月日のコートの空き状況ページに移動する
@reserve_tools.elapsed_time
def go_to_date_court(cfg, headers, cookies, _param):
    """
    指定年月日のコートの空き状況ページに移動する
    """
    global http_req_num
    # URLを生成する
    _url = cfg['day_search_url'] + str(_param)
    #print(f'url: {_url}')
    #print(f'headers: {headers}')
    #print(f'cookies: {cookies}')
    response = requests.get(_url, headers=headers, cookies=cookies)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'search_court.html'
    _file = reserve_tools.save_html_to_filename(response, _file_name)
    # 予約希望時間にチェックを入れて、予約内容
    return response

# 予約にチェックし、予約申込のページに移動する
@reserve_tools.elapsed_time
def go_to_reserve(cfg, headers, cookies, wanttime, response):
    """
    希望時間帯にチェックを入れて、予約内容の入力へをクリックする
    """
    global http_req_num
    # ヘッダー情報
    headers['Referer'] = cfg['reserve_url']
    # フォームデータを取得する
    _form_data = get_common_formdata(response)
    # フォームデータの不要部分を削除する
    del _form_data['TimeSelectCtrl$PrevWeekImgBtn']
    del _form_data['TimeSelectCtrl$PrevDayImgBtn']
    del _form_data['TimeSelectCtrl$NextDayImgBtn']
    del _form_data['TimeSelectCtrl$NextWeekImgBtn']
    del _form_data['ReturnButton']
    # 希望時間帯にチェックを入れる
    ## 希望時間帯からPOSTに使うフォームデータを作成する
    # 06:00～08:00とゼロ埋め4桁なのでこれを600:800:1にする
    _stime = int(wanttime.split('～')[0].replace(':', ''))
    _etime =int(wanttime.split('～')[1].replace(':', ''))
    _time = str(_stime) + ':' + str(_etime) + ':1'
    _form_data['YoyakuCB'] = str(_time)
    #print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    # 予約のチェックを入れて、予約内容の入力へをクリックする
    response = requests.post(cfg['reserve_url'], headers=headers, cookies=cookies, data=_form_data)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'reserve_court.html'
    _file = reserve_tools.save_html_to_filename(response, _file_name)
    return response

# 利用者数を入力し、予約カゴに登録をクリックする
@reserve_tools.elapsed_time
def go_to_input_reserve(cfg, headers, cookies, response):
    """
    利用者数を入力し、予約カゴに登録をクリックする
    """
    global http_req_num
    # ヘッダー情報
    headers['Referer'] = cfg['input_reserve_url']
    # フォームデータを取得する
    _form_data = get_common_formdata(response)
    # フォームデータの不要部分を削除する
    del _form_data['CancelButton']
    # 人数と目的を入力する。205はテニス
    _form_data['ItemInputCtrl$NinzuuTotalTextBox'] = 4
    _form_data['ItemInputCtrl$UseClassDropDownList'] = 205
    #print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    # 予約をクリックする
    response = requests.post(cfg['input_reserve_url'], headers=headers, cookies=cookies, data=_form_data)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'input_reserve_court.html'
    _file = reserve_tools.save_html_to_filename(response, _file_name)
    return response

# 前のページに戻り、申込に進むをクリックする
@reserve_tools.elapsed_time
def go_to_confirm_reserve(cfg, headers, cookies, response):
    """
    前のページに戻り、申込に進むをクリックする
    """
    global http_req_num
    # ヘッダー情報
    headers['Referer'] = cfg['day_search_url']
    # フォームデータを取得する
    _form_data = get_common_formdata(response)
    # フォームデータの不要部分を削除する
    del _form_data['WeeklyAkiListCtrl$FilteringButton']
    del _form_data['WeeklyAkiListCtrl$PrevWeekImgBtn']
    del _form_data['WeeklyAkiListCtrl$PrevDayImgBtn']
    del _form_data['WeeklyAkiListCtrl$NextDayImgBtn']
    del _form_data['WeeklyAkiListCtrl$NextWeekImgBtn']
    del _form_data['WeeklyAkiListCtrl$NextMonImgBtn']
    del _form_data['WeeklyAkiListCtrl$ModoruButton']
    del _form_data['CartUC$RegistButton2']
    #print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    # 予約をクリックする
    response = requests.post(cfg['day_search_url'], headers=headers, cookies=cookies, data=_form_data)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'confirm_reserve_court.html'
    _file = reserve_tools.save_html_to_filename(response, _file_name)
    return response

# 予約申込画面で、予約するをクリックする
@reserve_tools.elapsed_time
def done_reserve(cfg, headers, cookies, response):
    """
    予約申込画面で、予約するをクリックする
    """
    global http_req_num
    # ヘッダー情報
    headers['Referer'] = cfg['result_reserve_url']
    # フォームデータを取得する
    _form_data = get_common_formdata(response)
    # フォームデータの不要部分を削除する
    del _form_data['ToYoyakuChangeButton1']
    del _form_data['ToYoyakuChangeButton2']
    del _form_data['CancelButton']
    #print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    # 予約をクリックする
    response = requests.post(cfg['result_reserve_url'], headers=headers, cookies=cookies, data=_form_data)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'result_reserve_court.html'
    _file = reserve_tools.save_html_to_filename(response, _file_name)
    return response

# 予約番号を取得する
@reserve_tools.elapsed_time
def get_reserved_number(response):
    """
    予約番号を取得する
    """
    # レスポンスを読み込む
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    _form = soup.find_all('form')[0]
    # 予約番号を取得する
    _tr = _form.find('tr', id="ctl01_UketukeNoRow")
    reserved_number = _tr.span.string
    if bool(reserved_number):
        # 予約番号を取得できたら
        #print(f'reserved_number: {reserved_number}')
        return reserved_number
    else:
        return None

## 予約確定通知メッセージを作成する
def create_reserved_message(reserved_number, reserve, message_bodies, cfg):
    """
    予約確定通知用のメッセージボディーを作成する
    """
    # メッセージ本文の文頭を作成する
    _body = f'\n予約が確定しました。マイページで確認してください。\n'
    _body = f'{_body}予約番号: {reserved_number}\n'
    # 予約リストを与えて、取得した予約情報を追記する
    message_bodies = reserve_tools.create_message_body(reserve, message_bodies, cfg)
    # message_bodiesリストの最初の要素が予約情報なので、これを文頭と結合する
    _reserve_info = message_bodies[0]
    _body = f'{_body}{_reserve_info}'
    # message_bodiesリストの最初の要素を書き換える
    message_bodies[0] = f'{_body}'
    return message_bodies

## 空き予約リスト、希望日リスト、希望時間帯リスト、希望施設名リストより予約処理対象リストを作成する
def create_target_reserves_list(reserves_list, want_date_list, want_hour_list, want_location_list):
    """
    予約処理対象の希望日、希望時間帯のリストを作成する
    """
    # 希望日+希望時間帯のリストを初期化する
    target_reserves_list = {}
    # 空き予約リストから、空き予約日と値を取得する
    for _date, _d_value in reserves_list.items():
        # 空き予約日が希望日リストに含まれていない場合は次の空き予約日に進む
        if _date not in want_date_list:
            print(f'not want day: {_date}')
            continue
        # 空き予約時間帯とコートリストを取得する
        for _time, _court_list in _d_value.items():
            # 空き予約時間帯が希望時間帯リストに含まれていない場合は次の予約時間帯に進む
            if _time not in want_hour_list:
                print(f'not want hour: {_date} {_time}')
                continue
            for _court in _court_list:
                # 空きコート名から、施設名とコート名に分割する
                _location_name = _court.split('／')[0]
                # 空き予約コートが希望施設名に含まれていない場合は次の空きコートに進む
                if _location_name not in want_location_list:
                    print(f'not want location: {_date} {_time} {_court}')
                    continue
                # 希望日+希望時間帯のリストに空き予約日がない場合は初期化後、コート名を追加する
                if _date not in target_reserves_list:
                    target_reserves_list[_date] = {}
                    target_reserves_list[_date][_time] = []
                    target_reserves_list[_date][_time].append(_court)
                    print(f'regist target reserves list: {_date} {_time} {_court}')
                # ある場合は時間帯を追加する
                else:
                    # 同じ時間帯がない場合は時間帯は追加する
                    if _time not in target_reserves_list[_date]:
                        target_reserves_list[_date][_time] = []
                        target_reserves_list[_date][_time].append(_court)
                        print(f'regist target reserves list: {_date} {_time} {_court}')
                    else:
                        # 次の時間帯に進む
                        print(f'found {_time} in target reserves list. therefore next time.')
                        # breakでコートのループを抜ける
                        break
            else:
                # _d_valueの次のループに進む
                continue
    # 希望日+希望時間帯のリストを返す
    #print(f'{target_reserves_list}')
    return target_reserves_list

# 事後処理
def postproc(reserves_list):
    """
    空き予約リストを整形して、LINEにメッセージを送信する
    """
    # 送信メッセージリストの初期化
    message_bodies = []
    # 送信メッセージを作成する
    message_bodies = reserve_tools.create_message_body(reserves_list, message_bodies, cfg)
    # LINEに送信する
    reserve_tools.send_line_notify(message_bodies, cfg)
    return None

if __name__ == '__main__':
    # 実行時間を測定する
    _start = time.time()

    # 非同期ロック
    async_lock_urls = AsyncioLockUrlsList()
    court_link_list = async_lock_urls.court_link_list
    async_lock_reserves = AsyncioLockReservesList()
    reserves_list = async_lock_reserves.reserves_list
    # 事前準備
    ( cfg, date_list, want_date_list ) = prepare()
    # 同時実行数
    threads = cfg['threads_num']
    ( cookies, form_datas ) = get_cookie(cfg)
    # 空き予約検索データを作成する
    request_objs = create_request_objs(cfg, date_list, cookies, form_datas)
    # 検索対象年月日を指定して、空き年月日のHTMLボディを取得する
    results = main(request_objs, coro=coroutine, limit=threads)
    print(f'')
    print(f'#### Analyzed Link Start : ####')
    print(f'')
    # 空きコートのリンクを作成する
    for url, status, body in results:
        get_empty_court(body, cfg, url[0], court_link_list)
    print(f'')
    print(f'#### Analyzed Link End : ####')
    print(f'')
    #print(json.dumps(court_link_list, indent=2))
    # 実行時間を表示する
    elapsed_time = time.time() - _start
    print(f'search empty court link duration time: {elapsed_time} sec')
    print(f'')
    print(f'#### Analyzed Empty Reserves Start : ####')
    print(f'')
    # 空きコートリンクのHTTPページを取得する
    reserves_results = main2(cfg=cfg, cookies=cookies, court_link_list=court_link_list, coro=coroutine, limit=threads)
    # 空きコート時間のDictデータを作成する
    for url, status, body in reserves_results:
        get_empty_reserves(body, cfg, url[0], reserves_list)
    print(f'')
    print(f'#### Analyzed Empty Reserves End : ####')
    print(f'')
    #print(json.dumps(reserves_list, indent=2, ensure_ascii=False))
    # 空き予約リストを昇順にソートする
    sorted_reserves_list = reserve_tools.sort_reserves_list(reserves_list)
    # LINEにメッセージを送信する
    postproc(reserves_list)

    # 空き予約リストに値があるかないかを判断し、予約処理を開始する
    #print(f'reserves_list: {threadsafe_list.reserves_list}')
    if len(reserves_list) == 0:
        print(f'stop do reserve because no empty reserve.')
        #return None
    #want_date_list = reserve_tools.create_want_date_list(target_months_list, public_holiday, cfg)
    # コートマップファイルを読み込む
    court_map = reserve_tools.read_json_cfg('court_map.json')
    # 希望時間帯を取得する
    want_hour_list = cfg['want_hour_list']
    # 希望施設名を取得する
    want_location_list = cfg['want_location_list']
    # 予約処理対象の希望日、希望時間帯のリストを作成する
    # 空き予約リストを昇順にソートする
    #sorted_reserves_list = reserve_tools.sort_reserves_list(reserves_list)
    # 空き予約リストから、空き予約日と時間帯を取得する
    #target_reserves_list = reserve_tools.create_target_reserves_list(sorted_reserves_list, want_date_list, want_hour_list, want_location_list)
    target_reserves_list = create_target_reserves_list(sorted_reserves_list, want_date_list, want_hour_list, want_location_list)
    # 希望日+希望時間帯のリストを出力する
    print(f'target_reserves_list: {target_reserves_list}')
    # 希望日+希望時間帯のリストが空の場合は予約処理を中止する
    if bool(target_reserves_list) == False:
        print(f'reserve process stopped. because empty reserves is not wanted.')
        #return None
    #ヘッダー情報
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
    }
    # 既存予約リストと件数を取得する
    ( cookies, reserved_list, reserved_num ) = prepare_proc_for_reserve(cfg, headers)
    # 予約処理の継続確認
    if reserved_num >= cfg['reserved_limit']:
        print(f'reserve process stopped. because reserved limit: {reserved_num}')
        #return None
    #exit()
    # 希望日+希望時間帯のリストを元に空き予約を探し、予約処理を行う
    for _date, _time_list in target_reserves_list.items():
        for _time, _court_list in _time_list.items():
            for _court in _court_list:
                # 追加した予約によって、既存予約件数が上限を超えている場合はメッセージを出して処理を終了する
                if reserved_num >= int(cfg['reserved_limit']):
                    print(f'reserve number is limit over {cfg["reserved_limit"]}. threfore stop reserve process.')
                    # breakでコートのループを抜ける
                    break
                # 改めてメッセージボディを初期化する
                message_bodies = []
                # 利用日時を入力して空きコート予約を検索する
                #( reserved_number, reserve ) = do_reserve(cfg, court_map, cookies, 20210928, '06:00～08:00', '多摩東公園庭球場Ｃ（人工芝）')
                ( reserved_number, reserve ) = do_reserve(cfg, court_map, cookies, _date, _time, _court)
                # 予約できなかった場合はreturn を返す
                if reserved_number is None:
                    print(f'could not do reserve: {reserve}')
                    continue
                # 予約確定通知のメッセージを作成する
                message_bodies = create_reserved_message(reserved_number, reserve, message_bodies, cfg)
                # LINEに送信する
                reserve_tools.send_line_notify(message_bodies, cfg)
                # 予約件数に1件追加する
                reserved_num += 1
    # プログラムの終了
    #exit()
    #return None
    
    # デバッグ用(HTTPリクエスト回数を表示する)
    print(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - _start
    print(f'whole() duration time: {elapsed_time} sec')
    
    exit()