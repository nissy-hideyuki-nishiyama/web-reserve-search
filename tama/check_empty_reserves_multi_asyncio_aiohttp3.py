# モジュールの読み込み
## HTMLクローラー関連
from aiohttp.http import RESPONSES
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

from requests.sessions import session

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
async def get_empty_reserves(cfg, date_list, reserves_list, court_link_list, cookies, http_req_num, th_lock_urls, th_lock_reserves, conn_limit, loop):
    """
    指定年月日のリストを引数として、その指定年月日の空き予約を検索する
    """
    #print(f'call get_empty_reserves start: ##############')
    # 同時実行するを制限するためにセマフォを導入し、同時実行数を制限する
    limit = conn_limit
    sem = asyncio.Semaphore(limit)
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
    # HTTPリクエストを送信する処理をasyncioで非同期処理にする
    # セマフォを獲得できたら、実行する
    async with sem:
        # 検索日を指定して、空き予約コート一覧ページを取得する
        #async with aiohttp.ClientSession(connector=conn) as session:
        async with aiohttp.ClientSession() as session:
            #print(f'coroutine session start: ===========')
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
                    # デバッグ用ファイル名として保存するエンティティ名を生成する
                    name = md5(search_url.encode('utf-8')).hexdigest()
                    _entity = f'{_day}_{name}'
                    # 指定年月日を指定した検索リクエストを送信する
                    #res = requests.get(search_url, headers=headers_day, cookies=cookies)
                    http_req_num += 1
                    _day_resp = await aio_get_request_retry(session, _day, _entity, search_url, headers_day, cookies, cfg, th_lock_urls, th_lock_reserves)
                    _days_resp.append(_day_resp)
                    #print(type(_day_resp))
                    #print(dir(_day_resp))
                    #print(_day_resp)
                    #print(f'task {_day}:{param_string} end: -----------')
            #print(json.dumps(_days_resp, indent=2))
            court_http_req_num = http_req_num
            #print(f'=== finished to get court link request.===')
            #print(json.dumps(court_link_list, indent=2))
            #print(f'coroutine session end: ===========')
            #print(type(_days_resp))
            #print(dir(_days_resp))
            #print(_days_resp)
            #print(vars(_days_resp[0]))
            print(f'HTTPリクエスト(get_court_link) : {http_req_num} 回')
            #exit()
            # 完了したHTTPリクエスト結果を解析して、リンクを取得し、URLリンクリストを作成する
            #for _resp in as_completed(_days_resp):
            #for _resp in await asyncio.gather(*_days_resp):
            for _day in court_link_list:
                for link in court_link_list[_day]:
                    # 行頭の ./ykr31103,aspx を削除する
                    #search_url = cfg['court_search_url'] + re.sub('^\.\/ykr31103\.aspx', '', link)
                    search_url = cfg['court_search_url'] + re.sub('^\.\/ykr31103\.aspx', '', link)
                    #print(search_url)
                    # ファイル名として保存するエンティティ名を生成する
                    name = md5(search_url.encode('utf-8')).hexdigest()
                    _entity_string = f'{_day}_{name}'
                    # 指定年月日の空きコートリンクのGETリクエストを送信する
                    http_req_num += 1
                    _link_resp = await aio_get_request_retry(session, _day, _entity_string, search_url, headers_court, cookies, cfg, th_lock_urls, th_lock_reserves)
            # json,dumpsでは日本語が化けるので、ensure_ascii=Falseを追加する
            print(json.dumps(reserves_list, indent=2, ensure_ascii=False))
            #exit()
    #print(f'call get_empty_reserves end: ##############')
    return reserves_list, http_req_num


# 非同期IOのHTTPリクエストをする
@reserve_tools.elapsed_time
async def aio_get_request_retry(*args, **kwargs):
    """
    並行処理のために外に出して、ステータスコード200以外なら再試行する
    """
    session = args[0]
    _day = args[1]
    _entity = args[2]
    _search_url = args[3]
    headers = args[4]
    cookies = args[5]
    cfg = args[6]
    th_lock_urls = args[7]
    th_lock_reserves = args[8]
    _html = ''
    #print(f'call aio_get_request_retry {_entity} start: ##########')
    try:
        _res = await session.get(_search_url, headers=headers, cookies=cookies)
        # ステータスコード200以外は再試行を3回する
        max_retry = 3
        _retry = 0
        while _retry < max_retry:
            if _res.status != 200:
                asyncio.sleep(1)
                #_res = await session.get(_search_url, headers=headers, cookies=cookies)
                _res = session.get(_search_url, headers=headers, cookies=cookies)
                _retry += 1
                print(f'get request faild count: {_retry}')
            else:
                #print(f'success get request: {_entity}')
                _html = await _res.text()
                #print(f'{_search_url}')
                #print(f'{_html}')
                # 日付空き予約ページか、コート別日付空き予約ページかをURLから区別し、HTML処理を呼び出す
                if f'/cu/ykr132241/app/ykr30000/ykr31101.aspx' in _search_url:
                    get_court(_html, cfg, _day, th_lock_urls)
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
        #print(f'call aio_get_request_retry {_entity} end: ##########')
        #return _day, _entity, await _res.text()
        return _day, _entity, _html


