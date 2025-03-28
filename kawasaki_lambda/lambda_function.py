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
import urllib

# WEBAPI関連
import requests
from urllib3.util import Retry, timeout
from requests.adapters import HTTPAdapter

# JSONファイルの取り扱い
import json

# 並列処理モジュール(threading)
from concurrent.futures import (
    ThreadPoolExecutor,
    Future,
    as_completed,
    wait
)

# スレッドロック
import threading

# URLの'/'が問題になるためハッシュ化する
from hashlib import md5
from pathlib import Path

# ツールライブラリを読み込む
import reserve_tools

# 検索結果ページの表示件数
page_unit = 5

# HTTPリクエスト回数
http_req_num = 0

# スレッド数
threads = 5

# システムエラーにより空き予約ページを取得できない検索対象年月日を保存するリスト
retry_datetime_list = []

# 予約時間帯のリストを作成する。フォームデータのHTML解析でindex番号として使う
tzone = [ 9, 12, 14, 16, 18 ]

# 年月日時分の入力リストを作成する
#@reserve_tools.elapsed_time
def create_datetime_list(target_months_list, public_holiday, cfg, logger=None):
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
                # 開始時刻が9時の場合は3時間にする
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
    logger.debug(datetime_list)
    return datetime_list

# 並列処理をするための関数
## 空き予約を検索するために事前処理として、同時実行数分のcookieとフォームデータを取得する
#@reserve_tools.elapsed_time
def multi_thread_prepareproc(cfg, reqdata, threads=1, logger=None):
    """
    threads数分だけ実施する
    1)cookieを取得する
    2)利用日時リンクページに接続し、フォームデータを取得する
    """
    #print(f'スレッド数: {threads}')
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(get_cookie_and_formdata, cfg, index, logger=logger) for index in range(threads)]
        for future in as_completed(futures):
            #print(future.result())
            reqdata.append(future.result())
        #print(type(reqdata))
        #print(dir(reqdata))
        return reqdata

## 空き予約を検索する
#@reserve_tools.elapsed_time
def multi_thread_datesearch(cfg, datetime_list, threadsafe_list, reqdata, threads=1, logger=None):
    """
    利用日時ページに利用日時を入力して検索する
    """
    # 実行結果を入れるオブジェクトの初期化
    futures = []
    #print(f'スレッド数: {threads}')
    with ThreadPoolExecutor(max_workers=threads) as executor:
        _index = 0
        for datetime in datetime_list:
            # スレッド数分だけ取得したcookiesとform_dataのどれを使うか決める
            th_index = int(_index) % int(threads)
            future = executor.submit(search_empty_reserves_from_datesearch, cfg, threadsafe_list, reqdata, datetime, th_index, logger=logger)
            _index += 1
            futures.append(future)
        for future in as_completed(futures):
            future.result()
        return threadsafe_list

# クローラー
## cookieとフォームデータを事前に取得する
#@reserve_tools.elapsed_time
def get_cookie_and_formdata(cfg, index, logger=None):
    """
    cookieとformdataを取得する
    """
    #logger.debug(f'インデックス: # {index}')
    # ヘッダーを設定する
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
            }
    # cookieを取得する
    (cookies, response) = get_cookie_request(cfg, logger=logger)
    # フォームデータを取得する
    response = go_to_search_date_menu(cfg, headers, cookies, logger=logger)
    #reqdata.append(get_formdata(response))
    _reqdata = get_formdata(response)
    return cookies, _reqdata

## cookieを取得するため、トップページにアクセスする
@reserve_tools.elapsed_time
def get_cookie_request(cfg, logger=None):
    """
    cookieを取得する
    """
    global http_req_num
    # セッションを開始する
    session = requests.Session()
    # 再試行3回、sleep時間1秒、timeout以外でリトライのステータスコード
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    try:
        # 2023/3/12: ふれあいネットの応答悪化に伴い、タイムアウト時間を(3.0, 10.0)から(6.0, 15.0)に変更する
        response = session.get(cfg['first_url'], timeout=(6.0, 15.0))
    except requests.exceptions.Timeout as e:
        logger.exception(f'timeout for get cookie: {e}')
        http_req_num += retries
    except requests.exceptions.ConnectionError as e:
        logger.exception(f'connection error for get cookie: {e}')
        http_req_num += retries
    else:
        http_req_num += 1
    # セッションを開始する
    #session = requests.session()
    #response = session.get(cfg['first_url'])
    #global http_req_num
    #http_req_num += 1
    # cookie情報を初期化し、次回以降のリクエストでrequestsモジュールの渡せる形に整形する
    cookies = {}
    cookies[cfg['cookie_name_01']] = session.cookies.get(cfg['cookie_name_01'])
    cookies[cfg['cookie_name_02']] = session.cookies.get(cfg['cookie_name_02'])
    #print(cookies)
    return cookies , response

## 施設の空き状況検索の利用日時からのリンクをクリックして、検索画面に移動する
#@reserve_tools.elapsed_time
def go_to_search_date_menu(cfg, headers, cookies, logger=None):
    """
    施設の空き状況検索の利用日時からのリンクをクリックして、検索画面に移動する
    """
    global http_req_num
    res = requests.get(cfg['search_url'], headers=headers, cookies=cookies)
    http_req_num += 1
    #print(res.text)
    return res

## フォームデータを取得する
#@reserve_tools.elapsed_time
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
    #print(type(_form_data))
    return _form_data

## 利用日時ページに検索データを入力して検索する
#@reserve_tools.elapsed_time
def search_empty_reserves_from_datesearch(cfg, threadsafe_list, reqdata, datetime, th_index, logger=None):
    """
    利用日時と利用目的、地域を入力して空き予約を検索する
    """
    # 直前のリクエストURLからRefererを含んだヘッダーを生成する
    headers = {
        'Origin': cfg['origin_url'],
        'Referer': cfg['search_url'],
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
    }
    # reqdataからcookieとフォームデータを生成する
    cookies = dict(reqdata[th_index][0])
    form_data = dict(reqdata[th_index][1])
    # 利用目的を取得し、フォームデータに代入する
    form_data['layoutChildBody:childForm:purpose'] = cfg['selected_purpose']
    # 検索対象地域を取得、フォームデータに代入する
    #for _area in cfg['selected_areas']:
    #    form_data['layoutChildBody:childForm:area'] = cfg['selected_areas']
    # rsvDateSearchページの検索ボタンの値を代入する
    form_data['layoutChildBody:childForm:doDateSearch'] = '上記の内容で検索する'
    # 空き状況カレンダーの日付リンク(doChangeDate, rsvEmptyStateページ)の値を代入する
    #for _datetime in datetime_list:
    # フォームデータの検索日時データを生成する
    form_data['layoutChildBody:childForm:year'] = datetime[0]
    form_data['layoutChildBody:childForm:month'] = datetime[1]
    form_data['layoutChildBody:childForm:day'] = datetime[2]
    form_data['layoutChildBody:childForm:sHour'] = datetime[3]
    form_data['layoutChildBody:childForm:sMinute'] = datetime[4]
    form_data['layoutChildBody:childForm:eHour'] = datetime[5]
    form_data['layoutChildBody:childForm:eMinute'] = datetime[6]
    #print(form_data)
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、空き予約を検索する
    res = requests.post(cfg['search_url'], headers=headers, cookies=cookies, data=params)
    global http_req_num
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    #_datetime_string = str(datetime[0]) + str(datetime[1]).zfill(2) + str(datetime[2]).zfill(2) + str(datetime[3]).zfill(2) + str(datetime[4]).zfill(2)
    #_file_name = f'result_{_datetime_string}.html'
    #_file = reserve_tools.save_html_to_filename(res, _file_name)
    # HTML解析を実行して、発見した空き予約を予約リストに追加するする
    threadsafe_list = analyze_html(cfg, cookies, datetime, res, threadsafe_list, logger=logger)
    # 空き予約リストを返す
    return threadsafe_list

