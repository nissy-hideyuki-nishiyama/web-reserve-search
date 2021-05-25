# モジュールの読み込み
## HTMLクローラー関連
from requests.exceptions import Timeout
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
from hashlib import md5
from pathlib import Path


## HTML解析関連
from bs4 import BeautifulSoup
import re

## JSON関連
import json

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

## 年月日を指定して空き予約を検索する
def go_select_searching(cfg, form_data, cookies):
    """
    検索方法選択ページに移動する
    """
    # フォームデータをURLエンコードする
    # フォームデータに検索方法選択ページのデータを追加する
    top_form_data = form_data
    top_form_data['ykr00001c$YoyakuImgButton.x'] = 145
    top_form_data['ykr00001c$YoyakuImgButton.y'] = 70
    #print(cookies)
    #params = urllib.parse.urlencode(top_form_data)
    #print(params)
    #headers = {
    #    'Content-Type': 'application/x-www-form-urlencoded'
    #}
    #print(headers)
    # 検索方法ページに移動する
    #res = requests.post(cfg['second_url'], headers=headers, cookies=cookies, data=params)
    #res_form_data = get_formdata(res)

# コートの空き予約を検索する
@reserve_tools.elapsed_time
def get_empty_reserves(cfg, date_list, reserves_list, cookies, http_req_num):
    """
    指定年月日のリストを引数として、その指定年月日の空き予約を検索する
    """
    # リファレンスヘッダーを定義する。これがないと検索できない
    headers_day = { 'Referer': cfg['day_search_url'] }
    headers_court = { 'Referer': cfg['court_search_url'] }
    # 検索URL用のパラメータ部分のURLを定義する
    param_day_string = '?PSPARAM=Dt::0:1:205::::_TODAYSTRING_:1,2,3,4,5,6,7,10:_DATESTRING_:False:_SEARCHPARAM_:0:0&PYSC=0:1:205::::_TODAYSTRING_:1,2,3,4,5,6,7,10&PYP=:::0:0:0:0:True::False::0:0:0:0::0:0'
    # 今日の年月日を取得する
    ## タイムゾーンを設定する
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    _now = datetime.datetime.now(JST)
    _today = str(_now.year) + str(_now.month).zfill(2) + str(_now.day).zfill(2)
    #print(f'today: {_today}')
    # 指定年月日のリストから検索するためのURLを生成する
    for _day in date_list:
        # 奈良原公園とそれ以外で検索する
        for param_string in cfg['search_params']:
            # パラメータ文字列の日付部分を置換する
            _param = re.sub('_SEARCHPARAM_', param_string, param_day_string)
            _param = re.sub('_TODAYSTRING_', _today, _param)
            _param = re.sub('_DATESTRING_', _day, _param)
            # URLを生成する
            search_url =  cfg['day_search_url'] + _param
            #print(search_url)
            _entity = f'{_day}_{param_string}'
            # 指定年月日を指定した検索リクエストを送信する
            #res = requests.get(search_url, headers=headers_day, cookies=cookies)
            res = get_request_retry(_entity, search_url, headers_day, cookies)
            #print(f'Response: {res}')
            #print(res.hiistory)
            #print(res.text)
            http_req_num += 1
            # 空きコートのリンクを取得する
            court_link_list = get_court(res[1], cfg)
            # 空きコートリンクを使って、空き時間帯とコート名を取得する
            # 空きコートリンクが空の場合は次の指定年月日に移動する
            if len(court_link_list) == 0:
                #print(f'{_day} is empty')
                continue
            # dictに空き予約日の要素を追加する
            if f'{_day}' not in reserves_list:
                reserves_list[f'{_day}'] = {}
            #print(reserves_list[f'{date_string}'])
            for link in court_link_list:
                # 行頭の ./ykr31103,aspx を削除する
                search_url = cfg['court_search_url'] + re.sub('^\.\/ykr31103\.aspx', '', link)
                #print(search_url)
                # ファイル名として保存するエンティティ名を生成する
                name = md5(search_url.encode('utf-8')).hexdigest()
                _entity_string = f'{_day}_{name}'
                # 指定年月日の空きコートリンクのGETリクエストを送信する
                #res_court = requests.get(search_url, headers=headers_court, cookies=cookies)
                res_court = get_request_retry(_entity_string, search_url, headers_court, cookies)
                #print(f'Resp: {res_court}')
                #print(res_court.history)
                http_req_num += 1
                # 指定年月日の時間帯別空きコートのリストを作成する
                reserves_list = get_empty_time(res_court[1], cfg, _day, reserves_list)
    #retrun court_link_list
    print(json.dumps(reserves_list, indent=2, ensure_ascii=False))
    return reserves_list, http_req_num


