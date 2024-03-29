# 空きコート予約をする

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

# JSONファイルの取り扱い
import json

# URLの'/'が問題になるためハッシュ化する
from hashlib import md5
from pathlib import Path

# ツールライブラリを読み込む
import reserve_tools

# 検索結果ページの表示件数
page_unit = 5

# HTTPリクエスト回数
http_req_num = 0

# 予約時間帯のリストを作成する。フォームデータのHTML解析でindex番号として使う
tzone = [ 9, 12, 14, 16, 18 ]

# 年月日時分の入力リストを作成する
@reserve_tools.elapsed_time
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
                # 開始時刻が9時の場合は3時間後とする
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
@reserve_tools.elapsed_time
def get_cookie_request(cfg):
    """
    cookieを取得する
    """
    global http_req_num
    # セッションを開始する
    session = requests.session()
    response = session.get(cfg['first_url'])
    #exit()
    http_req_num += 1
    # cookie情報を初期化し、次回以降のリクエストでrequestsモジュールの渡せる形に整形する
    cookies = {}
    cookies[cfg['cookie_name_01']] = response.cookies.get(cfg['cookie_name_01'])
    cookies[cfg['cookie_name_02']] = response.cookies.get(cfg['cookie_name_02'])
    #cookies[cfg['cookie_name_03']] = response.cookies.get(cfg['cookie_name_03'])
    #cookies[cfg['cookie_name_04']] = cfg['userid']
    #print(json.dumps(cookies, indent=2))
    #print(response.text)
    #exit()
    return cookies , response

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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
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
    _file_name = f'login.html'
    #print(_file_name)
    _file = reserve_tools.save_html_to_filename(response, _file_name)
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
def input_userdata_in_login(cfg, cookies, headers, form_data):
    """
    ログインページでユーザーIDとパスワード、セキュリティ番号を入力し、マイページに移動する
    """
    global http_req_num
    # headers = {
    #     'Origin': cfg['origin_url'],
    #     'Referer': cfg['mypindex_url'],
    #     'Content-Type': 'application/x-www-form-urlencoded',
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
    # }
    _form_data = form_data
    # ユーザーIDとパスワード、セキュリティ番号を入力する
    _form_data['layoutChildBody:childForm:userid'] = cfg['userid']
    _form_data['layoutChildBody:childForm:passwd'] = cfg['password']
    _form_data['layoutChildBody:childForm:securityno'] = cfg['securityid']
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、マイページを表示する
    response = requests.post(cfg['mypindex_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'mypage.html'
    _file = reserve_tools.save_html_to_filename(response, _file_name)
    # ログインしたことによりcookieが再発行されるので、cookiesを更新する
    cookies[cfg['cookie_name_01']] = response.cookies.get(cfg['cookie_name_01'])
    # 次のPOSTリクエストのためにヘッダーを作成する
    headers['Referer'] = f'{response.url}'
    return cookies, headers, response

## マイページから既存予約情報を取得する
#def get_reserved_info(cfg):
def get_reserved_info(cfg, response):
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
        print(f'No Reserves Entry')
        return _reserved_list
    # 既存予約情報がある場合は予約情報を取得する
    _div = soup.find('div', id="isNotEmptylist")
    #print(_div)
    #_tr = _div.table.contents
    _tr = _div.find_all('tr')
    #print(_tr)
    # 既存予約件数を計算する
    reserves_num = int( ( len(_tr) - 1 ) / 2 )
    print(f'reserves_num : {reserves_num}')
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
    print(json.dumps(_reserved_list, indent=2, ensure_ascii=False))
    return _reserved_list

# 既存予約件数を取得する
def get_reserved_num(reserved_list):
    """
    既存予約件数を取得する
    """
    _reserved_num = 0
    for _date, _date_value in reserved_list.items():
        for _time, _court_list in _date_value.items():
            for _court in _court_list:
                _reserved_num += 1
    # 予約件数を返す
    print(f'reserved num: {_reserved_num}')
    return _reserved_num

## 利用日時から探すをクリックして、検索画面に移動する
@reserve_tools.elapsed_time
def go_to_search_date_menu_with_userid(cfg, cookies, headers):
    """
    施設の空き状況検索の利用日時からのリンクをクリックして、検索画面に移動する
    """
    global http_req_num
    headers = {
        'Host': 'www.fureai-net.city.kawasaki.jp',
        'Referer': headers['Referer'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
    }
    # クッキーにユーザーIDを追加する    
    cookies[cfg['cookie_name_04']] = str(cfg['userid'])
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
def do_reserves_from_datesearch(cfg, cookies, form_data, date, time):
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
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
    _file_name = f'result_{_datetime_string}.html'
    reserve_tools.save_html_to_filename(response, _file_name)
    # 次のリクエストでレスポンスヘッダーのURLの値をRefererとして使うため、これを取得する
    _location_url = response.url
    headers['Referer'] = f'{_location_url}'
    # 空き予約コートページのフォームデータと空き施設名、空きコート名を取得する
    ( rsv_form_data, court_list ) = get_formdata_rsvEmptyState(response)
    # 空き予約を予約カートに追加し、フォームデータと追加した空き施設名と空きコート名を取得する
    ( added_response, court, matched_flag ) = add_reserve_to_cart(cfg, cookies, headers, rsv_form_data, court_list, tzone_index)
    # 空き予約コートが希望日・時間帯・施設名に一致したフラッグを確認し、False(一致しない)ならreturnを返す
    if matched_flag == False:
        reserved_number = None
        reserve = None
        return reserved_number, reserve
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'result_add_reserve_{_datetime_string}.html'
    reserve_tools.save_html_to_filename(added_response, _file_name)
    # 予約をカートに追加済みのフォームデータを取得する
    ( added_form_data, court_list ) = get_formdata_rsvEmptyState(added_response)
    # 予約カートの内容を確認する
    cart_response = display_reserve_cart(cfg, cookies, headers, added_form_data, court_list)
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'result_cart_reserve_{_datetime_string}.html'
    reserve_tools.save_html_to_filename(cart_response, _file_name)
    # 予約カートのフォームを取得する
    cart_form_data = get_formdata_rsvCartList(cart_response)
    # 「予約確定の手続きへ」ボタンをクリックして、予約確定の手続きをする
    reserve_response = doing_reserve(cfg, cookies, headers, cart_form_data)
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'result_do_reserve_{_datetime_string}.html'
    reserve_tools.save_html_to_filename(reserve_response, _file_name)
    # 予約施設の確認内容のフォームデータを取得する
    reserve_form_data = get_formdata_rsvCartDetails(reserve_response)
    # 「予約内容を確認する」ボタンをクリックする
    input_response = input_reserve(cfg, cookies, headers, reserve_form_data)
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'result_input_reserve_{_datetime_string}.html'
    reserve_tools.save_html_to_filename(input_response, _file_name)
    # フォームデータを取得する
    confirm_form_data = get_formdata_rsvCartInputDetailsConfirm(input_response)
    # 「予約確定」ボタンをクリックする
    confirm_response = confirm_reserve(cfg, cookies, headers, confirm_form_data)
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'result_confirm_reserve_{_datetime_string}.html'
    reserve_tools.save_html_to_filename(confirm_response, _file_name)
    # 予約番号を取得する
    ( reserved_number_form_data, reserved_number ) = get_confirmed_reserve_number(confirm_response)
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
def add_reserve_to_cart(cfg, cookies, headers, form_data, court_list, tzone_index):
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
                #print(f'want location : {_want_location}')
                #print(f'found court name: {_court}')
                if _want_location == _location:
                    # 一致したコートに対するコートリストのindex番号を取得する
                    _want_index = court_list.index(_court)
                    # 次ページ検索フラッグをTrueにする
                    _matched = True
                    # whileループを抜けるため、_offsetを_allcountより大きくする
                    _offset = _allcount + page_unit
                    print(f'matched {_court} : court_index: {_want_index}')
                    break
        if _matched == False:
            # フォームデータのoffset値に5を追加して、次の予約を取得するため、POSTする
            _offset += page_unit
            # _offset値が_allcountを超えたら検索をwhileループを抜ける
            if _offset > _allcount:
                break
            # 一致したコートがない場合は次の空き予約ページに進む
            print(f'not found want court. next empty court page.')
            form_data['layoutChildBody:childForm:offset'] = str(_offset)
            response = search_next_empty_reserves_from_emptystate(cfg, cookies, headers, form_data)
            # 取得したレスポンスのフォームデータを取得する
            ( form_data, court_list ) = get_formdata_rsvEmptyState(response)
    # 希望する空きコートが見つからなかった場合はreturnする
    if _matched == False:
        print(f'not found want date time location. therefore this sript is finished')
        response = None
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
#@reserve_tools.elapsed_time
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
    del form_data['layoutChildBody:childForm:jumpRsvCartList']
    #print(form_data)
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、空き予約を検索する
    response = requests.post(cfg['empty_state_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # デバッグ用としてhtmlファイルとして保存する
    _datetime_string = str(datetime[0]) + str(datetime[1]).zfill(2) + str(datetime[2]).zfill(2) + str(datetime[3]).zfill(2) + str(datetime[4]).zfill(2)
    _file_name = f'result_{_datetime_string}.html'
    #print(_file_name)
    _file = reserve_tools.save_html_to_filename(response, _file_name)
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
    return _form_data

## 予約カートのフォームデータを取得する
def get_formdata_rsvCartList(response):
    """
    予約カートのフォームデータを取得する
    """
    # 予約カートのフォームデータは4番目
    _form_number = 3
    # フォームデータを取得する
    _form_data = get_formdata_common(response, _form_number)
    # フォームデータを返す
    return _form_data

## 予約内容の手続きをする
@reserve_tools.elapsed_time
def doing_reserve(cfg, cookies, headers, form_data):
    """
    「予約確定の手続き」ボタンをクリックする
    """
    global http_req_num
    # 不要なフォームデータを削除する
    ## 取り消しボタンの値を削除する
    del form_data['layoutChildBody:childForm:inputDetailsItems:0:doCancel']
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、カートに予約を追加する
    response = requests.post(cfg['cartlist_url'], headers=headers, cookies=cookies, data=params)
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
    _form_data = get_formdata_common(response, _form_number)
    # フォームデータを返す
    return _form_data

## 予約内容を入力して、「予約内容を確認する」ボタンをクリックして、予約結果を表示する
@reserve_tools.elapsed_time
def input_reserve(cfg, cookies, headers, form_data):
    """
    予約内容を入力して、「予約内容を確認する」ボタンをクリックして、予約結果を表示する
    予約内容: 利用目的、目的の詳細、利用人数
    """
    global http_req_num
    # 利用目的、目的の詳細、利用人数を入力する
    form_data['layoutChildBody:childForm:inputDetailsItems:0:purpose'] = cfg['selected_purpose']
    form_data['layoutChildBody:childForm:inputDetailsItems:0:purposeDetails'] = 'テニス'
    form_data['layoutChildBody:childForm:inputDetailsItems:0:useCnt'] = '4'
    # 不要なフォームデータを削除する
    ## 取り消しボタンの値を削除する
    del form_data['layoutChildBody:childForm:inputDetailsItems:0:doCancel']
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、カートに予約を追加する
    response = requests.post(cfg['cartdetails_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # レスポンスを返す
    return response

## 予約結果の最終確認ページのフォームデータを取得する
def get_formdata_rsvCartInputDetailsConfirm(response):
    """
    予約結果の最終確認ページのフォームデータを取得する
    """
    # 予約結果の最終確認ページのフォームデータは2番目
    _form_number = 1
    # フォームデータを取得する
    _form_data = get_formdata_common(response, _form_number)
    # フォームデータを返す
    return _form_data

## 予約結果を確定するため、「予約の確定をする」ボタンをクリックして、予約番号ページを表示する
@reserve_tools.elapsed_time
def confirm_reserve(cfg, cookies, headers, form_data):
    """
    予約内容を入力して、「予約内容を確認する」ボタンをクリックして、予約結果を表示する
    予約内容: 利用目的、目的の詳細、利用人数
    """
    global http_req_num
    # 不要なフォームデータを削除する
    ## お気に入りボタンの値を削除する
    del form_data['layoutChildBody:childForm:inputDetailsItems:0:doAddFavorite']
    ## 修正するボタンの値を削除する
    del form_data['layoutChildBody:childForm:doDetails']
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # フォームデータを使って、カートに予約を追加する
    response = requests.post(cfg['cartconfirm_url'], headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # レスポンスを返す
    return response

## 予約結果ページを解析して、予約番号を取得する
def get_confirmed_reserve_number(response):
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
    # divタグで、classzo属性がm-35のタグを抽出する
    _div_m35 = _form.find('div', class_='m-35')
    # 予約番号が発行されたかを確認し、発行されていない場合は終了する
    if _div_m35 is None:
        print(f'could not reserved.')
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

## ログイン前の事前準備する
def prepare_reserve(cfg):
    """
    空きコートを予約するためにログインなどの事前準備を行う
    1. トップページにアクセスし、クッキーを取得する
    2. トップページのフォームデータを取得する
    3. ログインページにアクセスする
    4. ログインページのフォームデータを取得する
    5. ログインページで、ユーザーＩＤ、パスワードを入力して、マイページを表示する
    """
    # トップページにアクセスし、クッキーを取得する
    ( cookies, response ) = get_cookie_request(cfg)
    # トップページのフォームデータを取得する
    form_data = get_homeindex_formdata(response)
    # ログインページにアクセスする
    ( headers, response ) = login_request(cfg, cookies, form_data)
    # ログインページのフォームデータを取得する
    form_data = get_login_formdata(response)
    # ログインページで、ユーザーＩＤ、パスワードを入力して、マイページを表示する
    ( cookies, headers, response ) = input_userdata_in_login(cfg, cookies, headers, form_data)
    return cookies, headers, response


## メイン
def main():
    """
    空きコートを予約する
    """
    """
    メインルーチン
    """
    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 空きコート予約の初期化
    reserves_list = {}
    # 送信メッセージリストの初期化
    message_bodies = []
    # 処理の開始
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    reserve_tools.set_public_holiday('public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = reserve_tools.read_json_cfg('cfg3.json')
    # 検索対象月を取得する
    target_months_list = reserve_tools.create_month_list(cfg)
    # 検索年月日時間を取得する
    #datetime_list = create_datetime_list(target_months_list, public_holiday, cfg)
    # 予約希望日リストを作成する
    want_date_list = reserve_tools.create_want_date_list(target_months_list, public_holiday, cfg)
    # ログイン前の事前準備する
    """
    空きコートを予約するためにログインなどの事前準備を行う
    1. トップページにアクセスし、クッキーを取得する
    2. トップページのフォームデータを取得する
    3. ログインページにアクセスする
    4. ログインページのフォームデータを取得する
    5. ログインページで、ユーザーＩＤ、パスワードを入力して、マイページを表示する
    """
    ( cookies, headers, response ) = prepare_reserve(cfg)
    # マイページから既存予約情報を取得する
    reserved_list = get_reserved_info(cfg, response)
    # 既存予約件数を取得する
    reserved_num = get_reserved_num(reserved_list)
    #exit()
    # 利用日時から探すをクリックして、検索画面に移動する
    response = go_to_search_date_menu_with_userid(cfg, cookies, headers)
    ## フォームデータを取得する
    form_data = get_formdata_rsvDateSearch(response)
    # 利用日時を入力して空きコート予約を検索する
    ( reserved_number, reserve ) = do_reserves_from_datesearch(cfg, cookies, form_data, "20210928", "12:00-14:00")
    # 予約できなかった場合はreturn を返す
    if reserved_number is None:
        print(f'could not do reseve: {reserve}')
        return None
    # 予約確定通知のメッセージを作成する
    message_bodies = create_reserved_message(reserved_number, reserve, message_bodies, cfg)
    # LINEに送信する
    reserve_tools.send_line_notify(message_bodies, cfg)
    # プログラムの終了
    #exit()
    return None

if __name__ == '__main__':
    # 実行時間を測定する
    start = time.time()
    print(f'HTTP リクエスト数 初期化: {http_req_num}')
    main()

    # デバッグ用(HTTPリクエスト回数を表示する)
    print(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - start
    print(f'whole() duration time: {elapsed_time} sec')

    exit()



