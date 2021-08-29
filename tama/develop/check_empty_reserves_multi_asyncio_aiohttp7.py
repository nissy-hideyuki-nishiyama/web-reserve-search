#
# check_empty_reserves_multi_asyncio_aiohttp7.pyの目的
# - 某サイトのasyncioの処理フローを導入する
#
# モジュールの読み込み
## HTMLクローラー関連
from asyncio.locks import Semaphore
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

# 平行・並列処理モジュール関連
from concurrent.futures import (
    ThreadPoolExecutor,
    Future,
    wait,
    as_completed
)
import threading

import asyncio
import aiohttp
import async_timeout
from aiohttp import ClientError

# URLの'/'が問題になるためハッシュ化する
from hashlib import md5
from pathlib import Path

# ツールライブラリを読み込む
import reserve_tools

# クローラー
## cookieを取得するため、トップページにアクセスする
def get_cookie(cfg):
    """
    cookieを取得する
    """
    # セッションを開始する
    session = requests.session()
    response = session.get(cfg['first_url'])
    #response.raise_for_status()
    
    cookie_sessionid = session.cookies.get(cfg['cookie_sessionid'])
    cookie_starturl = session.cookies.get(cfg['cookie_starturl'])
    cookies = { cfg['cookie_sessionid']: cookie_sessionid, cfg['cookie_starturl']: cookie_starturl }
    #print(f'{cookie_sessionid}:{cookie_starturl}')
    form_data = get_formdata(response)
    #type(response)
    #dir(response)
    #print(response.content)
    #print(response.text)
    return cookies , form_data

## フォームデータを取得する
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




