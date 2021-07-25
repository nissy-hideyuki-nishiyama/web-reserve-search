# 変更点
# - 利用日検索ページに接続し、form_dataを取得するところから、非同期処理とする
# うまくいっていないところ
# - システムエラーが頻発し、空き予約検索結果が取得できない

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

# カレンダー関連
from time import sleep
import math
import datetime
import calendar
import time

# ファイルIO、ディレクトリ関連
import os

# HTML解析関連
from bs4 import BeautifulSoup
import re


# JSONファイルの取り扱い
import json

# 非同期処理モジュール
import asyncio
import aiohttp
import async_timeout
from aiohttp import ClientError

# URLの'/'が問題になるためハッシュ化する
from hashlib import md5
from pathlib import Path

# ツールライブラリを読み込む
import reserve_tools

# 追加モジュール
# 配列処理、データ構造
#import numpy as np

# 検索結果ページの表示件数
page_unit = 5
#page = 0
#is_empty = 'False'

# 年月日時分の入力リストを作成する
#def create_datetime_list(target_months_list, selected_weekdays):
def create_datetime_list(target_months_list, public_holiday, cfg):
    """ 入力データとなる年月日日時のリストを2次元配列で作成する
    時分は固定値リストを使う
    時分： [ [ 9, 12, 14, 16. 18 ], [ 00. 30 ] ]
    """
    # 希望曜日のリストを作成する
    #selected_weekdays = cfg['want_weekdays']
    # 入力リストとして2次元配列を作成する
    datetime_list = []
    # 時分リストを初期化する
    #time_list = [ 9, 12, 14, 16, 18 ]
    time_list = cfg['target_hours']
    for _month in target_months_list:
        # 年越し確認
        _year = reserve_tools.check_new_year(_month)
        # 対象月の日付リストを作成する
        target_days_list = reserve_tools.create_day_list(_month, public_holiday, cfg)
        # 日付リストが空の場合は次の月の処理に移る
        if not target_days_list:
            continue
        # 入力リストに代入する
        for _day in target_days_list:
            for _hour in time_list:
                # 開始時刻と終了時刻を作成する
                _shour = _hour
                # 開始時刻が9時の場合は+3、それ以外は2を足す
                if _hour == 9:
                    _ehour = _hour + 3
                else:
                    _ehour = _hour + 2
                # 18時の場合はminは30とする
                if _hour == 18:
                    _min = 30
                else:
                    _min = 0
                # 入力パラメータとなる配列を作る
                _input_datetime_list = [ _year, _month, _day, _shour, _min, _ehour, _min ]
                # 2次元配列として、要素を追加する
                datetime_list.append(_input_datetime_list)
    print(datetime_list)
    return datetime_list

# クローラー
## cookieを取得するため、トップページにアクセスする
def get_cookie_request(cfg):
    """
    cookieを取得する
    """
    # セッションを開始する
    session = requests.session()
    response = session.get(cfg['first_url'])
    # cookie情報を初期化し、次回以降のリクエストでrequestsモジュールの渡せる形に整形する
    cookies = {}
    cookies[cfg['cookie_name_01']] = session.cookies.get(cfg['cookie_name_01'])
    cookies[cfg['cookie_name_02']] = session.cookies.get(cfg['cookie_name_02'])
    #print(cookies)
    return cookies , response

## 施設の空き状況検索の利用日時からのリンクをクリックして、検索画面に移動する
def go_to_search_date_menu(cfg, headers, cookies):
    """
    施設の空き状況検索の利用日時からのリンクをクリックして、検索画面に移動する
    """
    res = requests.get(cfg['search_url'], headers=headers, cookies=cookies)
    #print(res.text)
    return res