# HTTPリクエストをする
@reserve_tools.elapsed_time
def get_request_retry(*args, **kwargs):
    """
    並行処理のために外に出して、ステータスコード200以外なら再試行する
    """
    _entity = args[0]
    search_url = args[1]
    headers = args[2]
    cookies = args[3]
    try:
        res = requests.get(search_url, headers=headers, cookies=cookies, timeout=(6.0, 15.0))
        # ステータスコード200以外は再試行を3回する
        max_retry = 3
        _retry = 0
        # デバッグ用(HTTPリクエストのカウント)
        while _retry < max_retry:
            if res.status_code != 200:
                sleep(1)
                res = requests.post(search_url, headers=headers, cookies=cookies, timeout=(6.0, 15.0))
                _retry += 1
                print(f'get request faild count: {_retry}')
            else:
                #print(f'success get request: {_entity}')
                break
        else:
            print(f'faild get request: {_entity}')
            res = None
    except Timeout:
        print(f'get request timeout: {_entity}')
        res = None
    else:
        #print(f'{res.headers}')
        #print(dir(res))
        # デバッグ用としてhtmlファイルとして保存する
        #_file_name = f'result_{_entity}.html'
        #print(_file_name)
        #_file = reserve_tools.save_html_to_filename(res, _file_name)
        return _entity, res


# 指定した年月日の空き予約結果ページから空き予約のコートを取得する
def get_court(response, cfg):
    """
    年月日指定の空き予約検索結果ページから空きコートのリンクを取得する
    """
    # 空き予約リストを初期化する
    court_link_list = []
    # 登録済みリンクを初期化する
    registerd_link = ''
    #reserve_lists = eserver
    # 空きコート名のリンクを取得する
    ## レスポンスオブジェクトをHTML化する
    html = response.text
    soup = BeautifulSoup(html, features='html.parser')
    # aタグのhref属性を持つタグを抽出する
    for atag in soup.find_all('a'):
        # 空きの文字列をもつaタグのみ抽出する
        if atag.string == '空き':
            # 空きコートリンクのリストに追加する
            # 同じコードで空き予約が間欠的に発生した場合、同じリンクが複数表示されるため、二重登録を防ぐ
            # 前と同じリンクか確認し、異なる場合のみ追加する
            #print(dir(atag))
            #print(atag['href'])
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
                            #print(atag['href'])
                            court_link_list.append(atag['href'])
                            # 登録済みリンクとして代入する
                            registerd_link = atag['href']
    # 検索リストを表示する
    #print(court_link_list)
    # 終わる
    return court_link_list

# 指定した年月日のコート空き予約ページから空き予約の時間帯を取得する
def get_empty_time(response, cfg, day, reserves_list):
    """
    空き予約の時間帯を取得する
    """
    #print(reserves_list['day'])
    #print(f'get_empty_time: {day}')
    # レスポンスオブジェクトをHTML化する
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
                    reserves_list[f'{day}'].setdefault(reserve, []).append(court_name)
    #print(reserves_list)
    return reserves_list
    #return None


## メッセージを送信する

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
    # 送信メッセージリストの初期化
    message_bodies = []
    # 処理の開始
    # 空き予約リストの初期化
    reserves_list = {}
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
    ( reserves_list, http_req_num ) = get_empty_reserves(cfg, date_list, reserves_list, cookies, http_req_num=0)

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