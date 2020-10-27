# HTML関連
import requests
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import exceptions
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from time import sleep

# ファイルIO、システム関連
import sys

# 正規表現
import re

# カレンダー関連
import math
import datetime
import calendar
#import locale

# JSONファイルの取り扱い
import json

# 祝日のリスト
#public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
#public_holiday[1] = [ 1, 13 ]
#public_holiday[2] = [ 24 ]
#public_holiday[3] = [ 20 ]
#public_holiday[4] = [ 29 ]
#public_holiday[5] = [ 4, 5, 6 ]
#public_holiday[7] = [ 23, 24 ]
#public_holiday[8] = [ 10 ]
#public_holiday[9] = [ 21, 22 ]
#public_holiday[11] = [ 3, 23 ]

def set_public_holiday(public_holiday_file_name, public_holiday):
    """
    祝日ファイルを読み込んで、祝日リストを設定する
    """
    # 祝日のリストを初期化する
    #public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 祝日ファイルを読み込んで祝日リストに日を要素として追加する
    with open(public_holiday_file_name, mode='r', encoding='utf-8', errors='ignore' ) as hdfile:
        json_hday = json.load(hdfile)
        for key, value in json_hday.items():
            _key = int(key)
            public_holiday[_key] = value
            #print(f'PublicHoliday_{key}: {public_holiday[_key]}')
        #print(public_holiday)
        return public_holiday

def read_json_cfg(cfg_file_name):
    """
    JSON形式の設定ファイルを読み込み、変数、リスト、dictを設定する
    """
    with open(cfg_file_name, mode='r', encoding='utf-8', errors='ignore' ) as json_cfg:
        cfg = json.load(json_cfg)
        #print(f'Config:\n')
        #print(cfg)
        return cfg

def check_new_year(month):
    """
    年越し判定
    入力された月を見て、これが現在の月よりも小さい場合、年越し処理として
    新しい年を戻り値として返す
    """
    _now = datetime.datetime.now()
    _this_year = _now.year
    _this_month = _now.month
    _today = _now.day
    if _this_month > month:
        year = _this_year + 1
    else:
        year = _this_year
    #print(f'Yert: {year}')
    return year
     
    
#def create_month_list(month_num=4, start_day=5):
def create_month_list(cfg):
    """
    検索対象月のリスト作成
    今日の日付を取得し、当月から検索対象期間の最終月のリストを作成する
    """
    # 月リスト
    month_list = ( 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6 )
    # 検索対象期間と起点日を設定する
    month_period = cfg['month_period']
    start_day = cfg['start_day']
    # 現在の時刻を取得し、検索対象月を取得する
    _now = datetime.datetime.now()
    _start_num = _now.month - 1
    # 予約開始日以降の場合は検索対象月を増やす
    if _now.day >= start_day:
        _end_num = _start_num + month_period
        target_months = month_list[_start_num:_end_num]
    else:
        _end_num = _start_num + month_period - 1
        target_months = month_list[_start_num:_end_num]
    #print(f'{_start_num} , {_end_num}')
    # 検索対象月のタプルを作成する
    #target_months = month_list[_start_num:_end_num]
    #print(f'{target_months}')
    # 年越処理のために、年数に1を追加する
    #next_year = _now.year + 1
    return target_months