## フォームデータを取得する
def get_formdata(response):
    """
    ページからフォームデータを取得する
    """
    # フォームデータ(dict型)を初期化する
    _form_data = {}
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = reserve_tools.save_html_file(response)
    #print(f'save file: {_file_name}')
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    _form = soup.find_all('form')[1]
    # フォームデータを取得する
    _form_data = {}
    _form_data['layoutChildBody:childForm:dataSearchItemsSave'] = _form.find('input', id="dataSearchItemsSave")['value']
    _form_data['layoutChildBody:childForm:areaItemsSave'] = _form.find('input', id="areaItemsSave")['value']
    _form_data['layoutChildBody:childForm:communityItemsSave'] = _form.find('input', id="communityItemsSave")['value']
    _form_data['layoutChildBody:childForm:productcode4'] = _form.find('input', id="productcode4")['value']
    _form_data['layoutChildBody:childForm:eyear'] = _form.find('input', id="eyear")['value']
    _form_data['layoutChildBody:childForm/view/user/rsvDateSearch.html'] = _form.find_all('input')[-1]['value']
    # 最後の script ヘッダを抽出する
    _te = soup.find_all('script')[-1]
    # te-conditions 部分を抽出する
    _te_value = re.search('value=\'.+\'', _te.contents[0])
    # value=の文字列が含まれるので、これを削除してフォームデータに代入する
    _form_data['te-conditions'] = _te_value.group()[7:-1]
    # フォームデータを返す
    return _form_data

## フォームデータを取得する
def get_formdata_2(response, _form_data):
    """
    ページからフォームデータを取得する
    """
    # フォームデータ(dict型)を初期化する
    #_form_data = {}
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = reserve_tools.save_html_file(response)
    #print(f'save file: {_file_name}')
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    _form = soup.find_all('form')[1]
    # フォームデータにKey&Valueを代入する
    _form_data['layoutChildBody:childForm:dataSearchItemsSave'] = _form.find('input', id="dataSearchItemsSave")['value']
    _form_data['layoutChildBody:childForm:areaItemsSave'] = _form.find('input', id="areaItemsSave")['value']
    _form_data['layoutChildBody:childForm:communityItemsSave'] = _form.find('input', id="communityItemsSave")['value']
    _form_data['layoutChildBody:childForm:productcode4'] = _form.find('input', id="productcode4")['value']
    _form_data['layoutChildBody:childForm:eyear'] = _form.find('input', id="eyear")['value']
    _form_data['layoutChildBody:childForm/view/user/rsvDateSearch.html'] = _form.find_all('input')[-1]['value']
    # 最後の script ヘッダを抽出する
    _te = soup.find_all('script')[-1]
    # te-conditions 部分を抽出する
    _te_value = re.search('value=\'.+\'', _te.contents[0])
    # value=の文字列が含まれるので、これを削除してフォームデータに代入する
    _form_data['te-conditions'] = _te_value.group()[7:-1]
    # フォームデータを返す
    return _form_data



########################
# 非同期処理ブロック 開始
@reserve_tools.elapsed_time
#async def get_request_fetch(session, url, coro):
async def post_request_fetch(cfg, cookies, headers, _form_data, session, coro):
    """
    HTTPリソースからデータを取得しコルーチンを呼び出す
    """
    # 利用日時検索ページにアクセスし、form_dataを取得する
    form_response = go_to_search_date_menu(cfg, headers, cookies)
    _form_data = get_formdata_2(form_response, _form_data)
    # aiohttpのFormDataフォーマットに置き換える
    aio_form_data = aiohttp.FormData()
    #print(json.dumps(_form_data, indent=2))
    for key, value in _form_data.items():
        aio_form_data.add_field(key, value)
    async with async_timeout.timeout(10):
        try:
            response = await session.post(cfg['search_url'], headers=headers, cookies=cookies, data=aio_form_data)
        except ClientError as e:
            print(e)
            response = None
    return await coro(cfg, cookies, headers, _form_data, response)

@reserve_tools.elapsed_time
#async def bound_get_request_fetch(semaphore, url, session, coro):
async def bound_post_request_fetch(cfg, cookies, headers, _form_data, semaphore, session, coro):
    """
    並列処理数を制限しながらHTTPリソースを取得するコルーチン
    """
    async with semaphore:
        return await post_request_fetch(cfg, cookies, headers, _form_data, session, coro)

