# モジュールの読み込み
## カレンダー関連
from time import sleep
import math
import datetime
#from datetime import datetime, date, timedelta 
import calendar
from dateutil.relativedelta import relativedelta

## ファイルIO、ディレクトリ関連　
import os
import sys
import subprocess
import pathlib

# 正規表現
import re

## JSON関連
import json

## WEBAPI関連
import requests

## 処理時間の計測関連
from functools import wraps
import time

# ログ関連
from logging import (
    getLogger,
    StreamHandler,
    Formatter,
    DEBUG, INFO, WARNING, ERROR, CRITICAL
)
from logging.handlers import RotatingFileHandler

# AWS boto
import boto3
import botocore

# Discord関連
import asyncio
import discord

# S3クライアント
s3 = boto3.resource('s3')

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

# loggerの設定
def mylogger(cfg):
    """
    ロガーを定義し、ロガーのインスタンスを返す
    """
    # cfg から設定パラメータを取り出す
    _logfile_path = cfg['logger_conf']['logfile_path']
    _level_fh = cfg['logger_conf']['level_filehandler']
    _level_sh = cfg['logger_conf']['level_consolehandler']
    _logsize_maxbytes = cfg['logger_conf']['logsize_maxbytes']
    _backup_count = cfg['logger_conf']['backup_count']
    #ロガーの生成
    logger = getLogger('mylog')
    #出力レベルの設定
    logger.setLevel(DEBUG)
    #ハンドラの生成
    #fh = FileHandler(_logfile_path)
    fh = RotatingFileHandler(_logfile_path, mode='a', maxBytes=_logsize_maxbytes, backupCount=_backup_count)
    sh = StreamHandler(sys.stdout)
    # ハンドラーのレベルを設定
    ## ファイルハンドラーのレベル設定
    if _level_fh == 'CRITICAL':
        fh.setLevel(CRITICAL)
    elif _level_fh == 'ERROR':
        fh.setLevel(ERROR)
    elif _level_fh == 'INFO':
        fh.setLevel(INFO)
    elif _level_fh == 'DEBUG':
        fh.setLevel(DEBUG)
    else:
        fh.setLevel(WARNING)
    ## ストリームハンドラーのレベル設定
    if _level_sh == 'CRITICAL':
        sh.setLevel(CRITICAL)
    elif _level_sh == 'ERROR':
        sh.setLevel(ERROR)
    elif _level_sh == 'WARNING' or _level_sh == 'WARN':
        sh.setLevel(WARNING)
    elif _level_sh == 'DEBUG':
        sh.setLevel(DEBUG)
    else:
        sh.setLevel(INFO)
    #ロガーにハンドラを登録
    logger.addHandler(fh)
    logger.addHandler(sh)
    #フォーマッタの生成
    fh_fmt = Formatter('%(asctime)s.%(msecs)-3d [%(levelname)s] [%(funcName)s] [Line:%(lineno)d] %(message)s', datefmt="%Y-%m-%dT%H:%M:%S")
    sh_fmt = Formatter('%(message)s')
    #ハンドラにフォーマッタを登録
    fh.setFormatter(fh_fmt)
    sh.setFormatter(sh_fmt)
    return logger

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