def create_day_list(month, public_holiday, cfg):
    """
    検索対象月の土曜日・日曜日の日にちのリストを作成する
    当月の場合は今日以降の日にちのリストとする
    """
    # 希望曜日リストを作成する
    selected_weekdays = cfg['want_weekdays']
    # 祝日以外の希望日リストを作成する
    want_month_days = cfg['want_month_days'][str(month)]
    # 年越し確認をする
    year = check_new_year(month)
    # 対象日を格納するリストを初期化する
    day_list=[]
    # 対象月の初日の曜日と最終日とを取得する
    ( first_weekday , last_day ) = calendar.monthrange( year, month )
    # 当月の処理
    # 曜日比較で使う定数(ref_day)を変える
    # 当月なら今日の日付
    # それ以外なら0
    if month ==  datetime.datetime.now().month:
        _ref_day = datetime.datetime.now().day
    else:
        _ref_day = 0
    # 選択された曜日の日にちのリストを作成する
    for _wday in selected_weekdays:
        _day = _wday - first_weekday + 1
        while _day <= last_day:
            if _day > _ref_day:
                day_list.append(_day)
            _day += 7
    # 祝日の日をリストに追加する
    # 該当月の祝日が空なら追加しない
    if public_holiday[month]:
        for _holiday in public_holiday[month]:
            # 今日の日付より大きいなら追加する
            if _holiday > _ref_day:
                day_list.append(_holiday)
    # 希望対象日をリストに追加する
    # 該当月の希望対象日が空なら追加しない
    if want_month_days:
        for _want_day in want_month_days:
            # 今日の日付より大きいなら追加する
            if _want_day > _ref_day:
                day_list.append(_want_day)
    # 昇順でソートして日にちのリストを作る
    target_days = sorted(day_list)
    #print(target_days)
    return target_days


def create_date_string_list(target_months_list, public_holiday, cfg):
    """
    フィルターとして使う対象日(yyyymmdd)の文字列を作成し、配列に追加する
    """
    # フィルターとして使う文字列の配列の初期化
    date_string_list = []
    # 文字列を作成する
    for _month in target_months_list:
        # 年越し処理判定
        _year = check_new_year(_month)
        # 月の文字列を作成する。0詰めを行う
        str_month = '{:02d}'.format(_month)
        # 対象月の日付リストを作成する
        target_days_list = create_day_list(_month, public_holiday, cfg)
        # 日付リストが空の場合は次の月の処理に移る
        if not target_days_list:
            continue
        # 年月日の文字列を作成し、配列に代入する
        for _day in target_days_list:
            # 日の文字列を作成する。0詰めを行う
            str_day = '{:02d}'.format(_day)
            # 年月日の文字列を作成する
            date_string = f'{_year}{str_month}{str_day}'
            # 文字列の配列に追加する
            date_string_list.append(date_string)
        #print(f'date: {date_string_list}')
    # 全体の文字列を表示
    #print(f'All date string: {date_string_list}')
    return date_string_list
    
    
def create_inputdate(target_months_lists):
    """
    検索対象年月日の開始日と終了日を作成する
    """
    # 開始日を計算する
    _now = datetime.datetime.now()
    start_year = _now.year
    start_month = _now.month
    start_day = _now.day + 1
    # 終了時を計算する
    end_month = target_months_lists[-1]
    end_year = check_new_year( end_month )
    # その月の最終日を計算する
    ( _first_day, _last_day ) = calendar.monthrange( end_year, end_month )
    end_day = _last_day
    # 入力データの開始と終了の年月日のデータを作成する
    input_data_date = [ start_year, start_month, start_day, end_year, end_month, end_day ]
    #print(f'input_data_date: {input_data_date}')
    return input_data_date
    

#def create_inputdata(want_court_list, reserve_status, input_data_date):
def create_inputdata(cfg, input_data_date):
    """
    検索条件の入力データを作成する
    入力データの開始と終了の年月日のデータにコート番号と予約受付状態の値を追加する
    """
    # 検索対象の予約状態と検索対象コートを設定する
    reserve_status = cfg['reserve_status']
    want_court_list = cfg['want_court_list']
    # 入力データの初期化
    input_data = {}
    # 入力データの開始と終了の年月日のリストに連結する
    for key, value in want_court_list.items():
        #print(f'{key}')
        input_data[key] = input_data_date + [ value, reserve_status ]
        #print(input_data[key])
    #print(input_data)
    return input_data


def get_weekday_from_datestring(datestring):
    """
    年月日文字列からその日の曜日を取得し、戻り値として返す
    datestirngの型は、 yyyymmdd
    """
    # 年月日文字列から年、月、日を抽出する
    _year =  int(datestring[0:4])
    _month = int(datestring[4:6])
    _day = int(datestring[6:8])
    #print(f'{_year}-{_month}-{_day}')
    # 年月日オブジェクトを作成する
    dt = datetime.datetime(_year, _month, _day)
    # 曜日を取得する
    wd = dt.strftime('%a')
    #print(f'{dt}, {wd}')
    return dt, wd