@reserve_tools.elapsed_time
#async def get_request_courts(urls, coro, http_req_num, limit=1):
async def post_request_from_datesearch(cfg, cookies, datetime_list, reserves_list, coro, http_req_num, limit=1):
    """
    並列処理数を制限しながらHTTPリソースを取得するコルーチン
    """
    # form_dataの初期化
    form_data = {}
    # 非同期タスクリストの初期化
    tasks = []
    # 同時実行数の設定
    semaphore = asyncio.Semaphore(limit)
    # 直前のリクエストURLからRefererを含んだヘッダーを生成する
    headers = {
        'Origin': cfg['origin_url'],
        'Referer': cfg['search_url'],
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
    }
    # 利用目的を取得し、フォームデータに代入する
    form_data['layoutChildBody:childForm:purpose'] = cfg['selected_purpose']
    # 検索対象地域を取得、フォームデータに代入する
    #for _area in cfg['selected_areas']:
    #    form_data['layoutChildBody:childForm:area'] = cfg['selected_areas']
    # rsvDateSearchページの検索ボタンの値を代入する
    form_data['layoutChildBody:childForm:doDateSearch'] = '上記の内容で検索する'
    # 非同期処理タスクの作成
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for _datetime in datetime_list:
            # フォームデータの検索日時データを生成する。
            form_data['layoutChildBody:childForm:year'] = _datetime[0]
            form_data['layoutChildBody:childForm:month'] = _datetime[1]
            form_data['layoutChildBody:childForm:day'] = _datetime[2]
            form_data['layoutChildBody:childForm:sHour'] = _datetime[3]
            form_data['layoutChildBody:childForm:sMinute'] = _datetime[4]
            form_data['layoutChildBody:childForm:eHour'] = _datetime[5]
            form_data['layoutChildBody:childForm:eMinute'] = _datetime[6]
            #　関数の引数とするために新しい辞書オブジェクトとして生成する
            _form_data = dict(form_data)
            # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
            #params = urllib.parse.urlencode(form_data)
            # フォームデータを使って、空き予約を検索する
            #res = requests.post(cfg['search_url'], headers=headers, cookies=cookies, data=params)
            http_req_num += 1
            task = asyncio.ensure_future(bound_post_request_fetch(cfg, cookies, headers, _form_data, semaphore, session, coro))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)
        return responses, http_req_num

# 非同期処理ブロック 終了
########################


## 利用日時ページに検索データを入力して検索する
@reserve_tools.elapsed_time
def search_empty_reserves_from_datesearch(cfg, cookies, form_data, datetime_list, reserves_list):
    """
    利用日時と利用目的、地域を入力して空き予約を検索する
    """
    # 直前のリクエストURLからRefererを含んだヘッダーを生成する
    headers = {
        'Origin': cfg['origin_url'],
        'Referer': cfg['search_url'],
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
    }
    # 利用目的を取得し、フォームデータに代入する
    form_data['layoutChildBody:childForm:purpose'] = cfg['selected_purpose']
    # 検索対象地域を取得、フォームデータに代入する
    #for _area in cfg['selected_areas']:
    #    form_data['layoutChildBody:childForm:area'] = cfg['selected_areas']
    # rsvDateSearchページの検索ボタンの値を代入する
    form_data['layoutChildBody:childForm:doDateSearch'] = '上記の内容で検索する'
    # 空き状況カレンダーの日付リンク(doChangeDate, rsvEmptyStateページ)の値を代入する
    for _datetime in datetime_list:
        # フォームデータの検索日時データを生成する
        form_data['layoutChildBody:childForm:year'] = _datetime[0]
        form_data['layoutChildBody:childForm:month'] = _datetime[1]
        form_data['layoutChildBody:childForm:day'] = _datetime[2]
        form_data['layoutChildBody:childForm:sHour'] = _datetime[3]
        form_data['layoutChildBody:childForm:sMinute'] = _datetime[4]
        form_data['layoutChildBody:childForm:eHour'] = _datetime[5]
        form_data['layoutChildBody:childForm:eMinute'] = _datetime[6]
        #print(form_data)
        # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
        params = urllib.parse.urlencode(form_data)
        # フォームデータを使って、空き予約を検索する
        res = requests.post(cfg['search_url'], headers=headers, cookies=cookies, data=params)
        # デバッグ用としてhtmlファイルとして保存する
        #_datetime_string = str(_datetime[0]) + str(_datetime[1]).zfill(2) + str(_datetime[2]).zfill(2) + str(_datetime[3]).zfill(2) + str(_datetime[4]).zfill(2)
        #_file_name = f'result_{_datetime_string}.html'
        #print(_file_name)
        #_file = reserve_tools.save_html_to_filename(res, _file_name)
        # HTML解析を実行して、発見した空き予約を予約リストに追加するする
        analyze_html(cfg, cookies, _datetime, res, reserves_list)
    # 空き予約リストを返す
    return reserves_list