# コートの空き予約を検索する
## 指定日のコートの空き予約を検索するためのURLとパラメータを生成する
## 指定日のコートの空き予約を検索するHTTPリクエストを送信する
@reserve_tools.elapsed_time
#async def get_empty_reserves(cfg, date_list, reserves_list, court_link_list, cookies, http_req_num, th_lock_reserves, th_lock_urls, conn, loop):
#async def get_empty_reserves(cfg, date_list, reserves_list, court_link_list, cookies, http_req_num, th_lock_reserves, async_lock_urls, conn, loop, court_htmls):
async def get_empty_courts(cfg, date_list, court_link_list, cookies, http_req_num, conn, loop, async_lock_urls):
    """
    指定年月日のリストを引数として、その指定年月日の空き予約を検索する
    """
    # タスクリストの初期化
    _days_tasks = []
    # 同時実行するを制限するためにセマフォを導入し、同時実行数を制限する
    # limit = conn_limit
    sem = asyncio.Semaphore(4)
    print(f'call get_empty_reserves start: ##############')
    # リファレンスヘッダーを定義する。これがないと検索できない
    headers_day = { 'Referer': cfg['day_search_url'] }
    headers_court = { 'Referer': cfg['court_search_url'] }
    # 検索URL用のパラメータ部分のURLを定義する
    param_day_string = '?PSPARAM=Dt::0:1:205::::_TODAYSTRING_:1,2,3,4,5,6,7,10:_DATESTRING_:False:_SEARCHPARAM_:0:0&PYSC=0:1:205::::_TODAYSTRING_:1,2,3,4,5,6,7,10&PYP=:::0:0:0:0:True::False::0:0:0:0::0:0'
    # 今日の年月日を取得する
    ## タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    # 希望曜日リストを作成する
    _now = datetime.datetime.now(JST)
    _today = str(_now.year) + str(_now.month).zfill(2) + str(_now.day).zfill(2)
    #print(f'today: {_today}')
    # HTTPリクエストを送信する処理をマルチスレッド化する
    #with ThreadPoolExecutor(max_workers=4) as executor:
    #loop = asyncio.get_running_loop()
    #loop = asyncio.get_event_loop()
    async with sem:
        async with aiohttp.ClientSession(connector=conn) as session:
        #async with aiohttp.ClientSession() as session:
            print(f'coroutine session start: ===========')
            _days_resp = []
            #print(f'before: _days_resp')
            #print(type(_days_resp))
            #print(dir(_days_resp))
            # 指定年月日のリストから検索するためのURLを生成する
            for _day in date_list:
                #print(f'Day: {_day}')
                # 指定年月日のURLリンクリストを初期化する
                #court_link_list['{_day}'] = []
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
                    # 指定年月日を指定した検索リクエストを送信する
                    #res = requests.get(search_url, headers=headers_day, cookies=cookies)
                    http_req_num += 1
                    #_day_resp = loop.create_task(aio_get_request_retry(session, _day, _entity, search_url, headers_day, cookies, cfg, th_lock_urls, th_lock_reserves))
                    #_day_task = loop.create_task(aio_get_request_retry(session, _day, _entity, search_url, headers_day, cookies, cfg, async_lock_urls, court_link_list))
                    #_day_task = loop.create_task(aio_get_request_retry(session, _day, _entity, search_url, headers_day, cookies))
                    #_days_tasks.append(_day_task)
            print(f'=== finished to get court link request.===')
            print(f'HTTPリクエスト(get_court_link) : {http_req_num} 回')
            court_http_req_num = http_req_num
            #done, not_done = wait(_days_resp, timeout=30, return_when='FIRST_EXCEPTION')
            #exit()
            #await loop.run_until_complete(asyncio.gather(*_days_resp))
            court_htmls = await asyncio.gather(*_days_tasks)
            print(f'coroutine session end: ===========')
            #exit()
    return court_htmls, http_req_num
        # 完了したHTTPリクエスト結果を解析して、リンクを取得し、URLリンクリストを作成する
        #for _resp in as_completed(_days_resp):
            #for _resp in await asyncio.gather(*_days_tasks):
                # 空きコートのリンクを取得する
                #if bool(_resp.done()):
                #( _res, _day ) = ( _resp.result(timeout=10)[0], _resp.result(timeout=10)[1] )
                #( _res, _day ) = ( _resp[0], _resp[1] )
                #court_link_list = get_court(res, cfg, _day, th_lock_urls)
                #get_court(_res, cfg, _day, th_lock_urls)
            #    await get_court(_resp[2], cfg, _resp[0], async_lock_urls, court_link_list)
                #print(reserves_list[f'{date_string}'])
            #print(json.dumps(court_link_list, indent=2))
            #exit()
    #  with ThreadPoolExecutor(max_workers=4) as executor_secound:
    #     print(f'=== starting to get empty reserve request ===')
    #     _court_resp = []
    #     for _day in court_link_list:
    #         # 空き予約リストを初期化する
    #         reserves_list[_day] = {}
    #         for _link in court_link_list[_day]:
    #             # 指定年月とリンクを取得する
    #             #_day = day_link[0]
    #             #link = day_link[1]
    #             # 行頭の ./ykr31103,aspx を削除する
    #             search_url = cfg['court_search_url'] + re.sub('^\.\/ykr31103\.aspx', '', _link)
    #             #print(search_url)
    #             # ファイル名として保存するエンティティ名を生成する
    #             name = md5(search_url.encode('utf-8')).hexdigest()
    #             _entity = f'{_day}_{name}'
    #             http_req_num += 1
    #             # 指定年月日の空きコートリンクのGETリクエストを送信する
    #             #res_court = get_request_retry(_entity_string, search_url, headers_court, cookies)
    #             _court_resp.append(executor_secound.submit(get_request_retry, _day, _entity, search_url, headers_court, cookies))
    #             print(f'regist reserves : {_day} / {_link}')
    #     print(f'=== finished to get empty reserve request.===')
    #     reserve_http_req_num = http_req_num - court_http_req_num
    #     print(f'HTTPリクエスト(get_reserve) : {reserve_http_req_num} 回')
    #     #exit() 
    #     for resp in as_completed(_court_resp):
    #         # マルチスレッドのジョブ結果を格納したものを取り出す
    #         ( res_court, _day ) = ( resp.result()[0], resp.result()[1] )
    #         # 指定年月日のキーがない場合は空き予約リストを初期化する
    #         #if '{_day}' not in reserves_list:
    #         #    print(f'initialize : reserves_list[{_day}]')
    #         #    reserves_list[_day] = {}
    #         #else:
    #         #    print(f'{reserves_list}')
    #         #print(f'Response: {res_court}')
    #         # 指定年月日の時間帯別空きコートのリストを作成する
    #         reserves_list = get_empty_time(res_court, cfg, _day, reserves_list, th_lock_reserves)
    #     #done, not_done = wait(_court_resp)
    # #retrun court_link_list
    # #print(reserves_list)
    #print(f'call get_empty_reserves end: ##############')
    #return court_link_list, http_req_num