def setup_driver():
    """
    seleniumを初期化する
    デバッグ時にはChromeの動作を目視確認するために、options.add_argi,emt行をコメントアウトする。
    ヘッドレスモードを利用する場合は、options.add_argi,emt行のコメントアウトを外す。
    """
    # Chromeを指定する
    options = webdriver.ChromeOptions()
    #options.binary_location = '/usr/bin/chromium-browser'
    options.binary_location = '/usr/lib64/chromium-browser/headless_shell'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    #driver = webdriver.Chrome('/opt/google/chromedriver/chromedriver', options=options)
    #driver = webdriver.Chrome('/usr/lib64/chromium-browser/headless_shell', options=options)
    #driver = webdriver.Chrome('/usr/lib64/chromium-browser/chromiumdriver', options=options)
    driver = webdriver.Chrome('/usr/local/bin/chromedriver', options=options)
    return driver

#def selenium_get_cookie(driver, first_url):
def selenium_get_cookie(driver, cfg):
    """
    selenuimuで接続する
    cookieおよび_ncforminfoの値を取得する
    トップページにアクセスし、これらを取得する
    """
    # トップページにアクセスする
    first_url = cfg['first_url']
    first_res = driver.get(first_url)
    sleep(1)
    cookie = driver.get_cookies()
    #print(cookie)
    # 初期検索結果のHTML本文を取得する
    _html = driver.page_source
    #print(f'html: {html}')
    # _ncforminfoの値を取得するため、html解析を実施する
    _soup = BeautifulSoup(_html, 'html.parser')
    _ncforminfo = _soup.select('input[type="hidden"][name="__ncforminfo"]')[0]
    ncforminfo_value = _ncforminfo['value']
    #print(f'ncforminfo: {ncforminfo_value}')
    # 画面のtitleを確認する
    assert '会員：ServiceAce>コートスケジュール表示画面' in driver.title
    #return cookie, ncforminfo_value

def selenium_post_conditions(driver, input_data, court_reserve_name_list):
    """
    取得したcookieおよび_ncforminfoの値を設定して、
    空き予約情報を取得する
    """
    # 待機時間を設定する
    wait = WebDriverWait(driver, 10)
    # 検索ページがすべて表示されるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    for key, value in input_data.items():
        #print(f'research: {key}: {value}')
        selenium_input_datas(driver, value)
        # 検索結果をHTMLファイルとして保存する
        _html = driver.page_source
        # デバッグ用にHTMLファイルを保存する
        #save_result_html(_html, f'martgd_empty_reserves_{key}.html')
        sleep(5)
        # HTML解析を実行し、空き予約名リストを作成する
        court_reserve_name_list[key] = analize_html(key, _html)
    # 空き予約名リストを表示する
    #print(f'Court_Reserve_List:\n{court_reserve_name_list}')
    return court_reserve_name_list