## 利用日時ページに検索データを入力して検索する
@reserve_tools.elapsed_time
def search_empty_reserves_from_emptystate(cfg, cookies, datetime, form_data, res, reserves_list):
    """
    利用日時と利用目的、地域を入力して空き予約を検索する
    """
    # リダイレクトされているか確認する
    # リダイレクトされている場合はリダイレクト元のレスポンスヘッダのLocationを取得する
    if res.history:
        _referer = res.history[-1].headers['Location']
    else:
        _referer = cfg['empty_state_url']
    print(f'referer: {_referer}')
    # 直前のリクエストURLからRefererを含んだヘッダーを生成する
    headers = {
        'Origin': cfg['origin_url'],
        'Referer': _referer,
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
    }
    # フォームデータを変更する
    # doPagerの値をsubmitに変更する
    form_data['layoutChildBody:childForm:doPager'] = 'submit'
    # 開始時間と終了時間を追加する
    form_data['layoutChildBody:childForm:stime'] = str(datetime[3]).zfill(2) + str(datetime[4]).zfill(2)
    form_data['layoutChildBody:childForm:etime'] = str(datetime[5]).zfill(2) + str(datetime[6]).zfill(2)
    # doChangeDateを削除する
    #del form_data['layoutChildBody:childForm:doChangeDate']
    #print(form_data)
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、空き予約を検索する
    res = requests.post(cfg['empty_state_url'], headers=headers, cookies=cookies, data=params)
    # デバッグ用としてhtmlファイルとして保存する
    #_datetime_string = str(datetime[0]) + str(datetime[1]).zfill(2) + str(datetime[2]).zfill(2) + str(datetime[3]).zfill(2) + str(datetime[4]).zfill(2) +  '01'
    #_file_name = f'result_{_datetime_string}.html'
    #print(_file_name)
    #_file = reserve_tools.save_html_to_filename(res, _file_name)
    # HTML解析を実行して、発見した空き予約を予約リストに追加するする
    #print(res.text)
    analyze_html(cfg, cookies, datetime, res, reserves_list)
    # 空き予約リストを返す
    return reserves_list


# 空き予約検索結果ページを解析し、空き予約リストに追加する
@reserve_tools.elapsed_time
def analyze_html(cfg, cookies, datetime, res, reserves_list) :
    """
    6件目以降の検索のために、空き予約結果ページからフォームデータを取得するとともに、
    空き予約リストに追加する
    """
    # 入力値から空き予約リストに利用する年月日時分データを作成する
    _date = str(datetime[0]) + str(datetime[1]).zfill(2) + str(datetime[2]).zfill(2)
    _time = str(datetime[3]).zfill(2) + ':' + str(datetime[4]).zfill(2) + '-' + str(datetime[5]).zfill(2) + ':' + str(datetime[6]).zfill(2)
    #print(f'{_date} {_time}')
    # 6件目以降の検索のためのフォームデータを初期化する
    _form_data = {}
    soup =BeautifulSoup(res.text, "html.parser")
    _form = soup.find_all('form')
    # フォームデータ部分を取得する
    # 空き予約件数, 現在のページ数, 検索指定年月日、その他もろもろ
    _dataform = _form[1]
    _out = _dataform.find_all('input', id, type="hidden")
    for _tag in _out:
        _name = _tag['name']
        _value = _tag['value']
        _form_data[_name] = _value
        #print(_form_data)
    # te-conditionsを取得する
    # 最後のscriptタグを取得する
    _te_conditions = soup.find_all('script')[-1]
    # JavaScript中のspan.innerHTMLのinputタグのvalueを取得する
    _te_conditions_value = re.search(r'value=\'.+\'', _te_conditions.prettify()).group()
    _te_value = _te_conditions_value[7:-1]
    _form_data['te-conditions'] = _te_value
    # 発見した空き予約件数と現在のオフセット値を取得する
    _empty_count = int(_form_data['layoutChildBody:childForm:allCount'])
    _offset = int(_form_data['layoutChildBody:childForm:offset'])
    # 空き予約リストに追加する
    reserves_list = get_empty_reserve_name(cfg, datetime, _dataform, reserves_list)
    # 次の空き予約が存在する場合は次の空き予約ページに移動する
    if _offset + 5 < _empty_count:
        # フォームデータのoffset値に5を追加して、次の予約を参照できるようにする
        _next_offset = _offset + 5
        _form_data['layoutChildBody:childForm:offset'] = str(_next_offset)
        reserves_list = search_empty_reserves_from_emptystate(cfg, cookies, datetime, _form_data, res, reserves_list)
    #else:
    #    print(f'go to last empty reserves.')
    return None