# 指定した年月日の空き予約結果ページから空き予約のコートを取得する
def get_court(response, cfg, day, th_lock_urls):
    """
    年月日指定の空き予約検索結果ページから空きコートのリンクを取得する
    空きコートリンクのリストは次のdict型となる
    court_link_list['day'] = [ url0, url1, ... ]
    """
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
    #else:
    #    print(response)
    ## レスポンスオブジェクトをHTML化する
    #html = str(response)
    #soup = BeautifulSoup(html, features='html.parser')
    #html = str(response)
    # HTML解析をする
    soup = BeautifulSoup(response, features='html.parser')
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
                            th_lock_urls.add_url(_link_day, atag['href'])
                            # 登録済みリンクとして代入する。これによって二重登録を防止する
                            registerd_link = atag['href']
    # 検索リストを表示する
    #print(court_link_list)
    # 終わる
    #return court_link_list
    return None

# 指定した年月日のコート空き予約ページから空き予約の時間帯を取得する
def get_empty_time(response, cfg, day, th_lock_reserves):
    """
    空き予約の時間帯を取得する
    """
    #print(f'get_empty_time: {day}')
    # レスポンスオブジェクトをHTML化する
    ## 空のレスポンスオブジェクトの場合はHTTPリクエストが失敗しているので、解析しないで returnを返す
    #print(type(response))
    #print(dir(response))
    if response is None:
        return None
    #else:
    #    print(response)
    # HTML解析を開始する
    soup = BeautifulSoup(response, features='html.parser')
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
                #print(f'matched exclude time: {court_name}  {reserve}')
                break
            else:
                # 除外時間帯にマッチしなかったので、カウントアップする
                _match_count += 1
                # マッチしなかった回数がリスト回数以上になれば登録する
                if _match_count >= _exclude_time_count:
                    # 空き予約リストに追加する
                    #reserves_list[f'{day}'].setdefault(reserve, []).append(court_name)
                    #print(f'regist reserve : {day} {reserve} : {court_name}')
                    th_lock_reserves.regist_reserve(day, reserve, court_name)
    #print(reserves_list)
    #return reserves_list
    #print(th_lock_reserves)
    return None


## 空き予約時間帯を検索するURLリストへの登録を排他制御する
class ThreadLockUrlList:
    """
    スレッド処理に対応するため、排他制御で検索対象URLリストの登録を行う
    """
    lock = threading.RLock()
    def __init__(self):
        self.court_link_list = {}
    def add_url(self, day, url):
        with self.lock:
            #print(f'get url : {day} {url}')
            self.court_link_list.setdefault(day, []).append(url)
            #print(json.dumps(self.court_link_list, indent=2))
            #print(f'########')


## 空き予約リストへの登録を排他制御する
class ThreadLockReservesList:
    """
    スレッド処理に対応するため、排他制御で空き予約リストへの登録を行う
    """
    rlock = threading.RLock()
    def __init__(self):
        self.reserves_list = {}
    def regist_reserve(self, day, timestring, court_name):
        with self.rlock:
            #print(f'regist reserve in th_lock : {day} {timestring} : {court_name}')
            if f'{day}' not in self.reserves_list:
                #print(f'initialize reserves_list[{day}].')
                self.reserves_list[f'{day}'] = {}
            self.reserves_list[f'{day}'].setdefault(timestring, []).append(court_name)
            #self.reserves_list[f'{day}'][f'{timestring}'].append(f'{court_name}')
            #print(json.dumps(self.reserves_list, indent=2))

# url, responseを受け取る任意のコルーチン
#async def coroutine(url, response):
#    return url, response.status, await response.text

# メインルーチン
@reserve_tools.elapsed_time
def main():
    """
    メインルーチン
    """
    # 実行時間を測定する
    start = time.time()

    # HTTPリクエスト数
    http_req_num = 0
    # LINEのメッセージサイズの上限
    #line_max_message_size = 1000
    # ファイル
    #path_html = 'temp_result.html'
    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
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
    conn_limit = 4
    #conn = aiohttp.TCPConnector(limit=conn_limit)
    # 処理の開始
    # 空き予約を取得するためのURLリストの初期化
    th_lock_urls = ThreadLockUrlList()
    court_link_list = th_lock_urls.court_link_list
    # 空き予約リストの初期化
    #reserves_list = {}
    th_lock_reserves = ThreadLockReservesList()
    reserves_list = th_lock_reserves.reserves_list
    #print()
    #print(f'[reserves_list]')
    #print(f'{reserves_list}')
    #print(type(reserves_list))
    #print(dir(reserves_list))
    #exit()
    # 非同期IO処理のaiohttpのためにイベントループを作成する
    loop = asyncio.get_event_loop()
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
    # 空き予約検索を開始する
    ## 指定年月日を指定して、空きコートのリンクを取得する
    ( reserves_list, http_req_num ) = loop.run_until_complete(get_empty_reserves(cfg, date_list, reserves_list, court_link_list, cookies, http_req_num, th_lock_urls, th_lock_reserves, conn_limit, loop))

    # LINEにメッセージを送信する
    ## メッセージ本体を作成する
    #reserve_tools.create_message_body(reserves_list, message_bodies, cfg)
    ## LINEに空き予約情報を送信する
    #reserve_tools.send_line_notify(message_bodies, cfg)

    # デバッグ用(HTTPリクエスト回数を表示する)
    print(f'HTTP リクエスト数: {http_req_num} 回数')

    # 実行時間を表示する
    elapsed_time = time.time() - start
    print(f'main() duration time: {elapsed_time}')
    
    exit()
    
if __name__ == '__main__':
    main()