def selenium_input_datas(driver, input_data_value):
    """
    検索条件を入力する
    """
    # 選択する予約状態リストを取得する
    _status_list = input_data_value[7]
    # 検索フォームのフィールド設定
    src_year1 = Select(driver.find_element_by_name('src_year1'))
    src_month1 = Select(driver.find_element_by_name('src_month1'))
    src_day1 = Select(driver.find_element_by_name('src_day1'))
    src_year2 = Select(driver.find_element_by_name('src_year2'))
    src_month2 = Select(driver.find_element_by_name('src_month2'))
    src_day2 = Select(driver.find_element_by_name('src_day2'))
    src_court_id = Select(driver.find_element_by_name('src_court_id'))
    #srcLotStatus = Select(driver.find_element_by_name('srcLotStatus[]'))
    # 検索キーの送信
    src_year1.select_by_value(str(input_data_value[0]))
    src_month1.select_by_value(str(input_data_value[1]))
    src_day1.select_by_value(str(input_data_value[2]))
    src_year2.select_by_value(str(input_data_value[3]))
    src_month2.select_by_value(str(input_data_value[4]))
    src_day2.select_by_value(str(input_data_value[5]))
    src_court_id.select_by_value(str(input_data_value[6]))
    # 予約受付のチェックボックスをクリックする
    for _status in _status_list:
        # find_element_by_xpathの引数を作成する
        _xpath_str = f'.//input[@type=\'checkbox\'][@name=\'srcLotStatus[]\'][@value=\'{_status}\']'
        _status = driver.find_element_by_xpath(_xpath_str)
        if _status.is_selected() == False:
            _status.click()
    # 検索ボタンをクリックする
    driver.find_element_by_xpath(".//input[@type='button'][@value=' 検　索 '][@onclick='search_click();']").click()
    #sleep(30)
    # 検索結果がすべて表示されるまで待機する
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_all_elements_located)
    # 画面のtitleを確認する
    assert '会員：ServiceAce>コートスケジュール表示画面' in driver.title
    #return cookie, ncforminfo_value

    