# 空き予約検索結果ページを解析し、空き予約リストに追加する
@reserve_tools.elapsed_time
def analyze_html_02(cfg, cookies, res, reserves_list) :
    """
    6件目以降の検索のために、空き予約結果ページからフォームデータを取得するとともに、
    空き予約リストに追加する
    """
    # 入力値から空き予約リストに利用する年月日時分データを作成する
    #_date = str(datetime[0]) + str(datetime[1]).zfill(2) + str(datetime[2]).zfill(2)
    #_time = str(datetime[3]).zfill(2) + ':' + str(datetime[4]).zfill(2) + '-' + str(datetime[5]).zfill(2) + ':' + str(datetime[6]).zfill(2)
    #print(f'{_date} {_time}')
    # 6件目以降の検索のためのフォームデータを初期化する
    _form_data = {}
    #soup =BeautifulSoup(res.text, "html.parser")
    soup =BeautifulSoup(res, "html.parser")
    # 検索結果ページから検索条件である、年月日時分を取得する
    _year = int(soup.find('span', id="year--").string)
    _month = int(soup.find('span', id="month--").string)
    _day = int(soup.find('span', id="day--").string)
    _stime = soup.find('span', id="stimeLabel").string
    # hh時の場合、hh:00に置換される
    _stime = re.sub('時', ':00', _stime)
    # hh時30分の場合、hh:30に置換される
    _stime = re.sub('時30分', ':30', _stime)
    # 開始時刻と時分を取得する
    _shour = int(_stime.split(':')[0])
    _smin = int(_stime.split(':')[1])
    # 終了時刻
    _etime = soup.find('span', id="etimeLabel").string
    _etime = re.sub('時$', ':00', _etime)
    _etime = re.sub('時30分$', ':30', _etime)
    # 終了時刻と時分を取得する
    _ehour = int(_etime.split(':')[0])
    _emin = int(_etime.split(':')[1])
    # 検索時刻を作成する
    datetime = [ _year, _month, _day, _shour, _smin, _ehour, _emin ]
    #print(f'datetime: {datetime}')
    # デバッグ用としてhtmlファイルとして保存する
    _datetime_string = str(datetime[0]) + str(datetime[1]).zfill(2) + str(datetime[2]).zfill(2) + str(datetime[3]).zfill(2) + str(datetime[4]).zfill(2)
    _file_name = f'result_{_datetime_string}.html'
    #print(_file_name)
    _file = reserve_tools.save_html_to_filename_for_aiohttp(res, _file_name)
    _form = soup.find_all('form')
    # フォームデータ部分を取得する
    # 空き予約件数, 現在のページ数, 検索指定年月日、その他もろもろ
    _dataform = _form[1]
    _out = _dataform.find_all('input', id, type="hidden")
    for _tag in _out:
        _name = _tag['name']
        _value = _tag['value']
        _form_data[_name] = _value
        #print(_form_data)
    # te-conditionsを取得する
    # 最後のscriptタグを取得する
    _te_conditions = soup.find_all('script')[-1]
    # JavaScript中のspan.innerHTMLのinputタグのvalueを取得する
    _te_conditions_value = re.search(r'value=\'.+\'', _te_conditions.prettify()).group()
    _te_value = _te_conditions_value[7:-1]
    _form_data['te-conditions'] = _te_value
    # 発見した空き予約件数と現在のオフセット値を取得する
    _empty_count = int(_form_data['layoutChildBody:childForm:allCount'])
    _offset = int(_form_data['layoutChildBody:childForm:offset'])
    # 空き予約リストに追加する
    reserves_list = get_empty_reserve_name(cfg, datetime, _dataform, reserves_list)
    # 次の空き予約が存在する場合は次の空き予約ページに移動する
    if _offset + 5 < _empty_count:
        # フォームデータのoffset値に5を追加して、次の予約を参照できるようにする
        _next_offset = _offset + 5
        _form_data['layoutChildBody:childForm:offset'] = str(_next_offset)
        #reserves_list = search_empty_reserves_from_emptystate(cfg, cookies, datetime, _form_data, res, reserves_list)
    #else:
    #    print(f'go to last empty reserves.')
    return None