# 非同期IOのHTTPリクエストをする
@reserve_tools.elapsed_time
async def aio_get_request_retry(*args, **kwargs):
    """
    並行処理のために外に出して、ステータスコード200以外なら再試行する
    """
    # 非同期排他制御をする
    lock = asyncio.Lock()
    session = args[0]
    _day = args[1]
    _entity = args[2]
    _search_url = args[3]
    headers = args[4]
    cookies = args[5]
    #cfg = args[6]
    #th_lock_urls = args[7]
    #async_lock_urls = args[7]
    #court_link_list = args[8]
    #court_htmls = args[7]
    #_html = ''
    print(f'call aio_get_request_retry {_entity} start: ##########')
    print(f'task count: {len(asyncio.all_tasks())}')
    async with session.get(_search_url, headers=headers, cookies=cookies) as res:
        async with lock:
        #_html = await res.text()
        # 日付空き予約ページか、コート別日付空き予約ページかをURLから区別し、HTML処理を呼び出す
        #f f'/cu/ykr132241/app/ykr30000/ykr31101.aspx' in _search_url:
            #await get_court(_html, cfg, _day, async_lock_urls)
        #    get_court(await res.text(), cfg, _day, async_lock_urls, court_link_list)
        #else:
        #    get_empty_time(await res.text(), cfg, _day, th_lock_reserves)
            return _day, _entity, await res.text()


# 非同期IOのHTTPリクエストをする
@reserve_tools.elapsed_time
async def org_aio_get_request_retry(*args, **kwargs):
    """
    並行処理のために外に出して、ステータスコード200以外なら再試行する
    """
    # 非同期排他制御をする
    lock = asyncio.Lock()
    session = args[0]
    _day = args[1]
    _entity = args[2]
    _search_url = args[3]
    headers = args[4]
    cookies = args[5]
    cfg = args[6]
    #th_lock_urls = args[7]
    #async_lock_urls = args[7]
    #th_lock_reserves = args[8]
    court_htmls = args[7]
    _html = ''
    print(f'call aio_get_request_retry {_entity} start: ##########')
    print(f'task count: {len(asyncio.all_tasks())}')
    try:
        # ステータスコード200以外は再試行を3回する
        max_retry = 3
        _retry = 0
        _res = await session.get(_search_url, headers=headers, cookies=cookies)
        while _retry < max_retry:
            if _res.status != 200:
                await asyncio.sleep(1)
                #_res = await session.get(_search_url, headers=headers, cookies=cookies)
                _res = await session.get(_search_url, headers=headers, cookies=cookies)
                _retry += 1
                print(f'get request faild count: {_retry}')
            else:
                #print(f'success get request: {_entity}')
                async with lock: 
                    _html = await _res.text()
                    # 日付空き予約ページか、コート別日付空き予約ページかをURLから区別し、HTML処理を呼び出す
                    if f'/cu/ykr132241/app/ykr30000/ykr31101.aspx' in _search_url:
                        #await get_court(_html, cfg, _day, async_lock_urls)
                        court_htmls.append(_html)
                    else:
                        get_empty_time(_html, cfg, _day, th_lock_reserves)
                break
        else:
            print(f'=========>> faild get request: {_entity}')
            # 空のHTMLレスポンスを返す
            _res = None
    except ClientError as e:
        print(f'=========>> happend client_error: {_entity} {e}')
        # 空のHTMLレスポンスを返す
        _res = None
    #else:
        #print(f'{res.headers}')
        #print(dir(res))
        # デバッグ用としてhtmlファイルとして保存する
        #_file_name = f'result_{_entity}.html'
        #print(_file_name)
        #_file = reserve_tools.save_html_to_filename(res, _file_name)
    finally:
        #print(f'GET HTTP REQUESTED: {_day} {_entity} {_search_url}')
        #print(type(_res))
        #print(dir(_res))
        #print(f'Response: {_res}')
        #print(f'HTML Body: {_html}')
        print(f'call aio_get_request_retry {_entity} end: ##########')
        #return _day, _entity, await _res.text()
        return _day, _entity, _html


