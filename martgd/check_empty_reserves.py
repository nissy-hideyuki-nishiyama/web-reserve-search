# モジュールの読み込み
## HTMLクローラー関連
import requests
from time import sleep

## HTML解析関連
from bs4 import BeautifulSoup
import urllib
## 正規表現
import re

## ファイルIO、システム関連
import sys

## カレンダー関連
import math
import datetime
import calendar
import time

## JSONファイルの取り扱い
import json

## 文字コード処理関連。波ダッシュと全角チルダへの対応のため。
import unicodedata

## ツールライブラリを読み込む
from reserve_tools import reserve_tools

# HTTPリクエスト数
http_req_num = 0

def convert_WAVEDASH_to_FULLWIDTHTILDE(string, reverse=False):
    """
    波ダッシュを全角チルダに変換する。reverseにTrue渡せば逆になる
    """
    wavedash = (b'\xe3\x80\x9c').decode('utf-8')
    fullwidthtilde = (b'\xef\xbd\x9e').decode('utf-8')
    if not reverse:
        return string.replace(wavedash, fullwidthtilde)
    else:
        return string.replace(fullwidthtilde, wavedash)


def create_inputdate(target_months_lists, logger=None):
    """
    検索対象年月日の開始日と終了日を作成する
    """
    # 開始日を計算する。明日の日付を開始日とする
    _tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    start_year = _tomorrow.year
    start_month = _tomorrow.month
    start_day = _tomorrow.day
    # 終了時を計算する
    end_month = target_months_lists[-1]
    end_year = reserve_tools.check_new_year( end_month )
    # その月の最終日を計算する
    ( _first_day, _last_day ) = calendar.monthrange( end_year, end_month )
    end_day = _last_day
    # 入力データの開始と終了の年月日のデータを作成する
    input_data_date = [ start_year, start_month, start_day, end_year, end_month, end_day ]
    logger.debug(f'input_data_date: {input_data_date}')
    return input_data_date
    

#def create_inputdata(want_court_list, reserve_status, input_data_date):
def create_inputdata(cfg, input_data_date, logger=None):
    """
    検索条件の入力データを作成する
    入力データの開始と終了の年月日のデータにコート番号と予約受付状態の値を追加する
    """
    # 検索対象の予約状態と検索対象コートを設定する
    #reserve_status = cfg['reserve_status']
    reserve_status = cfg['want_reserve_status']
    want_court_list = cfg['want_court_list']
    # 入力データの初期化
    input_data = {}
    # 入力データの開始と終了の年月日のリストに連結する
    for key, value in want_court_list.items():
        #print(f'{key}')
        input_data[key] = input_data_date + [ value, reserve_status ]
        #print(input_data[key])
    logger.debug(f'{input_data}')
    return input_data


# クローラー
## cookieを取得するため、トップページにアクセスする
@reserve_tools.elapsed_time
def get_cookie(cfg):
    """
    cookieを取得する
    """
    global http_req_num
    # セッションを開始する
    session = requests.session()
    http_req_num += 1
    response = session.get(cfg['first_url'])
    #response.raise_for_status()
    cookie_sessionid = session.cookies.get(cfg['cookie_sessionid'])
    #cookie_starturl = session.cookies.get(cfg['cookie_starturl'])
    cookies = { cfg['cookie_sessionid']: cookie_sessionid }
    return cookies , response


## フォームデータを作成する
def create_formdata(input_data, response):
    """
    入力データを貰ってフォームデータを作成する
    """
    # フォームデータの初期化
    form_data = {}
    # フォームデータを作成する
    form_data['src_year1'] = input_data[0]
    form_data['src_month1'] = input_data[1]
    form_data['src_day1'] = input_data[2]
    form_data['src_year2'] = input_data[3]
    form_data['src_month2'] = input_data[4]
    form_data['src_day2'] = input_data[5]
    form_data['src_court_id'] = input_data[6]
    form_data['srcLotStatus[]'] = input_data[7]
    form_data['id'] = 1
    form_data['mode'] = 'search'
    form_data['__ncforminfo'] = get_ncforminfo(response)
    # フォームデータを返す
    return form_data