# 空き予約の施設名とコート名を取得する
@reserve_tools.elapsed_time
def get_empty_reserve_name(cfg, datetime, data_form, reserves_list):
    """
    検索結果ページより空き予約の施設名とコート名を取得する
    """
    # 入力値から空き予約リストに利用する年月日時分データを作成する
    #_date = str(datetime[0]) + '-' + str(datetime[1]).zfill(2) + '-' + str(datetime[2]).zfill(2)
    _date = str(datetime[0]) + str(datetime[1]).zfill(2) + str(datetime[2]).zfill(2)
    _time = str(datetime[3]).zfill(2) + ':' + str(datetime[4]).zfill(2) + '-' + str(datetime[5]).zfill(2) + ':' + str(datetime[6]).zfill(2)
    #print(f'{_date} {_time}')
    # 設定ファイルから除外施設のリストの要素数を取得する
    _exclude_count = len(cfg['exclude_location'])
    # 施設名とコート名を取得する
    #_locate = _d.find_all('span', id=["bnamem", "inamem"])
    _locate = data_form.find_all('span', id="bnamem")
    _court = data_form.find_all('span', id="inamem")
    # 空き予約がない場合は次の検索に進む
    if len(_locate) == 0:
        #print(f'No empty reseves: {_date} {_time}.')
        return None
    else:
        # 取得した施設名とコート名を結合し、空き予約リストに追加する
        # _no: 空き予約施設／コートの数
        _no = 0
        for _locate_name in _locate:
            # 除外施設がなければ、空き予約をすべて登録する
            if _exclude_count == 0:
                _locate_court = str(_locate_name.string) + '／' + str(_court[_no].string)
                _no += 1
                # 空き予約リストに追加する
                # 空き予約リストに発見した日がなければ、年月日をキーとして初期化する
                if _date not in reserves_list:
                    reserves_list[_date] = {}
                    reserves_list[_date].setdefault(_time, []).append(_locate_court)
                # 空き予約リストに発見した日が登録されていた場合
                else:
                    # 空き予約リストに発見した時間帯がなければ、時間をキーとしてリストを初期化する
                    if _time not in reserves_list[_date]:
                        reserves_list[_date][_time] = []
                    reserves_list[_date][_time].append(_locate_court)
            # 除外施設があれば、除外施設と一致するか比較し、一致しなければ登録する
            else:
                # 除外施設の場合は次に進む
                # _match: 比較した回数
                _match = 0
                for _exclude_location in cfg['exclude_location']:
                    # 除外施設名と一致するか確認する。一致する場合は次の施設名を処理する
                    if _exclude_location == str(_locate_name.string):
                        print(f'matched exclude location: {_locate_name.string}')
                        break
                    else:
                        # 一致しない場合はカウントアップし、除外施設名のリストの要素数より多くなったら
                        # 空き予約リストに追加する
                        _match += 1
                        if _match >= _exclude_count:
                            # 空き予約として表示された順に比較するので、施設名と対になるコート名をリスト番号から取得する
                            _locate_court = str(_locate_name.string) + '／' + str(_court[_no].string)
                            _no += 1
                            #print(_locate_court)
                            # 空き予約リストに追加する
                            # 空き予約リストに発見した日がなければ、年月日をキーとして初期化する
                            if _date not in reserves_list:
                                reserves_list[_date] = {}
                                reserves_list[_date].setdefault(_time, []).append(_locate_court)
                            # 空き予約リストに発見した日が登録されていた場合
                            else:
                                # 空き予約リストに発見した時間帯がなければ、時間をキーとしてリストを初期化する
                                if _time not in reserves_list[_date]:
                                    reserves_list[_date][_time] = []
                                reserves_list[_date][_time].append(_locate_court)
    print(reserves_list)
    return reserves_list

# 空き予約時間帯を検索するURLリストへの登録を排他制御する
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