# 指定日で検索したHTML本体を get_court に渡す
def get_court_links(cfg, responses, court_link_list):
    for _response in responses:
        print(f'analyze_html: {_response[1]}')
        court_link = get_court(cfg, _response[2], court_link_list)
    return court_link_list

#@reserve_tools.elapsed_time
#async def get_court(response, cfg, day, async_lock_urls):
#async def get_court(response, cfg, day, async_lock_urls, court_link_list):
def get_court(response, cfg, day, court_link_list):
    """
    年月日指定の空き予約検索結果ページから空きコートのリンクを取得する
    空きコートリンクのリストは次のdict型となる
    court_link_list['day'] = [ url0, url1, ... ]
    """
    # 非同期排他制御をする
    #lock = asyncio.Lock()
    #async with lock:
    # 空き予約結果ページを検索したときの指定年月日を設定する
    _day = day
    #print(f'analyze get_court : {_day}')
    # 空き予約リストを初期化する
    #court_link_list = []
    # 登録済みリンクを初期化する
    registerd_link = ''
    # 空きコート名のリンクを取得する
    ## 空のレスポンスオブジェクトの場合はHTTPリクエストが失敗しているので、解析しないで returnを返す
    #print(type(response))
    #print(dir(response))
    if response is None:
        return None
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
            #print(f'>>>>>>>>')
            #print(f'finding day: {_day}')
            #print(atag['href'])
            #print(f'>>>>>>>>')
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
                            #court_link_list.append([ day, atag['href'] ])
                            #print(f'########')
                            #print(f'regist url link : {_day}')
                            #print(atag['href'])
                            #print(atag['href'][82:90])
                            #print(f'========')
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
def get_empty_time(response, cfg, day, reserves_list, th_lock_reserves):
    """
    空き予約の時間帯を取得する
    """
    #print(reserves_list['day'])
    print(f'get_empty_time: {day}')
    # レスポンスオブジェクトをHTML化する
    ## 空のレスポンスオブジェクトの場合はHTTPリクエストが失敗しているので、解析しないで returnを返す
    #print(type(response))
    #print(dir(response))
    if response.status != 200:
        return None
    ## レスポンスオブジェクトをHTML化する
    html = response.text
    soup = BeautifulSoup(html, features='html.parser')
    # コート名を取得する
    court_table = soup.find(class_='table-vertical table-timeselect-sisetu')
    court_string = court_table.tr.td.next_sibling.next_sibling.stripped_strings
    for name in court_string:
        court_name = re.sub('庭球場（奈良原以外）\s+', '', name)
        court_name = re.sub('^奈良原公園庭球場\s+', '', court_name)
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
        reserve = re.sub('～(\d):', r'～0\1:', reserve)
        # 空き予約の除外時間帯かを確認し、除外時間帯以外を登録する
        _match_count = 0
        _exclude_time_count = len(cfg['exclude_times'])
        for _exclude_time in cfg['exclude_times']:
            if reserve == _exclude_time:
                print(f'matched exclude time: {court_name}  {reserve}')
                break
            else:
                # 除外時間帯にマッチしなかったので、カウントアップする
                _match_count += 1
                # マッチしなかった回数がリスト回数以上になれば登録する
                if _match_count >= _exclude_time_count:
                    # 空き予約リストに追加する
                    #reserves_list[f'{day}'].setdefault(reserve, []).append(court_name)
                    #print(f'regist reserve : {_day} {reserve} : {court_name}')
                    th_lock_reserves.regist_reserve(day, reserve, court_name)
    print(reserves_list)
    return reserves_list