## 空き予約が5件以上存在したので、6件目以降を利用日時ページに検索データを入力して検索する
#@reserve_tools.elapsed_time
def search_empty_reserves_from_emptystate(cfg, cookies, datetime, form_data, res, threadsafe_list, logger=None):
    """
    利用日時と利用目的、地域を入力して空き予約を検索する
    """
    # リダイレクトされているか確認する
    # リダイレクトされている場合はリダイレクト元のレスポンスヘッダのLocationを取得する
    if res.history:
        _referer = res.history[-1].headers['Location']
    else:
        _referer = cfg['empty_state_url']
    #print(f'referer: {_referer}')
    # 直前のリクエストURLからRefererを含んだヘッダーを生成する
    headers = {
        'Origin': cfg['origin_url'],
        'Referer': _referer,
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
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
    global http_req_num
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    #_datetime_string = str(datetime[0]) + str(datetime[1]).zfill(2) + str(datetime[2]).zfill(2) + str(datetime[3]).zfill(2) + str(datetime[4]).zfill(2) +  '01'
    #_file_name = f'result_{_datetime_string}.html'
    #print(_file_name)
    #_file = reserve_tools.save_html_to_filename(res, _file_name)
    # HTML解析を実行して、発見した空き予約を予約リストに追加するする
    #print(res.text)
    threadsafe_list = analyze_html(cfg, cookies, datetime, res, threadsafe_list, logger=logger)
    # 空き予約リストを返す
    return threadsafe_list

# 空き予約検索結果ページを解析し、空き予約リストに追加する
#@reserve_tools.elapsed_time
def analyze_html(cfg, cookies, datetime, res, threadsafe_list, logger=None) :
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
    # システムエラーが発生したか確認し、システムエラーが発生した場合は以降の処理は実施しない
    # システムエラー時は下記のタグが生成される
    #//*['form', id="errorForm"]
    _is_error = soup.find('form', id="errorForm")
    if _is_error != None:
        logger.warning(f'システムエラーが発生したため、HTML解析をスキップします。')
        logger.warning(f'システムエラーが発生した検索対象年月日時分: {_date} {_time}')
        global retry_datetime_list
        retry_datetime_list.append(datetime)
        return None
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
    threadsafe_list = get_empty_reserve_name(cfg, datetime, _dataform, threadsafe_list, logger=logger)
    # 次の空き予約が存在する場合は次の空き予約ページに移動する
    if _offset + 5 < _empty_count:
        # フォームデータのoffset値に5を追加して、次の予約を参照できるようにする
        _next_offset = _offset + 5
        _form_data['layoutChildBody:childForm:offset'] = str(_next_offset)
        threadsafe_list = search_empty_reserves_from_emptystate(cfg, cookies, datetime, _form_data, res, threadsafe_list, logger=logger)
    #else:
    #    print(f'go to last empty reserves.')
    return threadsafe_list

# 空き予約の施設名とコート名を取得する
#@reserve_tools.elapsed_time
def get_empty_reserve_name(cfg, datetime, data_form, threadsafe_list, logger=None):
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
                # if _date not in reserves_list:
                #     reserves_list[_date] = {}
                #     reserves_list[_date].setdefault(_time, []).append(_locate_court)
                # 空き予約リストに発見した日が登録されていた場合
                # else:
                #     # 空き予約リストに発見した時間帯がなければ、時間をキーとしてリストを初期化する
                #     if _time not in reserves_list[_date]:
                #         reserves_list[_date][_time] = []
                #     reserves_list[_date][_time].append(_locate_court)
                # スレッドセーフな空き予約リストに追加する
                threadsafe_list.add_reserves(_date, _time, _locate_court)
            # 除外施設があれば、除外施設と一致するか比較し、一致しなければ登録する
            else:
                # 除外施設の場合は次に進む
                # _match: 比較した回数
                _match = 0
                for _exclude_location in cfg['exclude_location']:
                    # 除外施設名と一致するか確認する。一致する場合は次の施設名を処理する
                    if _exclude_location == str(_locate_name.string):
                        logger.debug(f'matched exclude location: {_locate_name.string}')
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
                            # if _date not in reserves_list:
                            #     reserves_list[_date] = {}
                            #     reserves_list[_date].setdefault(_time, []).append(_locate_court)
                            # 空き予約リストに発見した日が登録されていた場合
                            # else:
                            #     # 空き予約リストに発見した時間帯がなければ、時間をキーとしてリストを初期化する
                            #     if _time not in reserves_list[_date]:
                            #         reserves_list[_date][_time] = []
                            #     reserves_list[_date][_time].append(_locate_court)
                            # スレッドセーフな空き予約リストに追加する
                            threadsafe_list.add_reserves(_date, _time, _locate_court)
    #print(threadsafe_list)
    return threadsafe_list

# スレッドセーフな空き予約リスト
class ThreadSafeReservesList:
    lock = threading.Lock()
    def __init__(self):
        self.reserves_list = {}
    def add_reserves(self, _date, _time, _locate_court):
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
            #print(self.reserves_list)

# 予約取得用クローラー
## cookieを取得するため、トップページにアクセスする
#@reserve_tools.elapsed_time
#def get_cookie_request(cfg, logger=None):

## トップページのフォームデータを取得する
def get_homeindex_formdata(response):
    """
    ログインページに移動するためにトップページのフォームデータを取得する
    """
    # フォームデータ(dict型)を初期化する
    _form_data = {}
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    _form = soup.find_all('form')[1]
    #print(_form)
    #exit()
    # フォームデータを取得する
    _form_data['layoutChildBody:childForm/view/user/homeIndex.html'] = _form.find_all('input')[1]['value']
    _form_data['layoutChildBody:childForm:doLogin'] = _form.find_all('input')[0]['type']
    # 最後の script ヘッダを抽出する
    _te = soup.find_all('script')[-1]
    # te-conditions 部分を抽出する
    _te_value = re.search('value=\'.+\'', _te.contents[0])
    # value=の文字列が含まれるので、これを削除してフォームデータに代入する
    _form_data['te-conditions'] = _te_value.group()[7:-1]
    # フォームデータを返す
    #print(json.dumps(_form_data, indent=2))
    #print(_form_data)
    return _form_data

## ログインページにアクセスする
@reserve_tools.elapsed_time
def login_request(cfg, cookies, form_data):
    """
    トップページの「ログインする」ボタンをクリックして、ログインページを表示する
    """
    global http_req_num
    # 直前のリクエストURLからRefererを含んだヘッダーを生成する
    headers = {
        'Origin': cfg['origin_url'],
        'Referer': cfg['first_url'],
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
    }
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    #print(headers)
    #print(cookies)
    #print(params)
    # フォームデータを使って、ログインページを表示する。リダイレクトを許可する
    response = requests.post(cfg['first_url'], headers=headers, cookies=cookies, data=params, allow_redirects=True)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = f'login.html'
    #print(_file_name)
    #_file = reserve_tools.save_html_to_filename(response, _file_name)
    #print(response.url)
    # 次のPOSTリクエストのためにヘッダーを作成する
    headers['Referer'] = f'{response.url}'
    return headers, response

## ログインページのフォームデータを取得する
def get_login_formdata(response):
    """
    ログインページのフォームデータを取得する
    """
    # レスポンスヘッダーから次のリクエストに必要なデータを取得する
    #res_headers = response.headers
    #print(res_headers)
    # フォームデータ(dict型)を初期化する
    _form_data = {}
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    _form = soup.find_all('form')[1]
    # フォームデータを取得する
    _form_data['layoutChildBody:childForm:loginJKey'] = _form.find('input', id="loginJKey")['value']
    _form_data['layoutChildBody:childForm:doLogin'] = _form.find('input', id="doLogin")['value']
    _form_data['layoutChildBody:childForm:cookieCheck'] = "false"
    _form_data['layoutChildBody:childForm/view/user/mypIndex.html'] = _form.find_all('input')[-1]['value']
    # 最後の script ヘッダを抽出する
    _te = soup.find_all('script')[-1]
    # te-conditions 部分を抽出する
    _te_value = re.search('value=\'.+\'', _te.contents[0])
    # value=の文字列が含まれるので、これを削除してフォームデータに代入する
    _form_data['te-conditions'] = _te_value.group()[7:-1]
    # フォームデータを返す
    #print(json.dumps(_form_data, indent=2))
    return _form_data

## ログインページで、ユーザーＩＤ、パスワードを入力して、マイページを表示する
@reserve_tools.elapsed_time
def input_userdata_in_login(cfg, userid, password, securityid, cookies, headers, form_data):
    """
    ログインページでユーザーIDとパスワード、セキュリティ番号を入力し、マイページに移動する
    """
    global http_req_num
    # headers = {
    #     'Origin': cfg['origin_url'],
    #     'Referer': cfg['mypindex_url'],
    #     'Content-Type': 'application/x-www-form-urlencoded',
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
    # }
    _form_data = form_data
    # # ユーザーIDとパスワード、セキュリティ番号を入力する
    # _form_data['layoutChildBody:childForm:userid'] = cfg['userid']
    # _form_data['layoutChildBody:childForm:passwd'] = cfg['password']
    # _form_data['layoutChildBody:childForm:securityno'] = cfg['securityid']
    _form_data['layoutChildBody:childForm:userid'] = userid
    _form_data['layoutChildBody:childForm:passwd'] = password
    _form_data['layoutChildBody:childForm:securityno'] = securityid
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、マイページを表示する
    response = requests.post(cfg['mypindex_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = f'mypage.html'
    #_file = reserve_tools.save_html_to_filename(response, _file_name)
    # ログインしたことによりcookieが再発行されるので、cookiesを更新する
    cookies[cfg['cookie_name_01']] = response.cookies.get(cfg['cookie_name_01'])
    # 次のPOSTリクエストのためにヘッダーを作成する
    headers['Referer'] = f'{response.url}'
    # 次のPOSTリクエストのためにクッキーのJSESSIONIDをレスポンスで新たに発行されたものに置き換える
    cookies['JSESSIONID'] = response.cookies['JSESSIONID']
    return cookies, headers, response

## マイページから既存予約情報を取得する
#def get_reserved_info(cfg):
def get_reserved_info(cfg, response, logger=None):
    """
    マイページから既存予約済みの情報を取得する
    """
    # デバッグ
    #with open('./mypage_reserves_01.html', mode='r', encoding='utf-8', errors='ignore') as shtml:
    # 予約リスト(dict型)を初期化する
    _reserved_list = {}
    # html解析
    #soup = BeautifulSoup(shtml.read(), 'html.parser')
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    # 既存予約情報がない場合は空のdictで返す
    _div = soup.find('div', id="isEmptylist")
    #print(_div)
    if _div is not None:
        logger.info(f'No Reserves Entry')
        return _reserved_list
    # 既存予約情報がある場合は予約情報を取得する
    _div = soup.find('div', id="isNotEmptylist")
    #print(_div)
    #_tr = _div.table.contents
    _tr = _div.find_all('tr')
    #print(_tr)
    # 既存予約件数を計算する
    reserves_num = int( ( len(_tr) - 1 ) / 2 )
    logger.info(f'reserves_num : {reserves_num}')
    # HTMLを解析する
    _tr_num = 0
    # 予約表のヘッダー行を除くため、2行目から解析する
    for _tag in _tr[1:]:
        #print(_tag)
        # 館情報のセルのtrタグを除外するため、奇数番目のtrタグを処理せず、次のセルの処理に移る
        if _tr_num % 2 == 1:
            _tr_num += 1
            continue
        # 日付ラベルの年、月、日を取り除き、年月日のそれぞれの数値を取得する
        _ymdLabel = _tag.find('span', id="ymdLabel").string.replace('年',' ').replace('月',' ').replace('日',' ')
        _year = _ymdLabel.split()[0]
        _month = _ymdLabel.split()[1]
        _day = _ymdLabel.split()[2]
        _date = str(_year) + str(_month).zfill(2) + str(_day).zfill(2)
        # 開始時刻と終了時刻の時刻文字列を作成する
        _stimeLabel = _tag.find('span', id="stimeLabel").string.replace('時30分', ':30').replace('時', ':00')
        _etimeLabel = _tag.find('span', id="etimeLabel").string.replace('時30分', ':30').replace('時', ':00')
        _time = _stimeLabel + '-' + _etimeLabel
        # コートの場所とコート番号の文字列を作成する
        _bnamem = _tag.find('span', id="bnamem").string
        _inamem = _tag.find('span', id="inamem").string
        _locate_court = _bnamem + '／' + _inamem
        #print(f'reserves_info: {_ymdLabel} {_date} {_stimeLabel} {_etimeLabel} {_time} {_bnamem} {_inamem}')
        # 予約リストに発見した日がなければ、年月日をキーとして初期化する
        if _date not in _reserved_list:
            _reserved_list[_date] = {}
            _reserved_list[_date].setdefault(_time, []).append(_locate_court)
        # 予約リストに発見した日が登録されていた場合
        else:
            # 空き予約リストに発見した時間帯がなければ、時間をキーとしてリストを初期化する
            if _time not in _reserved_list[_date]:
                _reserved_list[_date][_time] = []
            _reserved_list[_date][_time].append(_locate_court)
        _tr_num += 1
    logger.info(json.dumps(_reserved_list, indent=2, ensure_ascii=False))
    return _reserved_list

# 既存予約件数を取得する
def get_reserved_num(reserved_list, logger=None):
    """
    既存予約件数を取得する
    """
    _reserved_num = 0
    for _date, _date_value in reserved_list.items():
        for _time, _court_list in _date_value.items():
            for _court in _court_list:
                _reserved_num += 1
    # 予約件数を返す
    logger.info(f'reserved num: {_reserved_num}')
    return _reserved_num

## 利用日時から探すをクリックして、検索画面に移動する
@reserve_tools.elapsed_time
def go_to_search_date_menu_with_userid(cfg, userid, cookies, headers):
    """
    施設の空き状況検索の利用日時からのリンクをクリックして、検索画面に移動する
    """
    global http_req_num
    headers = {
        'Host': 'www.fureai-net.city.kawasaki.jp',
        'Referer': headers['Referer'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
    }
    # クッキーにユーザーIDを追加する
    #cookies[cfg['cookie_name_04']] = str(cfg['userid'])
    cookies[cfg['cookie_name_04']] = userid
    response = requests.get(cfg['search_url'], headers=headers, cookies=cookies)
    http_req_num += 1
    #print(res.text)
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = f'rsvDateSearch.html'
    #_file = reserve_tools.save_html_to_filename(response, _file_name)
    return response

## 利用日時検索のフォームデータを取得する
def get_formdata_rsvDateSearch(response):
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
    #print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    return _form_data

## 利用日時ページに発見した空き予約コートの年月日時分の検索データを入力して、空きコートを検索する
## 空きコートページが表示される
@reserve_tools.elapsed_time
def do_reserves_from_datesearch(cfg, cookies, form_data, date, time, logger=None):
    """
    利用日時と利用目的、地域を入力して空き予約を検索する
    date : string: YYYYMMDD
    time : string: hh:mm-hh:mm
    """
    global http_req_num
    # 入力用年月日データを初期化する
    _datetime = []
    # 入力値のdate, timeを検索パラメータに変換する
    # 引数で受け取った年月日と時間帯のデータを代入する
    _datetime.append(int(date[0:4]))
    _datetime.append(int(date[4:6]))
    _datetime.append(int(date[6:8]))
    _datetime.append(int(time[0:2]))
    _datetime.append(int(time[3:5]))
    _datetime.append(int(time[6:8]))
    _datetime.append(int(time[9:11]))
    # 検索する時間が予約時間帯リストの何番目かを取得する
    tzone_index = tzone.index(_datetime[3])
    # 直前のリクエストURLからRefererを含んだヘッダーを生成する
    headers = {
        'Origin': cfg['origin_url'],
        'Referer': cfg['search_url'],
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
    }
    # 利用目的を取得し、フォームデータに代入する
    form_data['layoutChildBody:childForm:purpose'] = cfg['selected_purpose']
    # 検索対象地域を取得、フォームデータに代入する
    for _area in cfg['selected_areas']:
        form_data['layoutChildBody:childForm:area'] = cfg['selected_areas']
    # rsvDateSearchページの検索ボタンの値を代入する
    form_data['layoutChildBody:childForm:doDateSearch'] = '上記の内容で検索する'
    # 空き状況カレンダーの日付リンク(doChangeDate, rsvEmptyStateページ)の値を代入する
    #for _datetime in datetime_list:
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
    response = requests.post(cfg['search_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    _datetime_string = str(_datetime[0]) + str(_datetime[1]).zfill(2) + str(_datetime[2]).zfill(2) + str(_datetime[3]).zfill(2) + str(_datetime[4]).zfill(2)
    #_file_name = f'result_{_datetime_string}.html'
    #_file = reserve_tools.save_html_to_filename(response, _file_name)
    # 次のリクエストでレスポンスヘッダーのURLの値をRefererとして使うため、これを取得する
    _location_url = response.url
    headers['Referer'] = f'{_location_url}'
    # 空き予約コートページのフォームデータと空き施設名、空きコート名を取得する
    ( rsv_form_data, court_list ) = get_formdata_rsvEmptyState(response)
    # 空き予約を予約カートに追加し、フォームデータと追加した空き施設名と空きコート名を取得する
    ( added_response, court, matched_flag ) = add_reserve_to_cart(cfg, cookies, headers, rsv_form_data, court_list, tzone_index, logger=logger)
    # 空き予約コートが希望日・時間帯・施設名に一致したフラッグを確認し、False(一致しない)ならreturnを返す
    if matched_flag == False:
        reserved_number = None
        reserve = None
        return reserved_number, reserve
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = f'result_add_reserve_{_datetime_string}.html'
    #reserve_tools.save_html_to_filename(added_response, _file_name)
    # 予約をカートに追加済みのフォームデータを取得する
    ( added_form_data, court_list ) = get_formdata_rsvEmptyState(added_response)
    # 予約カートの内容を確認する
    cart_response = display_reserve_cart(cfg, cookies, headers, added_form_data, court_list)
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = f'result_cart_reserve_{_datetime_string}.html'
    #reserve_tools.save_html_to_filename(cart_response, _file_name)
    # 予約カートのフォームを取得する
    ( cart_form_data, _url ) = get_formdata_rsvCartList(cart_response)
    # 「予約確定の手続きへ」ボタンをクリックして、予約確定の手続きをする
    reserve_response = doing_reserve(cfg, cookies, headers, cart_form_data)
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = f'result_do_reserve_{_datetime_string}.html'
    #reserve_tools.save_html_to_filename(reserve_response, _file_name)
    # 利用規約ページが表示された場合、「利用規約に同意する」をチェックして、「詳細情報の入力へ」ボタンをクリックする
    agree_response = agree_reserve(cfg, cookies, headers, reserve_response)
    # 予約施設の確認内容のフォームデータを取得する
    ( reserve_form_data, _url ) = get_formdata_rsvCartDetails(agree_response)
    # 「予約内容を確認する」ボタンをクリックする
    input_response = input_reserve(cfg, cookies, headers, reserve_form_data, _url)
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = f'result_input_reserve_{_datetime_string}.html'
    #reserve_tools.save_html_to_filename(input_response, _file_name)
    # フォームデータを取得する
    ( confirm_form_data, _url ) = get_formdata_rsvCartInputDetailsConfirm(input_response)
    # 「予約を確定する」ボタンをクリックする
    confirm_response = confirm_reserve(cfg, cookies, headers, confirm_form_data, _url)
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = f'result_confirm_reserve_{_datetime_string}.html'
    #reserve_tools.save_html_to_filename(confirm_response, _file_name)
    # 予約番号を取得する
    ( reserved_number_form_data, reserved_number ) = get_confirmed_reserve_number(confirm_response, logger=logger)
    # 予約した年月日と時間をキー、空き施設名／コート名を値としたdictを作成する
    reserve = {}
    reserve[date] = {}
    reserve[date][time] = [ court ]
    # 予約番号と予約した日時とコートを返す
    #print(f'reserved number: {reserved_number}')
    #print(f'reserve datetime and court: {reserve}')
    return reserved_number, reserve

## 空き予約コートページのフォームデータと空き施設名、空きコート名を取得する
def get_formdata_rsvEmptyState(response):
    """
    ページからフォームデータと空きコート施設名とコート名を取得する
    """
    # ファイルを読み込む
    #with open(filename, mode="r", encoding="UTF-8") as f:
    #    _html = f.read()
    #print(_html)
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = reserve_tools.save_html_file(response)
    #print(f'save file: {_file_name}')
    # フォームデータ(dict型)を初期化する
    _form_data = {}
    # html解析
    #soup = BeautifulSoup(_html, 'html.parser')
    soup = BeautifulSoup(response.text, 'html.parser')
    # 表示された空きコートのリストを作成する
    # 空き予約の施設名とコート番号が表示されたタグを抽出する
    # 施設名とコート名が記載されたspnaタグを抽出する
    _locate = soup.find_all('span', id="bnamem")
    _court = soup.find_all('span', id="inamem")
    # 施設名のリストの長さでforループを回す
    court_list = []
    for i in range(len(_locate)):
        #print(f'{_locate[i].text}／{_court[i].text}')
        court_list.append(f'{_locate[i].text}／{_court[i].text}')
    # form_data部分のみ抽出する
    _form = soup.find_all('form')[1]
    # フォームデータを取得する
    # inputタグで、value属性の値があるタグを抽出する
    _input_tags_with_value = _form.find_all('input', value=True)
    #print(_input_tags)
    #exit()
    for _tag in _input_tags_with_value:
        # name属性の値があるタグを対象とする
        if _tag.get('name') is not None:
            # value属性値が「予約カートに追加」と「予約カートの内容を確認」は対象外とする
            #if _tag['value'] != '予約カートに追加' and _tag['value'] != '予約カートの内容を確認':
            _form_data[_tag['name']] = _tag['value']
    # 最後の script ヘッダを抽出する
    _te = soup.find_all('script')[-1]
    # te-conditions 部分を抽出する
    _te_value = re.search('value=\'.+\'', _te.contents[0])
    # value=の文字列が含まれるので、これを削除してフォームデータに代入する
    _form_data['te-conditions'] = _te_value.group()[7:-1]
    # フォームデータを返す
    #print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    #print(court_list)
    return _form_data, court_list

## 空き予約コートページの空きコートと時間帯をクリックした状態にして、予約カートに追加ボタンをクリックして、カート追加済み状態にする
@reserve_tools.elapsed_time
def add_reserve_to_cart(cfg, cookies, headers, form_data, court_list, tzone_index, logger=None):
    """
    入力パラメータのフォームデータと空きコートリストから、カート追加済みのフォームデータを作成する
    """
    global http_req_num
    global page_unit
    # 空きコートと希望コートが一致したフラッグ
    # これがTrueの場合、次のページの検索はしない
    _matched = False
    # 希望施設リストを取得する
    want_location_list = cfg['want_location_list']
    # 最初の5件の空き予約件数と現在のオフセット値を取得する。
    # while文以降ではこれがsearch_next_empty_reserves_from_emptystate() で取得したフォームの値から取得する
    _allcount = int(form_data['layoutChildBody:childForm:allCount'])
    _offset = int(form_data['layoutChildBody:childForm:offset'])
    # 空き予約件数の最後まで確認する
    while _offset < _allcount:
        # 新たに発見した空き予約件数と現在のオフセット値を取得する
        _allcount = int(form_data['layoutChildBody:childForm:allCount'])
        _offset = int(form_data['layoutChildBody:childForm:offset'])
        # 希望施設リストとコートリストを比較する
        for _want_location in want_location_list:
            # 空きコートリストは逆順で辿る
            for _court in reversed(court_list):
                _location = _court.split(sep='／')[0]
                #logger.debug(f'want location : {_want_location}')
                #logger.debug(f'found court name: {_court}')
                if _want_location == _location:
                    # 一致したコートに対するコートリストのindex番号を取得する
                    _want_index = court_list.index(_court)
                    # 次ページ検索フラッグをTrueにする
                    _matched = True
                    # whileループを抜けるため、_offsetを_allcountより大きくする
                    _offset = _allcount + page_unit
                    logger.debug(f'matched {_court} : court_index: {_want_index}')
                    break
        if _matched == False:
            # フォームデータのoffset値に5を追加して、次の予約を取得するため、POSTする
            _offset += page_unit
            # _offset値が_allcountを超えたら検索をwhileループを抜ける
            if _offset > _allcount:
                break
            # 一致したコートがない場合は次の空き予約ページに進む
            logger.debug(f'not found want court. next empty court page.')
            form_data['layoutChildBody:childForm:offset'] = str(_offset)
            response = search_next_empty_reserves_from_emptystate(cfg, cookies, headers, form_data)
            # 取得したレスポンスのフォームデータを取得する
            ( form_data, court_list ) = get_formdata_rsvEmptyState(response)
    # 希望する空きコートが見つからなかった場合はreturnする
    if _matched == False:
        logger.info(f'not found want date time location. therefore this script is finished')
        response = None
        _court = None
        return response, _court, _matched
    # 予約カートに希望コートを追加する処理を開始する
    # 希望する空きコートのインデっクス値に変更する
    form_data['layoutChildBody:childForm:itemindex'] = f'{_want_index}'
    # 希望する空きコートと時間帯のチェックボックスをクリックした値に変更する
    index_string_sel = f'layoutChildBody:childForm:rsvEmptyStateItems:{_want_index}:emptyStateItemsItems:0:emptyStateItems:{tzone_index}:sel'
    form_data[f'{index_string_sel}'] = '1'
    # 不要なフォームデータを削除する
    ## 「予約カートに追加」で不要なコート分を削除する
    for _index in range(len(court_list)):
        # 希望するコート以外は値を削除する
        if _index != _want_index:
            index_string_doAddCart = f'layoutChildBody:childForm:rsvEmptyStateItems:{_index}:doAddCart'
            #print(f'delete formdata: {index_string_doAddCart}')
            del form_data[f'{index_string_doAddCart}']
    ## 「予約カートの内容を確認」を削除する
    if 'layoutChildBody:childForm:jumpRsvCartList' in form_data:
        del form_data['layoutChildBody:childForm:jumpRsvCartList']
    #print(json.dumps(form_data, indent=2, ensure_ascii=False))
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、カートに予約を追加する
    response = requests.post(cfg['empty_state_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # レスポンスを返す
    return response, _court, _matched

## 空き予約が5件以上存在したので、6件目以降を利用日時ページに検索データを入力して検索する
@reserve_tools.elapsed_time
def search_next_empty_reserves_from_emptystate(cfg, cookies, headers, form_data):
    """
    利用日時と利用目的、地域を入力して空き予約を検索する
    """
    global http_req_num
    global page_unit
    # フォームデータから年月日と開始時間を取得する
    datetime = []
    datetime.append(str(form_data['layoutChildBody:childForm:year']))
    datetime.append(str(form_data['layoutChildBody:childForm:month']))
    datetime.append(str(form_data['layoutChildBody:childForm:day']))
    datetime.append(str(form_data['layoutChildBody:childForm:stime']))
    datetime.append(str(form_data['layoutChildBody:childForm:offset']))
    # フォームデータを変更する
    # doPagerの値をsubmitに変更する
    form_data['layoutChildBody:childForm:doPager'] = 'submit'
    # 不要なフォームデータを削除する
    ## 「予約カートに追加」を削除する
    for _index in range(page_unit - 1):
        index_string_doAddCart = f'layoutChildBody:childForm:rsvEmptyStateItems:{_index}:doAddCart'
        #print(f'delete formdata: {index_string_doAddCart}')
        del form_data[f'{index_string_doAddCart}']
    # 「予約カートの内容を確認」を削除する
    if 'layoutChildBody:childForm:jumpRsvCartList' in form_data:
        del form_data['layoutChildBody:childForm:jumpRsvCartList']
    #print(form_data)
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、空き予約を検索する
    response = requests.post(cfg['empty_state_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    _datetime_string = str(datetime[0]) + str(datetime[1]).zfill(2) + str(datetime[2]).zfill(2) + str(datetime[3]).zfill(2) + str(datetime[4]).zfill(2)
    #_file_name = f'result_{_datetime_string}.html'
    #print(_file_name)
    #_file = reserve_tools.save_html_to_filename(response, _file_name)
    # レスポンスを返す
    return response

## 「予約カートの内容を確認」ボタンをクリックして、予約カートを表示する
@reserve_tools.elapsed_time
def display_reserve_cart(cfg, cookies, headers, form_data, court_list):
    """
    「予約カートの内容を確認」ボタンをクリックする
    """
    global http_req_num
    # 不要なフォームデータを削除する
    ## 「予約カートに追加」を削除する
    for _index in range(len(court_list)):
        index_string_doAddCart = f'layoutChildBody:childForm:rsvEmptyStateItems:{_index}:doAddCart'
        #print(f'delete formdata: {index_string_doAddCart}')
        del form_data[f'{index_string_doAddCart}']
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、「予約カートの内容を確認」ボタンをクリックする
    response = requests.post(cfg['empty_state_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # レスポンスを返す
    return response

## 空き予約用のフォームデータを取得する
def get_formdata_common(response, form_number):
    """
    空き予約で利用する汎用的なフォームデータを取得する
    """
    # フォームデータ(dict型)を初期化する
    _form_data = {}
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    _form = soup.find_all('form')[form_number]
    # フォームデータを取得する
    # inputタグで、value属性の値があるタグを抽出する
    _input_tags_with_value = _form.find_all('input', value=True)
    #exit()
    for _tag in _input_tags_with_value:
        # name属性の値があるタグを対象とする
        if _tag.get('name') is not None:
            _form_data[_tag['name']] = _tag['value']
    # 最後の script ヘッダを抽出する
    _te = soup.find_all('script')[-1]
    # te-conditions 部分を抽出する
    _te_value = re.search('value=\'.+\'', _te.contents[0])
    # value=の文字列が含まれるので、これを削除してフォームデータに代入する
    _form_data['te-conditions'] = _te_value.group()[7:-1]
    # フォームデータを返す
    #print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    return ( _form_data, response.url )

## 予約カートのフォームデータを取得する
def get_formdata_rsvCartList(response):
    """
    予約カートのフォームデータを取得する
    """
    # 予約カートのフォームデータは4番目
    _form_number = 3
    # フォームデータを取得する
    ( _form_data, _response_url ) = get_formdata_common(response, _form_number)
    # フォームデータを返す
    return ( _form_data, _response_url )

## 予約確定の手続きをする
@reserve_tools.elapsed_time
def doing_reserve(cfg, cookies, headers, form_data):
    """
    「予約確定の手続きへ」ボタンをクリックする
    """
    global http_req_num
    # 不要なフォームデータを削除する
    ## 取り消しボタンの値を削除する
    if 'layoutChildBody:childForm:inputDetailsItems:0:doCancel' in form_data:
        del form_data['layoutChildBody:childForm:inputDetailsItems:0:doCancel']
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、「予約確定の手続きへ」ボタンをクリックする
    response = requests.post(cfg['cartlist_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # レスポンスを返す
    return response

##　利用規約ページが表示されたか確認する
@reserve_tools.elapsed_time
def agree_reserve(cfg, cookies, headers, response):
    """ 利用規約ページが表示されたか確認する

    Args:
        cfg (_type_): 設定のDict
        cookies (_type_): 予約処理用に取得したcookies
        headers (_type_): HTTPヘッダー
        response (_type_): 予約確定の手続きのHTTPレスポンス

    Returns:
        agree_response: 規約同意のHTTPレスポンス
    """
    # レスポンスのURLを取得する
    _url = str(response.url)
    # 利用規約ページのURLであるか確認する
    if cfg['cartuserules_url'] in _url:
        # 同意処理する
        agree_response = agree_rules(cfg, cookies, headers, response)
    else:
        agree_response = response
    return agree_response

## 規約同意処理をする
@reserve_tools.elapsed_time
def agree_rules(cfg, cookies, headers, response):
    """規約同意のチェックをつけて、POSTリクエストする

    Args:
        cfg (_type_): 設定のDict
        cookies (_type_): 予約処理用に取得したcookies
        headers (_type_): HTTPヘッダー
        response (_type_): 予約確定の手続きのHTTPレスポンス

    Returns:
        response: HTTPレスポンス
    """
    # 利用規約のフォームデータは2番目
    _form_number = 1
    # フォームデータを取得する
    ( _form_data, _response_url )  = get_formdata_common(response, _form_number)
    global http_req_num
    # 利用規約の同意するのラジオボタンを選択する
    _form_data['layoutChildBody:childForm:selected'] = 'ok'
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(_form_data)
    # ヘッダーのRefererを一部を書き換える
    headers['Referer'] = response.url
    # フォームデータを使って、「予約内容を確認する」ボタンをクリックする
    response = requests.post(cfg['cartuserules_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # レスポンスを返す
    return response
    
## 予約施設の確認内容のフォームデータを取得する
def get_formdata_rsvCartDetails(response):
    """
    予約施設の確認内容のフォームデータを取得する
    """
    # 予約施設の確認内容のフォームデータは2番目
    _form_number = 1
    # フォームデータを取得する
    ( _form_data, _response_url ) = get_formdata_common(response, _form_number)
    # フォームデータを返す
    return ( _form_data, _response_url )

## 予約内容を入力して、「予約内容を確認する」ボタンをクリックして、予約結果を表示する
@reserve_tools.elapsed_time
def input_reserve(cfg, cookies, headers, form_data, url):
    """
    予約内容を入力して、「予約内容を確認する」ボタンをクリックして、予約結果を表示する
    予約内容: 利用目的、目的の詳細、利用人数
    """
    global http_req_num
    # 利用目的、目的の詳細、利用人数を入力する
    form_data['layoutChildBody:childForm:inputDetailsItems:0:purpose'] = cfg['selected_purpose']
    form_data['layoutChildBody:childForm:inputDetailsItems:0:purposeDetails'] = 'テニス'
    form_data['layoutChildBody:childForm:inputDetailsItems:0:gname'] = 'テニスグループ'
    form_data['layoutChildBody:childForm:inputDetailsItems:0:useCnt'] = '4'
    # form_data['layoutChildBody:childForm:doConfirm'] = '送信'
    # 2023/03/12: Value値の変更
    form_data['layoutChildBody:childForm:doConfirm'] = '予約を確定する'
    # 不要なフォームデータを削除する
    ## 取り消しボタンの値を削除する
    if 'layoutChildBody:childForm:inputDetailsItems:0:doCancel' in form_data:
        del form_data['layoutChildBody:childForm:inputDetailsItems:0:doCancel']
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # ヘッダーのRefererを一部を書き換える
    headers['Referer'] = url
    # フォームデータを使って、「予約内容を確認する」ボタンをクリックする
    response = requests.post(cfg['cartdetails_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # レスポンスを返す
    return response

## 予約施設の確認内容のフォームデータを取得する
def get_formdata_rsvCartInputDetailsConfirm(response):
    """
    予約結果の最終確認ページのフォームデータを取得する
    """
    # 予約結果の最終確認ページのフォームデータは2番目
    _form_number = 1
    # フォームデータを取得する
    ( _form_data, _response_url ) = get_formdata_common(response, _form_number)
    # フォームデータを返す
    return ( _form_data, _response_url )

## 予約結果を確定するため、「予約を確定する」ボタンをクリックして、予約番号ページを表示する
@reserve_tools.elapsed_time
def confirm_reserve(cfg, cookies, headers, form_data, url):
    """
    予約施設の確認内容を表示して、「予約を確定する」ボタンをクリックして、予約確定する
    """
    global http_req_num
    # 不要なフォームデータを削除する
    ## お気に入りボタンの値を削除する
    if 'layoutChildBody:childForm:inputDetailsItems:0:doAddFavorite' in form_data:
        del form_data['layoutChildBody:childForm:inputDetailsItems:0:doAddFavorite']
    ## 修正するボタンの値を削除する
    if 'layoutChildBody:childForm:doDetails' in form_data:
        del form_data['layoutChildBody:childForm:doDetails']
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、予約を確定する
    response = requests.post(url, headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # レスポンスを返す
    return response

## 予約結果ページを解析して、予約番号を取得する
def get_confirmed_reserve_number(response, logger=None):
    """
    予約番号を取得し、予約を確認する
    """
    # フォームデータ(dict型)を初期化する
    _form_data = {}
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    _form = soup.find_all('form')[1]
    # フォームデータを取得する
    # divタグで、class属性がm-35のタグを抽出する
    _div_m35 = _form.find('div', class_='m-35')
    # 予約番号が発行されたかを確認し、発行されていない場合は終了する
    if _div_m35 is None:
        logger.warning(f'could not reserved.')
        return _form_data, None
    # 予約番号が発行されていたら、処理を続ける
    reserved_number = _div_m35.text
    # 数字部分のみ抽出する
    reserved_number = re.search(r'\d+', reserved_number).group()
    #print(f'reserved number: {reserved_number}')
    # inputタグで、value属性の値があるタグを抽出する
    _input_tags_with_value = _form.find_all('input', value=True)
    #print(_input_tags)
    #exit()
    for _tag in _input_tags_with_value:
        # name属性の値があるタグを対象とする
        if _tag.get('name') is not None:
            _form_data[_tag['name']] = _tag['value']
    # 最後の script ヘッダを抽出する
    _te = soup.find_all('script')[-1]
    # te-conditions 部分を抽出する
    _te_value = re.search('value=\'.+\'', _te.contents[0])
    # value=の文字列が含まれるので、これを削除してフォームデータに代入する
    _form_data['te-conditions'] = _te_value.group()[7:-1]
    # フォームデータを返す
    #print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    return _form_data, reserved_number

## ログイン前の事前準備する
@reserve_tools.elapsed_time
def prepare_reserve(cfg, userid, password, securityid, logger=None):
    """
    空きコートを予約するためにログインなどの事前準備を行う
    1. トップページにアクセスし、クッキーを取得する
    2. トップページのフォームデータを取得する
    3. ログインページにアクセスする
    4. ログインページのフォームデータを取得する
    5. ログインページで、ユーザーＩＤ、パスワードを入力して、マイページを表示する
    """
    # トップページにアクセスし、クッキーを取得する
    ( cookies, response ) = get_cookie_request(cfg, logger=logger)
    # トップページのフォームデータを取得する
    form_data = get_homeindex_formdata(response)
    # ログインページにアクセスする
    ( headers, response ) = login_request(cfg, cookies, form_data)
    # ログインページのフォームデータを取得する
    form_data = get_login_formdata(response)
    # ログインページで、ユーザーＩＤ、パスワードを入力して、マイページを表示する
    ( cookies, headers, response ) = input_userdata_in_login(cfg, userid, password, securityid, cookies, headers, form_data)
    return cookies, headers, response

## 空き予約リスト、希望日リスト、希望時間帯リスト、希望施設名リストより、予約対象リストを作成する
def create_target_reserves_list(reserves_list, want_date_list, want_hour_list, want_location_list, logger=None):
    """
    予約処理対象の希望日、希望時間帯のリストを作成する
    """
    # 希望日+希望時間帯のリストを初期化する
    target_reserves_list = {}
    # 空き予約リストから、空き予約日と値を取得する
    for _date, _d_value in reserves_list.items():
        # 空き予約日が希望日リストに含まれていない場合は次の空き予約日に進む
        if _date not in want_date_list:
            logger.debug(f'not want day: {_date}')
            continue
        # 空き予約時間帯とコートリストを取得する
        for _time, _court_list in _d_value.items():
            # 空き予約時間帯が希望時間帯リストに含まれていない場合は次の予約時間帯に進む
            if _time not in want_hour_list:
                logger.debug(f'not want hour: {_date} {_time}')
                # 1日1件のみ予約取得したい場合は continueのコメントを削除する
                #continue
            for _court in _court_list:
                # 空きコート名から、施設名とコート名に分割する
                _location_name = _court.split('／')[0]
                # 空き予約コートが希望施設名に含まれていない場合は次の空きコートに進む
                if _location_name not in want_location_list:
                    logger.debug(f'not want location: {_date} {_time} {_court}')
                    continue
                # 希望日+希望時間帯のリストに空き予約日がない場合は初期化後、時間帯を追加する
                if _date not in target_reserves_list:
                    target_reserves_list[_date] = []
                    target_reserves_list[_date].append(_time)
                    logger.debug(f'regist target reserves list: {_date} {_time} {_court}')
                # ある場合は時間帯を追加する
                else:
                    # 同じ時間帯がない場合は時間帯を追加する
                    if _time not in target_reserves_list[_date]:
                        target_reserves_list[_date].append(_time)
                        logger.debug(f'regist target reserves list: {_date} {_time} {_court}')
                    else:
                        # 次の時間帯に進む
                        logger.debug(f'found {_time} in target reserves list. therefore next time.')
                        # breakでコートのループを抜ける
                        break
            else:
                # _d_valueの次のループに進む
                continue
    # 希望日+希望時間帯のリストを返す
    #print(f'{target_reserves_list}')
    return target_reserves_list

### メインルーチン ###
@reserve_tools.elapsed_time
def lambda_handler(event, context):
    """
    メインルーチン
    """
    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 空き予約の辞書の初期化
    threadsafe_list = ThreadSafeReservesList()
    # 送信メッセージリストの初期化
    message_bodies = []
    # WEBリクエストのヘッダー
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
            }
    # HTTPリクエストデータ
    reqdata = []
    # 処理の開始
    # /tmpファイルに設定ファイルがあるか確認し、なければS3からファイルをダウンロードする
    reserve_tools.is_exist_files('nissy-jp-input', 'webscribe/tennis_reserve_search/kawasaki/cfg.json', 'webscribe/tennis_reserve_search/common/public_holiday.json')
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    #reserve_tools.set_public_holiday('public_holiday.json', public_holiday)
    reserve_tools.set_public_holiday('/tmp/public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = reserve_tools.read_json_cfg('/tmp/cfg.json')
    #print(f'cfg: {cfg}')
    # ロギングを設定する
    logger = reserve_tools.mylogger(cfg)
    # スレッド数を設定する
    threads_num = cfg['threads_num']
    # 検索対象月を取得する
    target_months_list = reserve_tools.create_month_list(cfg, logger=logger)
    # 検索年月日時間を取得する
    datetime_list = create_datetime_list(target_months_list, public_holiday, cfg, logger=logger)
    # threadsに応じたcookieとフォームデータを取得する
    reqdata = multi_thread_prepareproc(cfg, reqdata, threads=threads_num, logger=logger)
    # threadsに応じたスレッド数で利用日時検索ページで空き予約を検索する
    threadsafe_list = multi_thread_datesearch(cfg, datetime_list, threadsafe_list, reqdata, threads=threads_num, logger=logger)
    # 1回目で取得できなかった空き予約検索を再実行する。再実行は1回のみ実施する
    ## 再試行リストが0以外なら実行する
    if len(retry_datetime_list) != 0:
        logger.warning(f'下記の検索年月日時分でシステムエラーが発生したため、再検索します。検索回数は {len(retry_datetime_list)} 回です')
        logger.warning(f'datetime list : {retry_datetime_list}')
        threadsafe_list = multi_thread_datesearch(cfg, retry_datetime_list, threadsafe_list, reqdata, threads=threads_num, logger=logger)
    else:
        logger.warning(f'システムエラーは発生しませんでした')
    # 送信メッセージを作成する
    message_bodies = reserve_tools.create_message_body(threadsafe_list.reserves_list, message_bodies, cfg, logger=logger)
    # LINEに送信する
    # reserve_tools.send_line_notify(message_bodies, cfg['line_token'], logger=logger)
    # Discordに空き予約情報のメッセージを送信する
    reserve_tools.send_discord_channel(message_bodies, cfg['discord_token'], cfg['discord_channel_id'], logger=logger)
    # 空き予約リストに値があるかないかを判断し、予約処理を開始する
    #print(f'reserves_list: {threadsafe_list.reserves_list}')
    if len(threadsafe_list.reserves_list) == 0:
        logger.info(f'stop do reserve because no empty reserve.')
        #return logger
        return {
            'status': 200,
            'body': 'stop do reserve because no empty reserve.'
        }
    #return {
    #    'status': 200,
    #    'body': 'completed to check empty reserves.'
    #}
    # 予約希望日リストを作成する
    want_date_list = reserve_tools.create_want_date_list(target_months_list, public_holiday, cfg, logger=logger)
    # 希望時間帯を取得する
    want_hour_list = cfg['want_hour_list']
    # 希望施設名を取得する
    want_location_list = cfg['want_location_list']
    # 予約処理対象の希望日、希望時間帯のリストを作成する
    # 空き予約リストを昇順にソートする
    sorted_reserves_list = reserve_tools.sort_reserves_list(threadsafe_list.reserves_list)
    # 空き予約リストから、空き予約日と時間帯を取得する
    target_reserves_list = reserve_tools.create_target_reserves_list(sorted_reserves_list, want_date_list, want_hour_list, want_location_list, logger=logger)
    # 希望日+希望時間帯のリストを出力する
    logger.info(f'target_reserves_list: {target_reserves_list}')
    # 希望日+希望時間帯のリストが空の場合は予約処理を中止する
    if bool(target_reserves_list) == False:
        logger.info(f'reserve process stopped. because empty reserves is not wanted.')
        #return looger
        return {
            'status': 200,
            'body': 'reserve process stopped. because empty reserves is not wanted.'
        }
    # 複数IDに対応する
    userauth = cfg['userauth']
    ## タイプ毎のID:PASSリストを取得する
    for _type, _type_list in userauth.items():
        # タイプ別のID:PASSリストが空の場合は次のタイプに移る
        if not bool(_type_list):
            logger.info(f'{_type} type users list is empty.')
            continue 
        # 利用者ID毎に予約処理を開始する
        ## IDとパスワードを取得する
        for _userid, _credential in _type_list.items():
            _password = _credential['password']
            _securityid = _credential['securityid']
            logger.info(f'UserID:{_userid}, PASS:{_password}, SecurityID:{_securityid} is logined.')
            # ログインIDを使ってログインし、事前準備をする
            ( cookies, headers, response ) = prepare_reserve(cfg, _userid, _password, _securityid, logger=logger)
            # マイページから既存予約情報を取得する
            reserved_list = get_reserved_info(cfg, response, logger=logger)
            #exit()
            # 既存予約件数を取得する
            reserved_num = get_reserved_num(reserved_list, logger=logger)
            # 既存予約が予約上限数以上なら予約処理を中止する
            if reserved_num < int(cfg['reserved_limit']):
                logger.info(f'reserve proccess starting')
            else:
                logger.info(f'reserved number is limit of {cfg["reserved_limit"]}. therefore stop do reserve.')
                # 次の利用者IDで予約する
                continue
            #exit()
            # 利用日時から探すをクリックして、検索画面に移動する
            response = go_to_search_date_menu_with_userid(cfg, _userid, cookies, headers)
            ## フォームデータを取得する
            form_data = get_formdata_rsvDateSearch(response)
            # 希望日+希望時間帯のリストを元に空き予約を探し、予約処理を行う
            for _date, _time_list in target_reserves_list.items():
                for _time in _time_list:
                    # 追加した予約によって、既存予約件数が上限を超えている場合はメッセージを出して次の利用者IDを使う
                    if reserved_num >= int(cfg['reserved_limit']):
                        logger.info(f'reserve number is limit over {cfg["reserved_limit"]}. threfore stop reserve process.')
                        # 次の利用者IDで予約する
                        #return None
                        continue
                    # 改めてメッセージボディを初期化する
                    message_bodies = []
                    # 利用日時を入力して空きコート予約を検索する
                    #( reserved_number, reserve ) = search_empty_reserves_from_datesearch(cfg, cookies, form_data, "20210928", "14:00-16:00", reserves_list)
                    ( reserved_number, reserve ) = do_reserves_from_datesearch(cfg, cookies, form_data, _date, _time, logger=logger)
                    # 予約できなかった場合はreturn を返す
                    if reserved_number is None:
                        logger.warning(f'could not do reserve: {reserve}')
                        continue
                    # 予約確定通知のメッセージを作成する
                    message_bodies = reserve_tools.create_reserved_message(_userid, reserved_number, reserve, message_bodies, cfg, logger=logger)
                    # LINEに送信する
                    # reserve_tools.send_line_notify(message_bodies, cfg['line_token_reserved'], logger=logger)
                    # Discordに空き完了情報のメッセージを送信する
                    reserve_tools.send_discord_channel(message_bodies, cfg['discord_token'], cfg['discord_reserved_channel_id'], logger=logger)
                    # 予約件数に1件追加する
                    reserved_num += 1
                else:
                    continue
            else:
                continue
    # プログラムの終了
    #exit()
    #return logger
    return {
        'status': 200,
        'body': 'completed.'
    }

# if __name__ == '__main__':
#     # 実行時間を測定する
#     start = time.time()
#     print(f'HTTP リクエスト数 初期化: {http_req_num}')
#     logger = main()

#     # デバッグ用(HTTPリクエスト回数を表示する)
#     logger.info(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
#     # 実行時間を表示する
#     elapsed_time = time.time() - start
#     logger.info(f'whole() duration time: {elapsed_time} sec')

#     exit()