### 事前準備処理 ###
@reserve_tools.elapsed_time
def prepare_proc():
    """
    事前準備プロセス
    - 祝日リストの作成
    - 設定ファイルの読み込み
    - 検索対象年月日時分リストの作成
    - 検索用cookiesの取得
    - 利用日時検索ページへの移動
    - フォームデータの取得
    """
    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 入力データの辞書の初期化
    input_data = {}
    # 送信メッセージリストの初期化
    message_bodies = []
    # WEBリクエストのヘッダー
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
            }
    # 処理の開始
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    reserve_tools.set_public_holiday('public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = reserve_tools.read_json_cfg('cfg2.json')
    # 検索リストを作成する
    #page = 0
    #is_empty = 'False'
    # 検索対象月を取得する
    target_months_list = reserve_tools.create_month_list(cfg)
    # 検索年月日時間を取得する
    datetime_list = create_datetime_list(target_months_list, public_holiday, cfg)
    #exit()
    # cookieの取得
    ( cookies, response ) = get_cookie_request(cfg)
    # 利用日時検索ページに移動する
    #response = go_to_search_date_menu(cfg, headers, cookies)
    # フォームデータを取得する
    #form_data = get_formdata(response)
    # 設定ファイル、検索対象年月日時分、クッキー、フォームデータを返す
    return ( cfg, cookies, datetime_list)

# 空き予約を検索する
@reserve_tools.elapsed_time
def main(cfg, cookies, datetime_list, coro, limit=2):
    """
    空き予約検索のメインルーチン
    """
    # 空き予約の辞書の初期化
    reserves_list = {}
    # 実行時間を測定する
    start = time.time()
    # HTTPリクエスト数
    http_req_num = 0
    # aiohttpのセッティング
    ## 同時接続数の設定
    #conn = aiohttp.TCPConnector(limit=limit)
    # 非同期IO処理のaiohttpのためにイベントループを作成する
    loop = asyncio.get_event_loop()
    # 空き予約検索を開始する
    ## 検索のためのリクエストオブジェクトを作成する
    ## 利用日時検索ページで空き予約を検索する
    #( reserves_list, http_req_num ) = loop.run_until_complete(search_empty_reserves_from_datesearch(cfg, cookies, form_data, datetime_list, reserves_list))
    ( responses, http_req_num ) = loop.run_until_complete(post_request_from_datesearch(cfg, cookies, datetime_list, reserves_list, coro, http_req_num, limit=2))
    # デバッグ用(HTTPリクエスト回数を表示する)
    print(f'HTTP リクエスト数: {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - start
    print(f'main() duration time: {elapsed_time} sec')
    print(f'####################################')
    #exit()
    return ( responses, http_req_num )

### 事後処理 ###
@reserve_tools.elapsed_time
def post_proc(cfg, reserves_list):
    """
    事後処理プロセス
    - 空き予約リストの正規化と書式設定
    - LINE Notifyへのメッセージ送信
    """
    # 送信メッセージを作成する
    message_bodies = reserve_tools.create_message_body(reserves_list, message_bodies, cfg)
    # LINEに送信する
    reserve_tools.send_line_notify(message_bodies, cfg)
    # プログラウの終了
    #exit()

if __name__ == '__main__':
    # 実行時間を測定する
    _start = time.time()

    # コルーチンを生成する
    @reserve_tools.elapsed_time
    async def coroutine(cfg, cookies, headers, form_data, response):
        return cookies, headers, response.status, await response.text()

    # 非同期ロックの設定
    #async_lock_reserves = AsyncioLockReservesList()
    #reserves_list = async_lock_reserves.reserves_list
     
    # 空き予約の辞書の初期化
    reserves_list = {}

    # 事前準備
    (cfg, cookies, datetime_list) = prepare_proc()

    print(f'')
    print(f'#### Collect Http Responses Start : ####')
    print(f'')

    # 空き予約を検索し、検索結果ページを取得する
    ( responses, http_req_num ) = main(cfg=cfg, cookies=cookies, datetime_list=datetime_list, coro=coroutine, limit=2)

    print(f'')
    print(f'#### Collect Http Responses End : ####')
    print(f'')

    # 空き予約検索結果ページを解析し、空き予約リストに追加する
    _n = 0
    for res in responses:
        # HTMLボディ本体はres[3]
        #reserves_list = analyze_html_02(cfg, cookies, res[3], reserves_list)
        # デバッグ用としてhtmlファイルとして保存する
        _str_n = str(_n).zfill(2)
        _file_name = F'result_multi_aiohttp01_{_str_n}.html'
        print(f'save html file: {_file_name}')
        with open(_file_name, mode='w', encoding='utf-8', errors='ignore') as f:
            f.write(res[3])
        _n += 1

    #print(reserves_list)

    # 事後処理
    #post_proc(cfg, reserves_list)

    # デバッグ用(HTTPリクエスト回数を表示する)
    print(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - _start
    print(f'whole() duration time: {elapsed_time} sec')

    print(type(responses))
    print(dir(responses))
    exit()