## 検索結果のHTMLボディを排他制御で追加する
class AsyncioLockHtmls:
    """
    スレッド処理に対応するため、排他制御で検索対象URLリストの登録を行う
    """
    lock = asyncio.Lock()
    def __init__(self):
        self.court_htmls = []
    def add_url(self, html):
        with self.lock:
            #print(f'get url : {day} {url}')
            #print(f'########')
            self.court_htmls.append(html)

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
class ThreadLockUrlsList:
    """
    スレッド処理に対応するため、排他制御で検索対象URLリストの登録を行う
    """
    lock = threading.RLock()
    def __init__(self):
        self.court_link_list = {}
    def add_url(self, day, url):
        with self.lock:
            #print(f'get url : {day} {url}')
            #print(f'########')
            self.court_link_list.setdefault(day, []).append(url)

## 空き予約リストへの登録を排他制御する
class ThreadLockReservesList:
    """
    スレッド処理に対応するため、排他制御で空き予約リストへの登録を行う
    """
    lock = threading.RLock()
    def __init__(self):
        self.reserves_list = {}
    def regist_reserve(self, day, timestring, court_name):
        with self.lock:
            print(f'regist reserve : {day} {timestring} : {court_name}')
            #if '{day}' not in self.reserves_list:
            #    print(f'initialize reserves_list[{day}].')
            #    self.reserves_list[day] = {}
            self.reserves_list[day].setdefault(timestring, []).append(court_name)

# url, responseを受け取る任意のコルーチン
#async def coroutine(url, response):
#    return url, response.status, await response.text()

# コートの空き予約を検索するためのリクエストオブジェクトのリストを作成する
def create_request_objs(cfg, date_list, cookies, form_data):
    """
    指定年月日のリストを引数として、その指定年月日の空き予約を検索する
    """
    # リクエストパラメータのリストを初期化する
    request_objs = []
    print(f'call get_empty_reserves start: ##############')
    # リファレンスヘッダーを定義する。これがないと検索できない
    headers_day = { 'Referer': cfg['day_search_url'] }
    headers_court = { 'Referer': cfg['court_search_url'] }
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
            # リクエストパラメータを追加する
            request_objs.append([_day, _entity, search_url, headers_day, cookies])
    #print(json.dumps(request_objs, indent=2))
    return request_objs

@reserve_tools.elapsed_time
async def get_request_fetch(session, url, coro):
    """
    HTTPリソースからデータを取得しコルーチンを呼び出す
    """
    async with async_timeout.timeout(10):
        try:
            response = await session.get(url[2], headers=url[3], cookies=url[4])
        except ClientError as e:
            print(e)
            response = None
    return await coro(url, response)

@reserve_tools.elapsed_time
async def bound_get_request_fetch(semaphore, url, session, coro):
    """
    並列処理数を制限しながらHTTPリソースを取得するコルーチン
    """
    async with semaphore:
        return await get_request_fetch(session, url, coro)

@reserve_tools.elapsed_time
async def get_request_courts(urls, coro, http_req_num, limit=1):
    """
    並列処理数を制限しながらHTTPリソースを取得するコルーチン
    """
    tasks = []
    semaphore = asyncio.Semaphore(limit)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for url in urls:
            http_req_num += 1
            task = asyncio.ensure_future(bound_get_request_fetch(semaphore, url, session, coro))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)
        return responses, http_req_num


