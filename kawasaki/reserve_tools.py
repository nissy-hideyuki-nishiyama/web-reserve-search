# モジュールの読み込み
## カレンダー関連
from time import sleep
import math
import datetime
import calendar

## ファイルIO、ディレクトリ関連
import os

## JSON関連
import json

## WEBAPI関連
import requests

## 処理時間の計測関連
from functools import wraps
import time

# 設定ファイルの読み込み
## 祝日ファイル
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

## 設定ファイル
def read_json_cfg(cfg_file_name):
    """
    JSON形式の設定ファイルを読み込み、変数、リスト、dictを設定する
    """
    with open(cfg_file_name, mode='r', encoding='utf-8', errors='ignore' ) as json_cfg:
        cfg = json.load(json_cfg)
        #print(f'Config:\n')
        #print(cfg)
        return cfg

# requestsメソッドのレスポンスをHTMLファイルを保存する
def save_html_file(response):
    html = response.text
    print(f'save html file: output.html')
    with open('output.html', mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(html)

# requestsメソッドのレスポンスをHTMLファイルを保存する
def save_html_to_filename(response, filename):
    html = response.text
    #print(f'save html file: {filename}')
    with open(filename, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(html)

# aiohttp.requestsメソッドのレスポンスをHTMLファイルを保存する
def save_html_to_filename_for_aiohttp(response, filename):
    print(f'save html file: {filename}')
    with open(filename, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(response)

# 年越し処理
def check_new_year(month):
    """
    年月日が年越ししているか確認する
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
 
# 検索対象月のリストを作成する
def create_month_list(cfg):
    """
    検索対象月のリストを作成する
    今日の日付を取得し、当月、翌月のリストを作成する

    """
    # ふれあいネットの検索期間および起点日の設定
    month_num = cfg['month_period']
    start_day = cfg['start_day']
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
        _end_num = _start_num + month_num
        target_months = month_list[_start_num:_end_num]
    else:
        _end_num = _start_num + month_num - 1
        target_months = month_list[_start_num:_end_num]
    #print(f'{_start_num} , {_end_num}')
    # 検索対象月のタプルを作成する
    #target_months = month_list[_start_num:_end_num]
    #print(f'{target_months}')
    # 年越処理のために、年数に1を追加する
    #next_year = _now.year + 1
    return target_months

# 検索対象月の土曜日・日曜日・祝日・希望日のリストを作成する
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
    #print(f'{first_weekday}, {last_day}')
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

# 東京都多摩市向け
# 年月日(YYYYMMDD)の入力リストを作成する
def create_date_list(target_months_list, public_holiday, cfg):
    """ 
    入力データとなる年月日日時のリストを2次元配列で作成する
    """
    # 入力リストとして2次元配列を作成する
    date_list = []
    for _month in target_months_list:
        # 年越し確認
        _year = check_new_year(_month)
        # 対象月の日付リストを作成する
        target_days_list = create_day_list(_month, public_holiday, cfg)
        # 日付リストが空の場合は次の月の処理に移る
        if not target_days_list:
            continue
        # 入力リストに代入する
        for _day in target_days_list:
            # YYYYMMDDの文字列を作成する
            _date = str(_year) + str(_month).zfill(2) + str(_day).zfill(2)
            date_list.append(_date)
    #print(date_list)
    return date_list

# 調布市向け
# 監視対象日の年月日リストの2次元配列を作成する
def create_date_list_chofu(target_months_list, public_holiday, cfg):
    """
    ( year, month, day )の配列を作成する
    """
    # 希望曜日のリストを作成する
    # 入力リストとして2次元配列を作成する
    date_list = []
    # リストを作成するselected_weekdays = cfg['want_weekdays']
    for _month in target_months_list:
        # 年越し確認
        _year = check_new_year(_month)
        # 対象月の日付リストを作成する
        target_days_list = create_day_list(_month, public_holiday, cfg)
        # 日付リストが空の場合は次の月の処理に移る
        if not target_days_list:
            continue
        # 入力リストに代入する
        for _day in target_days_list:
            # リストを作成する
            #_date = [ _year , _month , _day ]
            _date = [ str(_year) , str(_month) , str(_day) ]
            date_list.append(_date)
    #print(date_list)
    return date_list

# 監視対象年月のリストを作成する
def create_year_month_list(target_month_list):
    """
    ( year, month )の配列を作成する
    """
    year_month_list = []
    for _month in (target_month_list):
        _year = check_new_year(_month)
        _year_month = [ _year , _month ]
        year_month_list.append(_year_month)
    return year_month_list

# 東京都八王子向け
# 年月日(YYYY/MM/DD)の入力リストを作成する
def create_date_list_hachioji(target_months_list, public_holiday, cfg):
    """ 
    入力データとなる年月日日時のリストを作成する
    """
    # 入力リストとして2次元配列を作成する
    date_list = []
    # 時分リストを初期化する
    for _month in target_months_list:
        # 年越し確認
        _year = check_new_year(_month)
        # 対象月の日付リストを作成する
        target_days_list = create_day_list(_month, public_holiday, cfg)
        # 日付リストが空の場合は次の月の処理に移る
        if not target_days_list:
            continue
        # 入力リストに代入する
        for _day in target_days_list:
            # YYYYMMDDの文字列を作成する
            _date = str(_year) + '/' + str(_month).zfill(2) + '/' + str(_day).zfill(2)
            date_list.append(_date)
    print(date_list)
    return date_list

# LINEに空き予約を送信する
## メッセージ本文の作成
def create_message_body(reserves_list, message_bodies, cfg):
    """
    LINEに送信するメッセージの本体を作成する
    """
    # LINEのメッセージ本体サイズ
    max_message_size=int(cfg['line_max_message_size'])
    # メッセージ本体
    _body = f'\n'
    _body_date = f'\n'
    #for key, value in reserve_name_listt.items():
    # 予約リストのキーである日付を取り出してた配列を作成する
    # マートガーデンの予約リストが日付順で格納されない場合があるため、処理を追加した
    _datelist = []
    for _date in reserves_list:
        _datelist.append(_date)
    # 日付順にソートした配列にする
    _sort_datelist = sorted(_datelist)
    #sorted_reserves_list = sorted(reserves_list.items(), key=lambda x:x[0])
    #print(sorted_reserves_list)
    #for _date, _time_list in sorted_reserves_list.items():
    for _date in _sort_datelist:
        # _time_listが空の場合(監視除外対象で追加せず、空となる場合がある)は次の時間帯に進む
        #if _time_list == {}:
        if reserves_list[_date] == {}:
            #print(f'reserve empty: {_date} {_time_list}')
            print(f'reserve empty: {_date} {reserves_list[_date]}')
            continue
        else:
            # 年月日文字列から曜日を判定し、末尾に曜日を付ける
            ( _dt, _wd ) = get_weekday_from_datestring(_date)
            _dt = _dt.date()
            _body = f'{_body}<{_dt}({_wd})>\n'
            _body_date = f'{_body_date}<{_dt}({_wd})>\n'
            #print(_date)
            #print(_time_list)
            #for _time, _court_list in _time_list.items():
            for _time, _court_list in sorted(reserves_list[_date].items()):
                _body = f'{_body}{_time}\n'
                _body_date = f'{_body_date}{_time}\n'
                #print(_time)
                #print(_court_list)
                for _court in _court_list:
                    _body = f'{_body}　{_court}\n'
                    #print(_court)
    # メッセージ本体の文字数を1000文字以内にする
    message_bodies.append(_body[:max_message_size])
    # メッセージ本体の文字数が1000より大きい場合は予約日時だけのメッセージ本体を作成する
    if len(_body) >= max_message_size:
        _body_date = f'\n空きコートが多いのでWEBでサイトで確かめてください。上記の時間帯に空きコートがあります。\n{_body_date}'
        message_bodies.append(_body_date)
    else:
        print(f'within {max_message_size} characters.')
    # デバッグ: 送信文本体と日付インデックスを表示する
    #print(_body)
    #print(_body_date)
    for _message in message_bodies:
        print(_message)
    return message_bodies


# LINEにメッセージを送信する
def send_line_notify(message_bodies, cfg):
    """
    LINE Notifyを使ってメッセージを送信する
    """
    #print(f'sending to LINE.')
    #print(message_bodies)
    #print(len(message_bodies[0]))
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


# 実行時間を計測する
def elapsed_time(f):
    """
    関数の処理時間を計測する
    """
    print(f"call elapsed_time.")
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        #print(f"start: {start}")
        v = f(*args, **kwargs)
        print(f"{f.__name__}: {time.time() - start}")
        return v
    return wrapper


# メインルーチン
def main():
    """
    メインルーチン
    """
    
if __name__ == '__main__':
    main()

