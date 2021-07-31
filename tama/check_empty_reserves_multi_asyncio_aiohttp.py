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
        reserve = re.sub('～(\d):', r'～0\1:', reserve)
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
    cfg = reserve_tools.read_json_cfg('cfg2.json')
    # 検索リストを作成する
    ## 検索対象月を取得する
    target_months_list = reserve_tools.create_month_list(cfg)
    ## 検索対象月リストと祝日リストから検索対象年月日リストを作成する
    date_list = reserve_tools.create_date_list(target_months_list, public_holiday, cfg)
    return cfg, date_list

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
    ( cfg, date_list ) = prepare()
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
    
    # LINEにメッセージを送信する
    postproc(reserves_list)

    # デバッグ用(HTTPリクエスト回数を表示する)
    print(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - _start
    print(f'whole() duration time: {elapsed_time} sec')
    
    exit()