# メインルーチン
def main(urls, coro, limit=4):
    """
    メインルーチン
    """
    # 実行時間を測定する
    start = time.time()

    # url, responseを受け取る任意のコルーチン
    #async def coroutine(url, response):
    #    return url, response.status, await response.text()
    
    # HTTPリクエスト数
    http_req_num = 0
    # LINEのメッセージサイズの上限
    #line_max_message_size = 1000
    # ファイル
    #path_html = 'temp_result.html'
    # 祝日の初期化
    #public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 入力データの辞書の初期化
    #input_data = {}
    # 空き予約の辞書の初期化
    #reserve_name_list = {}
    #print(f'[reserve_name_list]')
    #print(f'{reserve_name_list}')
    #print(type(reserve_name_list))
    #print(dir(reserve_name_list))
    # 送信メッセージリストの初期化
    message_bodies = []
    # aiohttpのセッティング
    ## 同時接続数の設定
    con_limit = 4
    conn = aiohttp.TCPConnector(limit=con_limit)
    # 処理の開始
    # 空き予約を取得するためのURLリストの初期化
    #th_lock_urls = ThreadLockUrlsList()
    #court_link_list = th_lock_urls.court_link_list
    #async_htmls = AsyncioLockHtmls()
    #court_htmls = async_htmls.court_htmls
    #async_lock_urls = AsyncioLockUrlsList()
    #court_link_list = async_lock_urls.court_link_list
    #court_htmls = []
    #court_link_list = {}
    # 空き予約リストの初期化
    #reserves_list = {}
    th_lock_reserves = ThreadLockReservesList()
    reserves_list = th_lock_reserves.reserves_list

    # 非同期IO処理のaiohttpのためにイベントループを作成する
    loop = asyncio.get_event_loop()
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    #reserve_tools.set_public_holiday('public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    #cfg = reserve_tools.read_json_cfg('cfg2.json')
    # 検索リストを作成する
    #target_months_list = reserve_tools.create_month_list(cfg)
    #datetime_list = create_datetime_list(target_months_list, public_holiday, cfg)
    #date_list = reserve_tools.create_date_list(target_months_list, public_holiday, cfg)
    # 空き予約ページにアクセスし、cookieを取得する
    #( cookies, form_data ) = get_cookie(cfg)
    # 空き予約検索を開始する
    ## 検索のためのリクエストオブジェクトを作成する
    #request_objs = create_request_objs(cfg, date_list)
    ( results, http_req_num ) = loop.run_until_complete(get_request_courts(urls, coro, http_req_num, limit))

    #print(json.dumps(court_link_list, indent=2))

    # デバッグ用(HTTPリクエスト回数を表示する)
    print(f'HTTP リクエスト数: {http_req_num} 回数')

    # 実行時間を表示する
    elapsed_time = time.time() - start
    print(f'main() duration time: {elapsed_time} sec')
    print(f'####################################')
    
    #exit()
    return results
    
if __name__ == '__main__':
    # 実行時間を測定する
    _start = time.time()

    @reserve_tools.elapsed_time
    async def coroutine(url, response):
        return url, response.status, await response.text()
    
    # 非同期ロック
    async_lock_urls = AsyncioLockUrlsList()
    court_link_list = async_lock_urls.court_link_list
    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    reserve_tools.set_public_holiday('public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = reserve_tools.read_json_cfg('cfg2.json')
    # 検索リストを作成する
    target_months_list = reserve_tools.create_month_list(cfg)
    #datetime_list = create_datetime_list(target_months_list, public_holiday, cfg)
    date_list = reserve_tools.create_date_list(target_months_list, public_holiday, cfg)
    # 空き予約ページにアクセスし、cookieを取得する
    ( cookies, form_data ) = get_cookie(cfg)
    
    # リファレンスヘッダーを定義する。これがないと検索できない
    headers_day = { 'Referer': cfg['day_search_url'] }
    headers_court = { 'Referer': cfg['court_search_url'] }

    urls = create_request_objs(cfg, date_list, cookies, form_data)

    #exit()
    results = main(urls=urls, coro=coroutine, limit=4)

    print(f'')
    print(f'#### Analyzed Link Start : ####')
    print(f'')

    for url, status, body in results:
        #print(url, status, body)
        get_court(body, cfg, url[0], court_link_list)
    
    print(f'')
    print(f'#### Analyzed Link End : ####')
    print(f'')

    print(json.dumps(court_link_list, indent=2))
    
    # 実行時間を表示する
    elapsed_time = time.time() - _start
    print(f'whole() duration time: {elapsed_time}')
