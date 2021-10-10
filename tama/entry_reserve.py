# モジュールの読み込み
## HTMLクローラー関連
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

#import asyncio
#import aiohttp
#import async_timeout
#from aiohttp import ClientError

# URLの'/'が問題になるためハッシュ化する
from hashlib import md5
from pathlib import Path

# ツールライブラリを読み込む
import reserve_tools

http_req_num = 0

# 事前準備作業
def prepare_proc_for_reserve(cfg, headers):
    """
    事前準備作業をする
    """
    #ヘッダー情報
    #headers = {
    #    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
    #}
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

## Selenium関連
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

# トップページに接続する
def get_cookie_request(cfg, headers):
    """
    トップページに接続し、初期cookieを取得する
    """
    global http_req_num
    # セッションを開始する
    session = requests.session()
    response = session.get(cfg['first_url'], headers=headers)
    print(session.cookies)
    #exit()
    http_req_num += 1
    # cookie情報を初期化し、次回以降のリクエストでrequestsモジュールの渡せる形に整形する
    cookies = {}
    cookies[cfg['cookie_sessionid']] = session.cookies.get(cfg['cookie_sessionid'])
    cookies[cfg['cookie_starturl']] = session.cookies.get(cfg['cookie_starturl'])
    print(json.dumps(cookies, indent=2))
    #print(response.text)
    #exit()
    return cookies

# ログインIDとパスワードを入力し、ログインし、ログイン後のcookieを取得する
def do_login_and_get_cookie(cfg, headers, cookies):
    """
    ログインし、ログイン後のcookieを取得する
    このcookieを以後、利用していく
    """
    global http_req_num
    # ヘッダー情報を作成する
    headers['Referer'] =  cfg['second_url']
    print(f'headers: {headers}')
    print(f'cookies: {cookies}')
    # ログインボタンをクリックする
    response = requests.get(cfg['login_url'], headers=headers, cookies=cookies)
    http_req_num += 1
    # レスポンスURLを取得する
    print(f'response url: {response.url}')
    hash_url = response.url
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'login.html'
    #print(_file_name)
    _file = reserve_tools.save_html_to_filename(response, _file_name)
    # ログイン画面のフォームデータを取得する
    _form_data = get_common_formdata(response)
    # フォームデータを加工する
    ## 不要なフォームデータを削除する
    del _form_data['LoginInputUC$LoginImgButton']
    del _form_data['LoginInputUC$ReturnImgButton']
    del _form_data['id_nflag']
    ## ユーザーＩＤとパスワードをセットする
    _form_data['LoginInputUC$UserIdTextBox'] = cfg['userid']
    _form_data['LoginInputUC$PasswordTextBox'] = cfg['password']
    ## LoginInputUC$LoginImgButton.x, LoginInputUC$LoginImgButton.y に値を設定する
    _form_data['LoginInputUC$LoginImgButton.x'] = '30'
    _form_data['LoginInputUC$LoginImgButton.y'] = '26'
    ## id_nflag を 1 にする
    _form_data['id_nflag'] = '1'
    print(json.dumps(_form_data, indent=2, ensure_ascii=False))
    # ログインする
    ## ヘッダー情報を設定する
    headers['Referer'] = hash_url
    response = requests.post(hash_url, headers=headers, cookies=cookies)
    # デバッグ用としてhtmlファイルとして保存する
    _file_name = f'done_login.html'
    #print(_file_name)
    _file = reserve_tools.save_html_to_filename(response, _file_name)
    ## 認証後のcookieを取得する
    print(f'cookies: {response.cookies}')
    return None

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


# メイン
def main():
    """
    メインルーチン
    """
    # 変数の初期化
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
    # コートマップファイルを読み込む
    court_map = reserve_tools.read_json_cfg('court_map.json')
    # 検索対象月を取得する
    target_months_list = reserve_tools.create_month_list(cfg)
    #ヘッダー情報
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
    }
    # (TBD)予約処理の判定
    ## 予約希望日リスト、希望時間帯、希望コートと空きコートリストの比較と処理の継続確認
    ## 予約対象希望日+コートのリスト
    # 事前準備作業
    ## 予約希望日を作成する
    ## トップページに接続
    ## ログインする
    ## クッキーを取得する
    ## 既存予約リストと件数を取得する
    ( cookies, reserved_list, reserved_num ) = prepare_proc_for_reserve(cfg, headers)
    ## 予約処理の継続確認
    if reserved_num >= cfg['reserved_limit']:
        return None
    # 空き予約をする
    ## -- forループ start
    ## 空き予約日+空きコート番号を指定して、コート別空き予約時間帯ページを表示する
    ## 予約カゴに入れる
    ## 予約を確定する
    #( reserved_number, reserve ) = do_reserve(cfg, court_map, cookies, date, time, court)
    ( reserved_number, reserve ) = do_reserve(cfg, court_map, cookies, 20210928, '06:00～08:00', '多摩東公園庭球場Ｃ（人工芝）')
    ## -- forループ: まとめて複数予約すると、1件が予約できないとその判定処理が必要で複雑になる
    ## LINEで通知する
    message_bodies = create_reserved_message(reserved_number, reserve, message_bodies, cfg)
    # LINEに送信する
    reserve_tools.send_line_notify(message_bodies, cfg)
    ## -- forループ end
    # 事後処理
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