def save_result_html(html, file_name):
    """
    検索結果のHTMLをファイルとしてローカルに保存する
    デバッグ用
    """
    print(f'save file: {file_name}')
    with open(file_name, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(html)
    return file_name

    
#def analize_html(court, file_name):
def analize_html(court, html):
    """
    取得した空き予約情報から土日祝の空き予約情報をフィルタする
    """
    #with open(file_name, mode='r', encoding='utf-8', errors='ignore') as shtml:
    # 空き予約名リストの初期化
    reserve_name_list = {}
    #soup =BeautifulSoup(shtml.read(), "html.parser")
    soup =BeautifulSoup(html, "html.parser")
    # formタグ毎に要素を抽出する
    elems = soup.find_all("form", action="https://reserve.lan.jp/mtg/web")
    # formタグ範囲内で抽出する
    for _form in elems:
        # formタグ内のname属性(年月日の文字列)を取得する
        _date = re.sub("form_", "", _form['name'])
        # 予約時間帯の文字列とコート番号を取得する
        _reserve_list = _form.find_all("td", class_="data")
        # 予約時間帯の文字列のみ取得するため、コート番号および制御文字を削除して整形する
        for _reserve in _reserve_list:
            # 時間帯の文字列を取得するため、コート番号を削除(空文字列になる)し、制御文字列を削除して整形する
            _str = re.sub("[CDE\n\t ]", "", _reserve.contents[0])
            # 時間帯の文字列なら予約名リストに追加する
            if len(_str) > 0:
                reserve_name_list.setdefault(_date, []).append(_str)
    #print(f'{court}: reserve_name_list')
    #print(reserve_name_list)
    return reserve_name_list
    
def create_selected_reserve_list(court_reserve_name_list, selected_reserve_name_list, cfg, date_string_list):
    """
    希望時間帯および希望日のみ抽出したリストを作成する
    """
    # 希望時間帯を設定する
    want_time_list = cfg['want_time_list']
    # 希望日のみ抽出した予約名リストを作成する
    # コート別に空き予約名リストを取得する
    for _court, _date_reserves in court_reserve_name_list.items():
        #print(f'court_name: {_court}')
        # 年月日検索用文字列を土日祝日リストから複製する
        #_selected_reserve_name_list = {}
        _date_string_list = date_string_list
        # 年月日別に空き予約名リストを取得する
        for _day, _reserves in _date_reserves.items():
            #print(f'found day: {_day}')
            # 希望時間帯検索用文字列を希望時間帯リストから複製する
            _want_time_list = want_time_list
            # 希望日リストの日にちと一致したら
            for _want_day in _date_string_list:
                if _day == _want_day:
                    #print(f'day: {_day}')
                    #_date_string_list.pop(0)
                    # 希望日の予約名リストから希望時間帯のみ抽出する
                    for _want_time in _want_time_list:
                        for _reserve in _reserves:
                            #print(f'want_time: {_want_time}')
                            #print(f'reserve_string: {_reserve}')
                            if str(_want_time) == str(_reserve):
                                #print(f'{_court}:{_day}:{_reserve}')
                                # 希望時間帯と一致した予約を希望予約名リストに追加する
                                selected_reserve_name_list.setdefault(_day, []).append(f'{_reserve} {_court}コート')
                            # 一致しない場合は次の処理のループに移動する
                            else:
                                continue
                # 一致しない場合は平日なので、次の処理のループに移動する
                else:
                    continue
        #selected_reserve_name_list = _selected_reserve_name_list
    #print(f'selected_reserve_name_list:\n')
    #print(selected_reserve_name_list)
    return selected_reserve_name_list

    
#def create_mesage_body(selected_reserve_name_list, message_bodies, line_max_message_size):
def create_mesage_body(selected_reserve_name_list, message_bodies, cfg):
    """
    メッセージ本体を作成する
    """
    # 最大メッセージサイズを設定する
    line_max_message_size = cfg['line_max_message_size']
    # メッセージ本体を初期化する
    _body = f'\n'
    _body_datetime = f'\n'
    # ditcをkeyで照準に並べ替える。ditから配列[(day, [reserves]), (...)]になる
    sorted_selected_reserve_name_list = sorted(selected_reserve_name_list.items())
    #print(type(sorted_selected_reserve_name_list))
    #print(dir(sorted_selected_reserve_name_list))
    #print(sorted_selected_reserve_name_list)
    # メッセージ本体を作成する
    for _day_reserves in sorted_selected_reserve_name_list:
        # 年月日文字列から曜日を判定し、末尾に曜日を付ける
        ( _dt, _wd ) = get_weekday_from_datestring(_day_reserves[0])
        _dt = _dt.date()
        _body = f'{_body}{_dt}({_wd})\n'
        _body_datetime = f'{_body}{_dt}({_wd})\n'
        # 時間単位にソートしてからループする
        for _reserve in sorted(_day_reserves[1]):
            _body = f'{_body}{_reserve}\n'
        _body = f'{_body}\n'
    # メッセージを表示する
    # メッセージ本体の文字数を1000文字以内にする
    message_bodies.append(_body[:line_max_message_size])
    # メッセージ本体の文字数が1000より大きい場合は予約日時だけのメッセージ本体を作成し、2通目のメッセージとする
    if len(_body) >= line_max_message_size:
        _body_datetime = f'{_body_datetime}空きコートが多いのでWEBでサイトで確かめてください。上記の時間帯に空きコー>トがあります。'
        message_bodies.append(_body_datetime)
    #else:
    #    print(f'within 1000 characters.')
    # メッセージ本体のリストを返す
    for _message in message_bodies:
        print(_message)
    return message_bodies


#def send_line_notify(message_bodies, line_token):
def send_line_notify(message_bodies, cfg):
    """
    LINE Notifyでメッセージを送信する
    """
    # LINEトークン、APIのURLを設定する
    line_notify_token = cfg['line_token']
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    # メッセージの長さが1(\n分)の場合はコンソールに空き予約がないメッセージを表示する
    if len(message_bodies[0]) > 1:
        for _message in message_bodies:
            data = {'message': f'{_message}'}
            requests.post(line_notify_api, headers = headers, data = data)
            sleep(1)
        print(f'sent empty reserves.')
    else:
        # 空き予約がない場合もメッセージを送信する
        #data = {'message': f'空き予約はありませんでした'}
        #requests.post(line_notify_api, headers = headers, data = data)
        print(f'not found empty reserves.')
    
    
def main():
    """
    メインルーチン
    """
    # 初期値
    # マートガーデン予約サーバの情報
    #first_url = 'https://reserve.lan.jp/mtg/hp/court_schedule.php?id=1'
    #search_url = 'https://reserve.lan.jp/js/admin.js'
    #cookie_name = 'PHPSESSID'
    # 予約受付状態(入力データに利用する)
    #reserve_status = 3  # 予約受付中
    # 希望コート番号(入力データに利用する)
    # A:1
    # B:2
    # C:3
    # D:4
    # E:7
    #want_court_list = { 'C': 3, 'D': 4, 'E': 7 }
    
    # 希望時間帯(フィルターに利用する)
    #want_time_list = [ '08:00～10:00', '10:00～12:00', '12:00～14:00', '14:00～16:00' ]

    # LINE notifyの通知先Token
    # 個人向けNotify Token
    #line_token = '1PyWFO9iaqPHHw1ibHT04k1FitSPt5zGc9KpUZ32NNQ'
    # PowerChot向けのLINEグループ
    #line_token = 'ksSMNGG8qXXbkL89GXAF5Ot2WWwnmGMZ9zoY8WNRHJN'
    # LINEのメッセージサイズの上限
    #line_max_message_size = 1000

    # 希望曜日(フィルターに利用する)
    # 月曜日: 0
    # 火曜日: 1
    # 水曜日: 2
    # 木曜日: 3
    # 金曜日: 4
    # 土曜日: 5
    # 日曜日: 6
    #selected_weekdays = [ 5 , 6 ]

    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]

    # 入力データの辞書の初期化
    input_data = {}

    # 空き予約名リストの初期化
    court_reserve_name_list = {}
    selected_reserve_name_list = {}
    # 送信メッセージの初期化
    message_bodies = []

    # WEBリクエストのヘッダー
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
            }

    # 処理の開始
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    set_public_holiday('public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = read_json_cfg('cfg.json')
    # 検索対象月のリストを作成する
    #target_months_list = create_month_list(month_num=4, start_day=5)
    target_months_list = create_month_list(cfg)
    # 検索対象の開始日と終了日のリストを作成する
    input_data_date = create_inputdate(target_months_list)
    # 検索データを作成する
    #input_data = create_inputdata(want_court_list, reserve_status, input_data_date)
    input_data = create_inputdata(cfg, input_data_date)
    # フィルターリストを作成する
    #date_string_list = create_date_string_list(target_months_list, selected_weekdays, public_holiday, cfg)
    date_string_list = create_date_string_list(target_months_list, public_holiday, cfg)
    #exit()
    # seleniumの初期化
    driver = setup_driver()
    # トップページにアクセスする
    #( cookie_value, ncforminfo_value ) = get_cookie(first_url, cookie_name)
    #post_conditions(input_data, search_url, cookie_value, ncforminfo_value)
    #selenium_get_cookie(driver, first_url)
    selenium_get_cookie(driver, cfg)
    # 検索条件を入力して、空き情報のHTMLを取得し、空き予約名リストを作成する
    court_reserve_name_list = selenium_post_conditions(driver, input_data, court_reserve_name_list)
    
    # デバッグ用　取得しているHTMLファイルからリストを作成する
    #court_reserve_name_list['C'] = analize_html('C', 'martgd_empty_reserves_C.html')
    #court_reserve_name_list['D'] = analize_html('D', 'martgd_empty_reserves_D.html')
    #court_reserve_name_list['E'] = analize_html('E', 'martgd_empty_reserves_E.html')
    #print(f'\n\ncourt_reserve_name_list:\n{court_reserve_name_list}')
    
    # seleniumを終了する
    driver.quit()
    # 空き予約名リストから希望時間帯のみを抽出したリストを作成する
    #selected_reserve_name_list = create_selected_reserve_list(court_reserve_name_list, selected_reserve_name_list, want_time_list, date_string_list)
    selected_reserve_name_list = create_selected_reserve_list(court_reserve_name_list, selected_reserve_name_list, cfg, date_string_list)
    # 送信メッセージ本体を作成する
    #messages = create_mesage_body(selected_reserve_name_list, message_bodies, line_max_message_size)
    messages = create_mesage_body(selected_reserve_name_list, message_bodies, cfg)
    # LINE Notifyに空き予約情報のメッセージを送信する
    #send_line_notify(message_bodies, line_token)
    send_line_notify(message_bodies, cfg)
    # 終了する
    exit()
 
if __name__ == '__main__':
    main()
    