## フォームデータを取得する
def get_ncforminfo(response):
    """
    ページからフォームデータを取得する
    """
    # フォームデータ(dict型)を初期化する
    form_data = {}
    # デバッグ用としてhtmlファイルとして保存する
    #_file_name = reserve_tools.save_text_html_to_filename(response.text, 'tmp01.html')
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    _form = soup.find('form')
    _tag_ncforminfo = _form.find_all('input')[-1]
    _ncforminfo = _tag_ncforminfo['value']
    return _ncforminfo

# POSTリクエストを実行する
@reserve_tools.elapsed_time
def do_post_request(cookies, form_data, pre_url, url):
    """
    cookie、フォームデータ、直前のリクエストURL、対象URLを貰って、POSTリクエストを実行する
    """
    global http_req_num
    # 直前のリクエストURLからRefererを含んだヘッダーを生成する
    headers = {
        'Origin': 'https://reserve.lan.jp',
        'Referer': 'pre_url',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib.parse.urlencode(form_data)
    # POSTリクエストする
    res = requests.post(url, headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # shift_jisのHTMLを正しく理解できるように文字コードを指定する
    #res.encoding = 'cp932'
    # レスポンスオブジェクトを返す
    return res

# 空き予約をコート別に検索する
def do_search_empty_reserve(cfg, cookies, response, input_data, court_empty_reserves_list, logger=None):
    """
    入力データを取得して、コート別に空き予約を検索する
    """
    # 検索URL
    url = cfg['search_url']
    # コート別に空き予約を検索する
    for _court, _in_data in input_data.items():
        # 検索条件のためのフォームデータを作成する
        form_data = create_formdata(_in_data, response)
        # フォームデータの値を使って、POSTリクエストを発行し、そのコートに対する空き予約を取得する
        _html = do_post_request(cookies, form_data, url, url)
        # 取得した空き予約結果のWEBページを解析して、空き予約リストに追加する
        court_empty_reserves_list[_court] = analize_html(_court, _html, logger=logger)
    return court_empty_reserves_list


# HTMLファイルを解析する    
def analize_html(court, html, logger=None):
    """
    取得した空き予約情報から土日祝の空き予約情報をフィルタする
    """
    #with open(file_name, mode='r', encoding='utf-8', errors='ignore') as shtml:
    # 空き予約名リストの初期化
    empty_reserves_list = {}
    #soup =BeautifulSoup(shtml.read(), "html.parser")
    soup =BeautifulSoup(html.text, "html.parser")
    # formタグ毎に要素を抽出する
    elems = soup.find_all("form", action="https://reserve.lan.jp/mtg/sp")
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
                empty_reserves_list.setdefault(_date, []).append(_str)
    logger.debug(f'empty_reserves_list: {empty_reserves_list}')
    return empty_reserves_list


# コートの空き予約リストと希望日リストを比較して、予約リストを作成する
def create_selected_reserve_list(court_empty_reserves_list, reserves_list, cfg, input_data_date, logger=None):
    """
    希望時間帯および希望日のみ抽出したリストを作成する
    """
    # 希望時間帯を設定する
    want_time_list = cfg['want_time_list']
    # 希望日のみ抽出した予約名リストを作成する
    # コート別に空き予約名リストを取得する
    for _court, _date_reserves in court_empty_reserves_list.items():
        logger.debug(f'court_name: {_court}')
        # 年月日検索用文字列を土日祝日リストから複製する
        #_selected_reserve_name_list = {}
        _date_string_list = input_data_date
        # 年月日別に空き予約名リストを取得する
        for _day, _reserves in _date_reserves.items():
            logger.debug(f'found day: {_day}')
            # 希望時間帯検索用文字列を希望時間帯リストから複製する
            _want_time_list = want_time_list
            # 希望日リストの日にちと一致したら
            for _want_day in _date_string_list:
                if _day == _want_day:
                    #logger.debug(f'day: {_day}')
                    #_date_string_list.pop(0)
                    # 希望日の予約名リストから希望時間帯のみ抽出する
                    for _want_time in _want_time_list:
                        for _reserve in _reserves:
                            #logger.debug(f'want_time: {_want_time}')
                            #logger.debug(f'reserve_string: {_reserve}')
                            # 2020/12/03に突如発生した。マートガーデン側のデータ更新が怪しい
                            # 波ダッシュが文字列に含まれていたら、全角チルドに変換する
                            if b'\xe3\x80\x9c' in _reserve.encode('utf-8'):
                                _reserve = convert_WAVEDASH_to_FULLWIDTHTILDE(_reserve)
                                #logger.debug(_reserve.encode('utf-8'))
                            if str(_want_time) == str(_reserve):
                                logger.debug(f'{_court}:{_day}:{_reserve}')
                                # 希望時間帯と一致した予約を空き予約リストに登録する
                                # 空き予約リストに発見した日がない場合はその日をキーとして登録する
                                if f'{_day}' not in reserves_list:
                                    reserves_list[f'{_day}'] = {}
                                    reserves_list[f'{_day}'].setdefault(str(_reserve), []).append(f'{_court}コート')
                                # 空き予約リストに発見した日が存在する場合
                                else:
                                    # 空き予約リストに発見した時間帯が存在しない場合はその時間帯をキーとして初期化する
                                    if str(_reserve) not in reserves_list[f'{_day}']:
                                        reserves_list[f'{_day}'][str(_reserve)] = []
                                    reserves_list[f'{_day}'][str(_reserve)].append(f'{_court}コート')
                            # 一致しない場合は次の処理のループに移動する
                            else:
                                continue
                # 一致しない場合は平日なので、次の処理のループに移動する
                else:
                    continue
    #logger.debug(f'{reserves_list}')
    return reserves_list


# メインルーチン    
def main():
    """
    メインルーチン
    """
    # 空き予約名リストの初期化
    court_empty_reserves_list = {}
    #selected_reserve_name_list = {}
    reserves_list = {}
    # 送信メッセージの初期化
    message_bodies = []
    # WEBリクエストのヘッダー
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
            }
    # 処理の開始
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    public_holiday = reserve_tools.set_public_holiday('public_holiday.json')
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = reserve_tools.read_json_cfg('cfg.json')
    # ロギングを設定する
    logger = reserve_tools.mylogger(cfg)
    # 検索対象月のリストを作成する
    target_months_list = reserve_tools.create_month_list(cfg, logger=logger)
    # 検索対象の開始日と終了日のリストを作成する
    input_data_date = create_inputdate(target_months_list, logger=logger)
    # 検索データを作成する
    input_data = create_inputdata(cfg, input_data_date, logger=logger)
    # フィルターリストを作成する
    date_string_list = reserve_tools.create_date_list(target_months_list, public_holiday, cfg)
    logger.debug(f'date_string_list: {date_string_list}')
    # 空き予約ページのトップページにアクセスし、cookieを取得する
    ( cookies, response ) = get_cookie(cfg)
    # 検索データを入力して、空き予約を検索する
    court_empty_reserves_list = do_search_empty_reserve(cfg, cookies, response, input_data, court_empty_reserves_list, logger=logger)
    logger.debug(f'court_empty_reserves_list: {court_empty_reserves_list}')
    # 空き予約名リストから希望曜日の希望時間帯のみを抽出したリストを作成する
    reserves_list = create_selected_reserve_list(court_empty_reserves_list, reserves_list, cfg, date_string_list, logger=logger)
    logger.debug(f'reserves_list: {reserves_list}')
    #exit()
    # 送信メッセージ本体を作成する
    message_bodies = reserve_tools.create_message_body(reserves_list, message_bodies, cfg, logger=logger)
    # LINE Notifyに空き予約情報のメッセージを送信する
    # reserve_tools.send_line_notify(message_bodies, cfg['line_token'], logger=logger)
    # Discordに空き予約情報のメッセージを送信する
    reserve_tools.send_discord_channel(message_bodies, cfg['discord_token'], cfg['discord_channel_id'], logger=logger)
    # 終了する
    #exit()
    return logger
 
if __name__ == '__main__':
    # 実行時間を測定する
    start = time.time()
    logger = main()
    # デバッグ用(HTTPリクエスト回数を表示する)
    logger.debug(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - start
    logger.debug(f'whole() duration time: {elapsed_time} sec')
    exit()