# selenium(chrome)のレスポンスをHTMLファイルを保存する
def save_result_html(response, filename):
    print(f'save html file: {filename}')
    with open(filename, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(response)

# 設定ファイルや祝日ファイルなど必要なファイルが/tmp以下に存在することを確認する
def is_exist_files(s3bucket, *args):
    """
    設定ファイルと祝日ファイルが存在することを確認する
    """
    # ローカルのファイル保存先を指定する
    for file_s3path in args:
        # ファイル名のみ抽出する
        file_name = os.path.basename(file_s3path)
        file_path = '/tmp/' + file_name
        # ファイルの存在を確認する
        if os.path.isfile(file_path):
            print(f'found {file_path}')
        else:
            #print(f'downloading {file_name} from s3.')
            get_file_from_s3(s3bucket, file_s3path)

# 設定ファイルと祝日ファイルなど必要なファイルをS3バケットから取得し、/tmpディレクトリに保存する
def get_file_from_s3(s3bucket, file_s3path):
    """
    設定ファイルと祝日ファイルを所定のS3バケットから取得し、/tmpディレクトリに保存する
    """
    # バケット名とファイルパスを設定する
    bucket_name = s3bucket
    key = file_s3path
    file_name = os.path.basename(file_s3path)
    # ローカルのファイル保存先を指定する
    file_path = '/tmp/' + file_name
    # S3からファイルをダウンロードする
    try:
        bucket = s3.Bucket(bucket_name)
        bucket.download_file(key, file_path)
        print(subprocess.run(["ls", "-l", "/tmp" ], stdout=subprocess.PIPE))
        print(f'downloaded {file_name} from s3bucket:{file_s3path}')
        return
    except Exception as e:
        print(e)

# 年越し処理
def check_new_year(month):
    """
    年月日が年越ししているか確認する
    入力された月を見て、これが現在の月よりも小さい場合、年越し処理として
    新しい年を戻り値として返す
    """
    # タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    _now = datetime.datetime.now(JST)
    _this_year = _now.year
    _this_month = _now.month
    _today = _now.day
    if _this_month > month:
        year = _this_year + 1
    else:
        year = _this_year
    #print(f'Year: {year}')
    return year

# 検索対象月のリストを作成する
def create_month_list(cfg, logger=None):
    """
    検索対象月のリストを作成する
    今日の日付を取得し、当月、翌月のリストを作成する

    """
    # タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    # 検索対象期間と起点日を設定する
    month_num = cfg['month_period']
    start_day = cfg['start_day']
    # 初期化する
    target_months = []
    # 現在の時刻を取得し、検索対象月を取得する
    _now = datetime.datetime.now(JST)
    # 予約開始日より前の場合は、検索対象月を1か月減らす
    if _now.day < start_day:
        month_num = month_num - 1
    for _num in range(month_num):
        # 月を取得し、対象月リストに追加する
        target_month = _now + relativedelta(months=+_num)
        #logger.debug(f'target_month: {target_month} / _num: {_num}')
        target_months.append(target_month.month)
    # 検索対象月のタプルを作成する
    #logger.debug(f'target months: {target_months}')
    return target_months

# 今日と翌月1日(YYYYMM)の文字列を取得する
def get_today_and_netx_month_string():
    """
    翌月(YYYYMM)の文字列を取得する
    """
    # 今日の年月日を取得する# タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    # 今日の年月を取得する
    _now = datetime.datetime.now(JST)
    _this_year = str(_now.year)
    _this_month = str(_now.month).zfill(2)
    _this_day = str(_now.day).zfill(2)
    _this_yyyymm = str(_this_year + _this_month)
    _today = str(_this_year + _this_month + _this_day)
    # 今月の1日を取得してから翌月1日を取得する
    _next_firstday = datetime.datetime.today().replace(day=1) + relativedelta(months=+1)
    _next_year = str(_next_firstday.year)
    _next_month = str(_next_firstday.month).zfill(2)
    _next_day = str(_next_firstday.day).zfill(2)
    _next_month_firstday = str(_next_year + _next_month + _next_day)
    #print(f'today:{_today}, next_month_firstday:{_next_month_firstday}')
    return _today, _next_month_firstday

# 検索対象月の希望曜日・祝日・希望日のリストを作成する
def create_day_list(month, public_holiday, cfg):
    """
    検索対象月の土曜日・日曜日の日にちのリストを作成する
    当月の場合は今日以降の日にちのリストとする
    """
    # タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    # 希望曜日リストを作成する
    selected_weekdays = cfg['want_weekdays']
    # 祝日以外の希望日リストを作成する
    want_month_days = cfg['want_month_days'][str(month)]
    # 検索除外日リストを作成する
    exclude_month_days = cfg['exclude_month_days'][str(month)]
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
    if month ==  datetime.datetime.now(JST).month:
        _ref_day = datetime.datetime.now(JST).day
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
    # 重複した年月日日時を取り除き、昇順でソートして日にちのリストを作る
    target_days = sorted(list(set(day_list)))
    # 除外日をリストから削除する
    if exclude_month_days:
        for _exclude_day in exclude_month_days:
            # 除外日リストが存在した場合、削除する
            if _exclude_day in target_days:
                target_days.remove(int(_exclude_day))
    #print(target_days)
    return target_days

# 指定月に対して予約する希望日リストを作成する
def create_want_day_list(month, public_holiday, cfg):
    """
    希望遅延日を計算の上、希望検索対象月の土曜日・日曜日の日にちのリストを作成する
    当月の場合は今日以降の日にちのリストとする
    """
    # タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    # 希望曜日リストを作成する
    selected_weekdays = cfg['want_weekdays']
    # 祝日以外の希望日リストを作成する
    want_month_days = cfg['want_month_days'][str(month)]
    # 予約希望除外日リストを作成する
    exclude_want_month_days = cfg['exclude_want_month_days'][str(month)]
    # 希望遅延日を取得する
    days_later = int(cfg['days_later'])
    # 年越し確認をする
    year = check_new_year(month)
    # 対象日を格納するリストを初期化する
    day_list=[]
    # 対象月の初日の曜日と最終日とを取得する
    ( first_weekday , last_day ) = calendar.monthrange( year, month )
    #print(f'{first_weekday}, {last_day}')
    # 今日から希望X日後の日付を取得する
    after_date = datetime.datetime.now(JST) + datetime.timedelta(days=days_later)
    after_month = after_date.month
    after_day = after_date.day
    # 月の処理
    # X日後の月が指定月と同じ場合は、今日からX日後の日付(after_day)を_ref_dayとする
    if month == after_month:
        _ref_day = after_day
    # X日後の月が翌月の場合は、対象月は空の日付リストを返す
    else:
        return day_list
    # 選択された曜日の日にちのリストを作成する
    for _wday in selected_weekdays:
        _day = _wday - first_weekday + 1
        while _day <= last_day:
            if _day >= _ref_day:
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
    # 重複した年月日日時を取り除き、昇順でソートして日にちのリストを作る
    target_days = sorted(list(set(day_list)))
    # 予約希望除外日をリストから削除する
    if exclude_want_month_days:
        for _exclude_day in exclude_want_month_days:
            # 予約希望除外日リストが存在した場合、削除する
            if _exclude_day in target_days:
                target_days.remove(int(_exclude_day))
    #print(target_days)
    return target_days

# 予約希望日リストを作成する
def create_want_date_list(target_months_list, public_holiday, cfg, logger=None):
    """
    予約希望日(実際に予約アクションをする条件)リストを作成する
    """
    want_date_list = []
    for _month in target_months_list:
        # 年越し確認
        _year = check_new_year(_month)
        # 対象月の希望日リストを作成する
        want_days_list = create_want_day_list(_month, public_holiday, cfg)
        for _day in want_days_list:
            # 文字列YYYYMMDDを作成する
            _date = str(_year) + str(_month).zfill(2) + str(_day).zfill(2)
            want_date_list.append(_date)
    #logger.info(f'want_date_list: {want_date_list}')
    return want_date_list

# 予約希望日リストを同時実行数に応じて分割したリストを作成する
def split_date_list_by_threads(cfg, date_list, logger=None):
    """
    予約希望日リストを同時実行数に応じて分割したリストを作成する

    Args:
        target_months_list ([List]): YYYYMMDDの日付のリスト
        cfg ([Dict]): 設定ファイルのDictオブジェクト
        logger ([Object], optional): ロギングオブジェクト. Defaults to None.

    Returns:
        [List]: ListのList型の日付のリスト
    """
    # スレッド数を取得する
    threads_num = int(cfg['threads_num'])
    # 日付リストの初期化。スレッド数に応じたリストのリストを作成する
    split_date_list = []
    for i in range(threads_num):
        split_date_list.append([])
    index = 0
    for _date in date_list:
        _index = index % threads_num
        split_date_list[_index].append(_date)
        index += 1
    # 分割した日付リストを返す
    logger.debug(f'split_date_list:')
    logger.debug(json.dumps(split_date_list, indent=2))
    #print(json.dumps(request_objs, indent=2))
    return split_date_list

# 年月日(YYYYMMDD)から曜日を取得し、曜日を計算し、年月日と曜日を返す
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

## 空き予約リストを昇順に並べ替える
def sort_reserves_list(reserves_list):
    """
    空き予約リストを昇順に並べ変える
    """
    sorted_reserves_list = {}
    _sort_date = []
    # 日付順に並び変えたリストを作成する
    sorted_date = sorted(reserves_list.keys())
    for _date in sorted_date:
        sorted_reserves_list[_date] = {}
        for _time, _location_list in sorted(reserves_list[_date].items()):
            # 昇順にソートして、重複を取り除く(非同期処理の弊害)
            _sorted_location_list = sorted(list(set(_location_list)))
            sorted_reserves_list[_date][_time] = _sorted_location_list
    # 昇順に並び変えた予約リストを返す
    print(json.dumps(sorted_reserves_list, indent=2, ensure_ascii=False))
    return sorted_reserves_list

## 空き予約リストを、希望日リスト、希望時間帯リスト、希望施設名リストより予約処理対象リスト(年月日:[時間帯]のdict型)を作成する
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
                # 希望日+希望時間帯のリストに空き予約日がない場合は初期化語、時間帯を追加する
                if _date not in target_reserves_list:
                    target_reserves_list[_date] = []
                    target_reserves_list[_date].append(_time)
                    logger.debug(f'regist target reserves list: {_date} {_time} {_court}')
                # ある場合は時間帯を追加する
                else:
                    # 同じ時間帯がない場合は時間帯は追加する
                    if _time not in target_reserves_list[_date]:
                        target_reserves_list[_date].append(_time)
                        logger.info(f'regist target reserves list: {_date} {_time} {_court}')
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

# 予約リストのdictから指定日の時間帯の最小値と最大値を取得する
def get_min_and_max_time(reserves_list, date, split_string, logger=None):
    """
    予約リストのdictから指定日の時間帯の最小値と最大値を取得する
    """
    # 文字列を分割する文字を取得する
    _split_string = str(split_string)
    # 時間帯の最小値と最大値を初期化する
    min_time = datetime.time(23, 59, 59) 
    max_time = datetime.time(0, 0, 0)
    # 予約リストのdictに指定日が存在しない場合は、Noneを返す
    if date not in reserves_list:
        #logger.debug(f'not found {date} in reserves_list')
        #return datetime.time(0, 0, 0), datetime.time(23, 59, 59)
        return None, None
    else:
        for _time in reserves_list[date]:
            # 時間帯を開始時間と終了時間に分割する
            ( start_time, end_time ) = get_start_and_end_time(_time, _split_string, logger=logger)
            # 時間帯の最小値よりも開始時間が小さい場合は、時間帯の最小値を置換する
            if start_time < min_time:
                min_time = start_time
            # 時間帯の最大値よりも終了時間が大きい場合は、時間帯の最大値を置換する
            if end_time > max_time:
                max_time = end_time
            #logger.debug(f'min_time: {min_time} , max_time: {max_time}')
    # 時間帯の最小値と最大値を返す
    logger.debug(f'date( {date} ) final: min_time: {min_time} , max_time: {max_time}')
    return min_time, max_time

# 時間帯の文字列から開始時間と終了時間を取得する
def get_start_and_end_time(time, split_string, logger=None):
    """
    時間帯の文字列から開始時間と終了時間を取得する
    """
    # 文字列を分割する文字を取得する
    _split_string = str(split_string)
    # 時間帯を開始時間と終了時間に分割する
    start_time_string = time.split(f'{_split_string}')[0]
    start_time_hour = int(start_time_string.split(':')[0])
    start_time_min = int(start_time_string.split(':')[1])
    end_time_string = time.split(f'{_split_string}')[1]
    end_time_hour = int(end_time_string.split(':')[0])
    end_time_min = int(end_time_string.split(':')[1])
    start_time = datetime.time(start_time_hour, start_time_min, 0)
    end_time = datetime.time(end_time_hour, end_time_min, 0)
    logger.debug(f'start_time: {start_time}, end_time: {end_time}')
    return start_time, end_time

# 現在の時間帯(min_time, max_time)を開始時間(start_time)と終了時間(end_time)で条件を満たしていたら更新する
def update_min_and_max_time(min_time, max_time, start_time, end_time, logger=None):
    """[summary]
    現在の時間帯(min_time, max_time)を開始時間(start_time)と終了時間(end_time)で条件を満たしていたら更新する
    開始時間がmin_timeより小さい場合は開始時間をmin_timeとする
    終了時間がmax_timeより大きい場合は終了時間をmax_timeとする
    Args:
        min_time ([Time]): 時間帯の最小時間
        max_time ([Time]): 時間帯の最大時間
        start_time ([Time]): 開始時間
        end_time ([Time]): 終了時間
        いずれも、datetimeモジュールのdatetime.timeオブジェクト

    Returns:
        min_time [Time]: 更新された時間帯の最小時間
        max_time [Time]: 更新された時間帯の最大時間
    """
    # 時間帯の最小時間と開始時間を比較する。最小時間がNoneまたは開始時間が小さければ、最小時間を置き換える。
    if min_time == None or start_time < min_time:
        min_time = start_time
    # 時間帯の最大時間と終了時間を比較する。最大時間がNoneまたは終了時間が大きれければ、最大時間を置き換える
    if max_time == None or end_time > max_time:
        max_time = end_time
    # 時間帯の最小時間と最大時間を返す
    logger.debug(f'updated min_time: {min_time}, max_time: {max_time}')
    return min_time, max_time

# ユーザー毎の希望予約リストを作成する
# ユーザー毎既存予約済みリストと希望予約リストを比較し、既存予約済みリストと日時と時間帯の予約が重なっている場合はユーザー毎の希望予約リストに追加しない
def create_user_target_reserves_list(target_reserves_list, user_reserved_list, logger=None):
    """
    ユーザー毎の希望予約リストを作成する
    ユーザー毎既存予約済みリストと希望予約リストを比較し、既存予約済みリストと日付と時間帯の予約が重なっている場合はユーザー毎の希望予約リストに追加しない
    """
    # ユーザー毎希望予約リストを初期化する
    user_target_reserves_list = {}
    # ユーザー毎既存予約済みリスト
    # 空き予約検索で見つけた希望予約リストを走査する
    # 日付のキーを取得する
    for _date, _time_dict in target_reserves_list.items():
        # ユーザー毎既存予約済みリストの時間帯の最小値と最大値を取得する
        ( min_time, max_time ) = get_min_and_max_time(user_reserved_list, _date, '～', logger=logger)
        # 取得した日付がユーザー毎既存予約済みリストに存在するか確認する
        if _date in user_reserved_list:
            # 時間帯のキーを取得する
            for _time, _court_list in _time_dict.items():
                # 時間帯の文字列から開始時間と終了時間を取得する
                ( start_time, end_time ) = get_start_and_end_time(_time, '～', logger=logger)
                # 取得した時間帯がユーザー毎既存予約済みリストに存在するか確認する。存在したら次の時間帯の処理に進む
                if _time in user_reserved_list[_date]:
                    logger.debug(f'found reserve( {_date} {_time} ) in user_reserved_list')
                    continue
                else:
                    # ユーザー毎希望予約リストにないか確認する。なければ、その予約をユーザー毎希望予約リストに追加する
                    if _date not in user_target_reserves_list:
                        # ユーザー毎既存予約済みリストの時間帯の最小値と最大値の時間に重なっていないことを確認する
                        # 開始時間、終了時間がかともに最小値と最大値の間にないことを確認する
                        if start_time >= max_time or end_time <= min_time :
                            logger.debug(f'regist reserve( {_date} {_time} ) to user_target_reserves_list')
                            user_target_reserves_list[_date] = {}
                            user_target_reserves_list[_date][_time] = _court_list
                            # 次のキーの判定のために、min_timeとmax_timeを更新する
                            ( min_time, max_time ) = update_min_and_max_time(min_time, max_time, start_time, end_time, logger=logger)
                    else:
                        # 時間帯のキーがないか確認する。なければ、その予約をユーザー毎希望予約リストに追加する
                        if _time not in user_target_reserves_list[_date]:
                            # ユーザー毎既存予約済みリストの時間帯の最小値と最大値の時間に重なっていないことを確認する。
                            # 重なっていると予約できないため。
                            # ユーザー毎既存予約済みリストの時間帯の最小値と最大値の時間に重なっていないことを確認する
                            # 開始時間、終了時間がかともに最小値と最大値の間にないことを確認する
                            if start_time >= max_time or end_time <= min_time :
                                logger.debug(f'regist reserve( {_date} {_time} ) to user_target_reserves_list')
                                user_target_reserves_list[_date][_time] = _court_list
                                # 次のキーの判定のために、min_timeとmax_timeを更新する
                                ( min_time, max_time ) = update_min_and_max_time(min_time, max_time, start_time, end_time, logger=logger)
        else:
            # 時間帯のキーを取得する
            for _time, _court_list in _time_dict.items():
                # 時間帯の文字列から開始時間と終了時間を取得する
                ( start_time, end_time ) = get_start_and_end_time(_time, '～', logger=logger)
                # ユーザー毎希望予約リストにないか確認する。なければ、その予約をユーザー毎希望予約リストに追加する
                if _date not in user_target_reserves_list:
                    user_target_reserves_list[_date] = {}
                    user_target_reserves_list[_date][_time] = _court_list
                    # 次のキーの判定のために、min_timeとmax_timeを更新する
                    ( min_time, max_time ) = update_min_and_max_time(min_time, max_time, start_time, end_time, logger=logger)
                else:
                    # 日付のキーが存在したら、時間帯を確認する
                    if _time in user_target_reserves_list[_date]:
                        # ユーザー毎希望予約リストにその時間帯が存在していたら、次の時間帯の検索に移る
                        continue
                    else:
                        # ユーザー毎既存予約済みリストの時間帯の最小値と最大値の時間に重なっていないことを確認する
                        # 開始時間、終了時間がかともに最小値と最大値の間にないことを確認する
                        if start_time >= max_time or end_time <= min_time :
                            logger.debug(f'regist reserve( {_date} {_time} ) to user_target_reserves_list')
                            user_target_reserves_list[_date][_time] = _court_list
                            # 次のキーの判定のために、min_timeとmax_timeを更新する
                            ( min_time, max_time ) = update_min_and_max_time(min_time, max_time, start_time, end_time, logger=logger)
                    # for _utime in user_target_reserves_list[_date]:
                    #     # 時間帯のキーがないか確認する。なければ、その予約をユーザー毎希望予約リストに追加する
                    #     if _utime not in user_target_reserves_list[_date]:
                    #         # ユーザー毎既存予約済みリストの時間帯の最小値と最大値の時間に重なっていないことを確認する。
                    #         # 重なっていると予約できないため。
                    #         # 時間帯の文字列から開始時間と終了時間を取得する
                    #         ( start_time, end_time ) = get_start_and_end_time(_utime, '～', logger=logger)
                    #         # ユーザー毎既存予約済みリストの時間帯の最小値と最大値の時間に重なっていないことを確認する
                    #         # 開始時間、終了時間がかともに最小値と最大値の間にないことを確認する
                    #         if start_time >= max_time or end_time <= min_time :
                    #             logger.debug(f'regist reserve( {_date} {_time} ) to user_target_reserves_list')
                    #             user_target_reserves_list[_date][_time] = _court_list[0]
                    #             # 次のキーの判定のために、min_timeとmax_timeを更新する
                    #             ( min_time, max_time ) = update_min_and_max_time(min_time, max_time, start_time, end_time, logger=logger)
    # ユーザー毎希望予約リストを返す
    logger.debug(f'user_target_reserves_list:')
    logger.debug(json.dumps(user_target_reserves_list, indent=2, ensure_ascii=False))
    return user_target_reserves_list

# 時間帯の文字列を2桁の0で埋める
def time_zfill2(_time, split_string):
    """
    h:m～h:mの時間帯の文字列を時間、分とも2桁に変換する
    """
    # 昇順で表示させるため時間帯がひと桁のものを0で埋める。11文字以下なら処理をする
    if len(str(_time)) < 11:
        #開始時刻と終了時刻に分割する
        _start_time = re.split(split_string, str(_time))[0]
        _end_time = re.split(split_string, str(_time))[1]
        # 5文字以下なら処理をする
        if len(str(_start_time)) < 5:
            _hour = re.split(':', str(_start_time))[0]
            _min = re.split(':', str(_start_time))[1]
            _start_time = str(_hour).zfill(2) + ':' + str(_min).zfill(2)
        if len(str(_end_time)) < 5:
            _hour = re.split(':', str(_end_time))[0]
            _min = re.split(':', str(_end_time))[1]
            _end_time = str(_hour).zfill(2) + ':' + str(_min).zfill(2)
        _time= str(_start_time) + '～' + str(_end_time)
    return _time

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

# 予約上限数と翌月の予約上限数を取得する
def get_reserved_limit(cfg):
    """
    予約上限数を取得する
    開放日(cfg['open_day'])以降は予約上限数をcfg['reserved_limit_after']の値とする
    開放日前は予約上限数をcfg['reserved_limit_after_open_day']の値とする
    """
    # タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    # 今日の日付を取得する
    _now = datetime.datetime.now(JST)
    #_this_year = _now.year
    #_this_month = _now.month
    _today = _now.day
    # 今日の日付から予約上限数を取得する
    if _today < cfg['open_day']:
        reserved_limit = cfg['reserved_limit']
        reserved_limit_for_next_month = cfg['reserved_limit_for_next_month']
    else:
        reserved_limit = cfg['reserved_limit_after_open_day']
        reserved_limit_for_next_month = cfg['reserved_limit_for_next_month_after_open_day']
    return reserved_limit, reserved_limit_for_next_month

# 予約処理をする利用者IDリストを作成する
def get_userauth_dict(cfg):
    """
    利用者IDリストを作成する。ID:PASSWORDのdict型で作成する
    開放日(cfg['open_day'])以降はadmin、inner(市内在住者)、outer(市外居住者)を利用者IDリストとする
    開放日以前はadmin、innerとする
    """
    # 利用者IDリストを初期化する
    userauth = cfg['userauth']
    # タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    # 今日の日付を取得する
    _now = datetime.datetime.now(JST)
    #_this_year = _now.year
    #_this_month = _now.month
    _today = _now.day
    # 今日の日付から予約上限数を取得する
    if _today < cfg['open_day']:
        # 市外居住者のIDを削除する
        del userauth['outers']
    #print(f'userauth: {userauth}')
    return userauth

# 調布市向け
# 監視対象日の年月日リストの2次元配列([[YYYY, MM, DD], [YYYY, MM, DD], ...])を作成する
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

# 監視対象年月のリスト([[YYYY,MM], [YYYY, MM], ...])を作成する
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
def create_date_list_hachioji(target_months_list, public_holiday, cfg, logger=None):
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
    logger.debug(date_list)
    return date_list

## 空き予約リストを、希望日リスト、希望時間帯リスト、希望施設名リストより予約処理対象リスト(年月日:[時間帯]のdict型)を作成する
def create_target_reserves_list_hachioji(reserves_list, want_date_list, want_hour_list, want_location_list, logger=None):
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
            # 空きコートが希望空きコートリストに含まれていない場合は次のコートに進む
            for _court in _court_list:
                # 空きコート名から、施設名とコート名に分割する
                #_location_name = _court.split(' ')[0]
                #_court_name = _court.split(' ')[1]
                # 空き予約コートが希望施設名に含まれていない場合は次の空きコートに進む
                if _court not in want_location_list:
                    logger.debug(f'not want location: {_date} {_time} {_court}')
                    continue
                # 希望日+希望時間帯のリストに空き予約日がない場合は初期化後、時間帯を追加する
                if _date not in target_reserves_list:
                    target_reserves_list[_date] = {}
                    target_reserves_list[_date][_time] = []
                    target_reserves_list[_date][_time].append(_court)
                    logger.debug(f'regist target reserves list: {_date} {_time} {_court}')
                # ある場合は時間帯を追加する
                else:
                    # 同じ時間帯がない場合は時間帯は追加する
                    if _time not in target_reserves_list[_date]:
                        target_reserves_list[_date][_time] = []
                        target_reserves_list[_date][_time].append(_court)
                        logger.info(f'regist target reserves list: {_date} {_time} {_court}')
                    else:
                        # 次の時間帯に進む
                        logger.debug(f'found {_time} in target reserves list. therefore next time.')
                        # breakでコートのループを抜ける
                        break
            else:
                # _d_valueの次のループに進む
                continue
    # 希望日+希望時間帯のリストを返す
    #logger.debug(f'{target_reserves_list}')
    return target_reserves_list

# 東京都町田市向け
# 検索対象日リストを作成する。希望日を追加、除外日を除外した日付リストを作成する
def create_date_list_machida(target_months_list, public_holiday, cfg, logger=None):
    """
    検索対象日リストを作成する
    プログラム実行日から1か月先までの日付リストを作成する。1か月先以降は空き予約できないため、無視する

    Args:
        target_months_list ([List]): 検索対象月の月リスト[description]
        public_holiday ([Dict]): 祝日のDict[description]
        cfg ([Dict]): 設定ファイル
        logger ([Obj], optional): ロギングオブジェクト. Defaults to None.

    Returns:
        [List]: 検索対象日(YYYYMMDD)のリスト
    """
    # 
    # タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    # 除外日リストを取得する
    exclude_days = []
    exclude_month_days_dict = cfg['exclude_month_days']
    # 対象月リストから月を取得し、月毎の除外日リストを追加する
    for _month in target_months_list:
        # 除外日Dictから除外日のリストを取得する
        # 除外日のリストがあるか確認する。空なら次の月に進む
        if exclude_month_days_dict[str(_month)] == False:
            continue
        for _exclude_month_day in exclude_month_days_dict[str(_month)]:
            _str_year = str(check_new_year(_month))
            _str_month = str(_month).zfill(2)
            _str_day = str(_exclude_month_day).zfill(2)
            _str_date = _str_year + _str_month + _str_day
            exclude_days.append(_str_date)
    #logger.debug(f'exlude_days: {exclude_days}')
    # 除外日も含めた検索対象日リストを作成する
    # 多摩市向けの create_date_list を使う
    _date_list_with_exclude = create_date_list(target_months_list, public_holiday, cfg)
    #logger.debug(f'date_list_with_exclude_days: {_date_list_with_exclude}')
    # 今日の日付を計算する
    _now = datetime.datetime.now(JST)
    # 翌月の日付を計算する
    _one_month_after = _now + relativedelta(months=1)
    #logger.debug(f'one_month_after: {_one_month_after}')
    # 検索対象日のリストを作成する
    date_list = []
    for _str_date in _date_list_with_exclude:
        # 文字列からtimeオブジェクトに変換して、タイムゾーン情報を付与する
        _date = datetime.datetime.strptime(_str_date, '%Y%m%d').replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        #logger.debug(f'date: {_date}')
        # 除外日リストに入っていないことを確認する
        if _str_date not in exclude_days:
            # 翌月の日付以前かを確認する
            if _date <= _one_month_after:
                date_list.append(_str_date)
    return date_list

# 空き予約を送信する
## メッセージ本文の作成
def create_message_body(reserves_list, message_bodies, cfg, logger=None):
    """
    LINEに送信するメッセージの本体を作成する
    """
    # Discordのメッセージ本体サイズの最大値
    max_message_size=int(cfg['discord_max_message_size'])
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
            logger.debug(f'reserve empty: {_date} {reserves_list[_date]}')
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
                for _court in sorted(_court_list):
                    _body = f'{_body}　{_court}\n'
                    #print(_court)
    # メッセージ本体の文字数を1000文字以内にする
    message_bodies.append(_body[:max_message_size])
    # メッセージ本体の文字数が1000より大きい場合は予約日時だけのメッセージ本体を作成する
    if len(_body) >= max_message_size:
        _body_date = f'\n空きコートが多いのでWEBでサイトで確かめてください。上記の時間帯に空きコートがあります。\n{_body_date}'
        message_bodies.append(_body_date)
    else:
        logger.debug(f'within {max_message_size} characters.')
    # デバッグ: 送信文本体と日付インデックスを表示する
    #print(_body)
    #print(_body_date)
    for _message in message_bodies:
        logger.debug(_message)
    return message_bodies

## 予約確定通知メッセージの本文を作成する
def create_reserved_message(userid, reserved_number, reserve, message_bodies, cfg, logger=None):
    """
    予約確定通知用のメッセージボディーを作成する
    """
    # メッセージ本文の文頭を作成する
    _body = f'\n予約が確定しました。マイページで確認してください。\n'
    _body = f'{_body}利用者ID: {userid}\n'
    _body = f'{_body}予約番号: {reserved_number}\n'
    # 予約リストを与えて、取得した予約情報を追記する
    message_bodies = create_message_body(reserve, message_bodies, cfg, logger=logger)
    # message_bodiesリストの最初の要素が予約情報なので、これを文頭と結合する
    _reserve_info = message_bodies[0]
    _body = f'{_body}{_reserve_info}'
    # message_bodiesリストの最初の要素を書き換える
    message_bodies[0] = f'{_body}'
    return message_bodies

# LINEにメッセージを送信する
# LINE Noftifyサービスの停止に伴い、2025/4以降は本関数は使わない
def send_line_notify(message_bodies, token, logger=None):
    """
    LINE Notifyを使ってメッセージを送信する
    """
    #print(f'sending to LINE.')
    #print(message_bodies)
    #print(len(message_bodies[0]))
    # line_notify_token = cfg['line_token']
    line_notify_token = token
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    # メッセージの長さが1(\n分)の場合はコンソールに空き予約がないメッセージを表示する
    if len(message_bodies[0]) > 1:
        for _message in message_bodies:
            data = {'message': f'{_message}'}
            requests.post(line_notify_api, headers = headers, data = data)
            sleep(1)
        logger.info(f'sent empty reserves.')
    else:
        # 空き予約がない場合はログ出力のみする
        #data = {'message': f'空き予約はありませんでした'}
        #requests.post(line_notify_api, headers = headers, data = data)
        logger.debug(f'not found empty reserves.')

# Discordのチャンネルに空き予約を送信する
def send_discord_channel(message_bodies, token, channel_id, logger=None):
    """
    Discordのチャンネルにメッセージを送信する
    """
    # メッセージボディーサイズが1以下の場合は、送信を止める
    if len(message_bodies[0]) <= 1:
        logger.debug(f'message size is less than 1, therefore stop to send to discord.')
        return None
    
    # BotのトークンとチャンネルIDを設定する
    _token = token
    _channel_id = channel_id
    
    # Intentsを設定
    intents = discord.Intents.default()
    intents.message_content = True  # メッセージの内容にアクセスするためのIntent
    
    # クライアントを作成
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        logger.debug(f'We have logged in as {client.user}')
        channel = client.get_channel(_channel_id)
        if channel is not None:
            if len(message_bodies[0]) > 1:
                for _message in message_bodies:
                    await channel.send(f'{_message}')
                    await asyncio.sleep(1)
                logger.info(f'sent empty reserves.')
                await client.close()  # メッセージを送信後にクライアントを閉じる
            else:
                # 空き予約がない場合はログ出力のみする
                logger.debug(f'not found empty reserves.')
                await client.close()  # メッセージを送信後にクライアントを閉じる
        else:
            logger.debug(f'Channel with ID {_channel_id} not found.')
    client.run(_token)

# 実行時間を計測する
def elapsed_time(f):
    """
    関数の処理時間を計測する
    """
    #print(f"call elapsed_time.")
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        #print(f"start: {start}")
        v = f(*args, **kwargs)
        print(f"{f.__name__}: {time.time() - start} sec")
        return v
    return wrapper

# メインルーチン
def main():
    """
    メインルーチン
    """
    
if __name__ == '__main__':
    main()
