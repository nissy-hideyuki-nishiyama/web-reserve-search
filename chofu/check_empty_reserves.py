# モジュールの読み込み
## HTMLクローラー関連
import ssl
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

## カレンダー関連
from time import sleep
import time

## ファイルIO、ディレクトリ関連
import os

## HTML解析関連
from bs4 import BeautifulSoup
import re

## JSON関連
import json

# ツールライブラリを読み込む
from reserve_tools import reserve_tools

class TLSAdapter(HTTPAdapter):
    """
    強制的にTLSv1.2以上を使用するカスタムアダプター
    """
    def init_poolmanager(self, connections, maxsize, block=False):
        # クライアント用のSSLコンテキストを作成
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2  # TLSv1.2以上を指定
        context.set_ciphers("DEFAULT:@SECLEVEL=1")  # セキュリティレベルを調整
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=context
        )

# HTTPリクエスト数
http_req_num = 0

# クローラー
## cookieを取得するため、トップページにアクセスする
@reserve_tools.elapsed_time
def get_cookie(cfg):
    """
    cookieを取得する
    """
    global http_req_num
    # セッションを開始する
    session = requests.Session()
    session.mount('https://', TLSAdapter())
    try:
        response = session.get(cfg['first_url'], timeout=10)
        http_req_num += 1
        #response.raise_for_status()
        cookie_sessionid = session.cookies.get(cfg['cookie_sessionid'])
        #cookie_starturl = session.cookies.get(cfg['cookie_starturl'])
        cookies = { cfg['cookie_sessionid']: cookie_sessionid }
        #print(response.content)
        #res_sjis = response.text
        #logger.debug(res_sjis.encode('utf-8'))
    except requests.exceptions.SSLError as e:
        logger.error(f"SSLエラーが発生しました: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"リクエストエラー: {e}")
    return cookies , response

## フォームデータを取得する
def get_formdata(response, logger=None):
    """
    ページからフォームデータを取得する
    """
    logger.debug(f'get form data from response')
    # フォームデータ(dict型)を初期化する
    form_data = {}
    # html解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # form_data部分のみ抽出する
    tags = soup.find_all("input")
    # form_dataを生成する
    for _tag in tags:
        form_data[_tag.get('name')] = _tag.get('value')
    logger.debug(f'form data: {form_data}')
    return form_data

# POSTリクエストを実行する
@reserve_tools.elapsed_time
def do_post_request(cookies, form_data, pre_url, url):
    """
    cookie、フォームデータ、直前のリクエストURL、対象URLを貰って、POSTリクエストを実行する
    """
    global http_req_num
    # 直前のリクエストURLからRefererを含んだヘッダーを生成する
    headers = {
        'Referer': 'pre_url',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    # フォームデータからPOSTリクエストに含めるフォームデータをURLエンコードする
    params = urllib3.parse.urlencode(form_data)
    # POSTリクエストする
    session = requests.Session()
    session.mount('https://', TLSAdapter())
    res = session.post(url, headers=headers, cookies=cookies, data=params)
    http_req_num += 1
    # shift_jisのHTMLを正しく理解できるように文字コードを指定する
    res.encoding = 'cp932'
    # レスポンスオブジェクトを返す
    return res

## 検索方法選択ページ、施設リストページに移動する
def go_to_search_menu(cfg, cookies, response, logger=None):
    """
    検索方法選択ページ、施設リストページに移動する
    """
    logger.debug(f'get top page form data.')
    # トップページのform_dataを取得する
    form_data = get_formdata(response, logger=logger)
    # 選択メニューを表示する
    form_data['menuNo'] = 1
    #print(form_data_top)
    # 検索方法指定ページに移動する
    res = do_post_request(cookies, form_data, cfg['first_url'], cfg['second_url'])
    # form_dataを取得し、パラメータを一部書き換える
    form_data = get_formdata(res, logger=logger)
    form_data['conditionMode'] = 1
    # 施設リストページを表示する
    res = do_post_request(cookies, form_data, cfg['second_url'], cfg['third_url'])
    # 施設リストページを返す
    return res, cfg['third_url']

# 対象施設の空き予約を取得する
def get_reserves(cfg, month_list, date_list, reserves_list, cookies, response, pre_url, logger=None):
    """
    監視対象施設の月間予約について検索する
    """
    #　対象施設の月間予約ページを取得する
    form_data = get_formdata(response, logger=logger)
    # 監視対象リストから、、各監視対象施設別の月間予約ページを取得する
    for _institution_code, _institution_name in cfg['institution_list'].items():
        # 施設を指定するパラメータを含んだフォームデータを作成する
        form_data['selectBldCd'] = _institution_code
        # 翌月リンクのクリック数を初期化する
        _next_month_click = 0
        for _year_month in month_list:
            #print(f'TargetYearMonth: {_year_month}')
            # 翌月リンクをクリックした場合のフォームデータとURLを作成する
            if _next_month_click >= 1:
                _year = str(_year_month[0])
                _month = str(_year_month[1]).zfill(2)
                _ymd = str(_year) + str(_month) + '01'
                #print(f'Year:{_year}, Month:{_month}, YMD:{_ymd}')
                form_data = {
                    'displayNo': 'prwmo1000',
                    'dispYY': _year,
                    'dispMM': _month,
                    'dispDD': '01',
                    'selectYY': _year,
                    'selectMM': _month,
                    'selectDD': '01',
                    'srchSelectYMD': _ymd,
                    'srchSelectInstNo': '0',
                    'transVacantMode': '0'
                }
                pre_url = cfg['court_search_url']
                target_url = cfg['month_search_url']
            else:
                target_url = cfg['court_search_url']
            # 
            # 対象施設の対象月の月間予約ページを取得する
            #logger.debug(f'{form_data}')
            res = do_post_request(cookies, form_data, pre_url, target_url)
            logger.debug(f'Institution_Name : {_institution_name}')
            #reserve_tools.save_html_file(res)
            form_data = get_formdata(res, logger=logger)
            # 月間予約ページから空き予約日リストを生成する
            reserve_days_list = get_reserve_day(date_list, res, logger=logger)
            # 空き予約日を指定して、施設のコート・時間帯ページを表示する
            for _day in reserve_days_list:
                # 空き予約日を指定するパラメータを含んだフォームデータを生成する
                form_data['dispYY'] = str(_day[0])
                form_data['dispMM'] = str(_day[1])
                form_data['dispDD'] = str(_day[2])
                form_data['selectYY'] = str(_day[0])
                form_data['selectMM'] = str(_day[1])
                form_data['selectDD'] = str(_day[2])
                form_data['srchSelectYMD'] = str(_day[0]) + str(_day[1]).zfill(2) + str(_day[2]).zfill(2)
                form_data['srchSelectInstNo'] = '0'
                form_data['transVacantMode'] = '7'
                #logger.debug(f'FormData: {form_data["dispYY"]}  {form_data["dispMM"]} , {form_data["dispDD"]} , {form_data["srchSelectYMD"]} , {form_data["srchSelectInstNo"]} , {form_data["transVacantMode"]}')
                #logger.debug(f'{form_data["srchSelectYMD"]}')
                # 空き予約日の施設のコート・時間帯ページを表示する
                res_reserve = do_post_request(cookies, form_data, cfg['court_search_url'], cfg['day_search_url'])
                #reserve_tools.save_html_file(res_reserve)
                # 空きコートと時間帯を取得する
                reserves_list = get_empty_court_time(cfg, form_data, res_reserve, reserves_list, logger=logger)
            # 翌月のリンクをクリックするため、カウントアップする
            _next_month_click += 1
    return reserves_list

# 指定した年月日のコート空き予約ページから空き予約の時間帯を取得する
def get_empty_court_time(cfg, form_data, response, reserves_list, logger=None):
    """
    空き予約日のコート番号と時間帯を取得する
    """
    _empty_day = form_data['srchSelectYMD']
    # レスポンスオブジェクトをHTML化する
    html = response.text
    soup = BeautifulSoup(html, features='html.parser')
    # 施設の指定日予約ページから施設名と時間帯のリストを取得する
    # 施設名を取得する
    _table = soup.find(class_="akitablelist")
    institution_name = _table.find('a').text
    # テーブルの時間帯列名を取得する
    _index = _table.find('tr')
    # 空き予約日の文字列
    _thead_day = ''
    # テーブルの時間帯列名のリスト
    _thead_times = []
    # テーブルを解析する
    for _head in _index:
        if _thead_day == "":
            # 空き予約日を取得する。最初のセルに空き予約日が表示されている
             _thead_day = _head.text
        else:
            # 2セル目以降は空き情報となる
            _thead_times.append(_head.text)
            # カラムのサイズを取得する。後で空き予約時間帯の計算で利用する
            _colum_size = _head['colspan']
    # 最終時間帯の要素を追加する。最終時間帯をなめる時にエラーが出てしまうので、その回避のため。
    _last = _thead_times[-1].replace('時', '')
    #print(_thead_times[-1])
    _last_hour = int(_last) + 1
    _last_string = str(_last_hour) + '時'
    _thead_times.append(_last_string)
    # 時間帯列名のリストの長さを取得する
    _colum_num = len(_thead_times)

    # reserves_listにKey:{_thead_day} が存在しない場合は、reserves_list[_thead_day]を初期化する。
    if _empty_day not in reserves_list:
        reserves_list[_empty_day] = {}

    # 空き予約があるコートのテーブル行を取得する
    a_tag_list = soup.find_all('img')
    for a_tag in a_tag_list:
        if a_tag.get('alt') == '空き':
            # テーブル行を取得する
            tr_tag = a_tag.find_parent('tr')
            # コート名を取得し、施設名と結合させる
            court_name = tr_tag.find('strong').text
            # 除外施設の場合は次の行に移る
            # 除外コートのリンクは追加しないため、リンクに除外コートのコート番号を確認する
            _exclude_court_count = len(cfg['exclude_courts'])
            _match_count = 0
            for _exclude_court in cfg['exclude_courts']:
                if _exclude_court == court_name:
                    logger.debug(f'found exclude court: {_exclude_court}')
                    break
                else:
                    # 除外コートリストにマッチしなかったのでカウントアップする
                    _match_count += 1
                    # マッチしなかった回数がリスト数より多くなれば処理を進める
                    if _match_count >= _exclude_court_count:
                        court_fullname = institution_name + '_' + court_name
                        # 予約時間帯を計算する
                        # tdタグのcolspanから時間帯を計算する
                        col_list = tr_tag.find_all('td')
                        # 空き予約のカラムの位置を調べるための変数を定義する
                        _colum_pos = 0
                        for _td in col_list:
                            # カラムの位置を計算する
                            _pos_span =  int(_td['colspan']) / int(_colum_size)
                            _pos = int(_pos_span + _colum_pos)
                            if _td.img['alt'] == "空き":
                                # 空き時間帯名を作成する。
                                _empty = _thead_times[_colum_pos] + "-" + _thead_times[int(_pos)]
                                # 空き予約リストに追加する
                                # 空き予約時間帯が存在しない場合は追加する
                                if _empty not in reserves_list[_empty_day]:
                                    reserves_list[_empty_day].setdefault(_empty,[]).append(court_fullname)
                                # すでに他の空き予約でこの時間帯が存在した場合
                                # 同じコートで時間帯がずれている場合、2重登録されるのを防止する
                                else:
                                    # 同じコート名が登録されていない場合のみ登録する
                                    if court_fullname not in reserves_list[_empty_day][_empty]:
                                        reserves_list[_empty_day][_empty].append(court_fullname)
                            # カラムのポジションを加算する
                            _colum_pos += int(_pos_span)
    # 空き予約リストを返す
    # logger.info(f'reserves_list: {reserves_list}')
    return reserves_list

# 空き予約日リストを生成する
def get_reserve_day(date_list, response, logger=None):
    """
    施設の月間空き予約ページから空き予約日リストを作成する
    """
    # 施設の月間空き予約ページの結果を解析し、空き予約日リストを作成する
    # 空き予約リストを初期化する
    _court_empty_day_list = []
    reserve_days_list = []
    # 空きコート名のリンクを取得する
    ## レスポンスオブジェクトをHTML化する
    html = response.text
    soup = BeautifulSoup(html, features='html.parser')
    # aタグのhref属性を持つタグを抽出する
    a_tag_list = soup.find_all('a')
    for a_tag in a_tag_list:
        # 空きまたは一部空きでhref='javascript:selectDay...'であるタグを抽出する
        if "javascript:selectDay((_dom == 3) ? document.layers['disp'].document.form1 : document.form1, gRsvWInstSrchVacantWAllAction" in str(a_tag.get('href')):
            # 空き予約日の取得する
            ## 区切り文字", "で文字列を分割する#
            _m = re.split(r',\s+', a_tag.get('href'))
            #_condition = re.search(r'\d+', _m[2])
            _year = re.search(r'\d+', _m[3])
            _month = re.search(r'\d+', _m[4])
            _day = re.search(r'\d+', _m[5])
            # 空き予約日のリストを作成する
            _reserve_day = [ _year.group(), _month.group(), _day.group() ]
            # 施設別空き予約日リストに追加する
            _court_empty_day_list.append(_reserve_day)
    # 発見した空き予約日をチェックする
    for _empty_day in _court_empty_day_list:
        #print(f'EmptyDay: {_empty_day}')
        # 希望する予約日と発見した空き予約日が一致するか確認し、一致したらリストに追加する
        for _want_day in date_list:
            if _want_day == _empty_day:
                reserve_days_list.append(_empty_day)
                break
            #else:
            #    print(f'not matched want day. compare to {_want_day}')
    # 希望に沿った空き予約日リストを返す
    # logger.info(f'reserve_days_list: {reserve_days_list}')
    return reserve_days_list

# メインルーチン
def main():
    """
    メインルーチン
    """
    # 祝日の初期化
    public_holiday = [ [], [], [], [], [], [], [], [], [], [], [], [], [] ]
    # 送信メッセージリストの初期化
    message_bodies = []
    # 処理の開始
    # 空き予約リストの初期化
    reserves_list = {}
    # 祝日設定ファイルを読み込んで、祝日リストを作成する
    reserve_tools.set_public_holiday('public_holiday.json', public_holiday)
    # 設定ファイルを読み込んで、設定パラメータをセットする
    cfg = reserve_tools.read_json_cfg('cfg.json')
    # ロギングを設定する
    logger = reserve_tools.mylogger(cfg)
    # 検索リストを作成する
    target_months_list = reserve_tools.create_month_list(cfg, logger=logger)
    #datetime_list = create_datetime_list(target_months_list, public_holiday, cfg)
    date_list = reserve_tools.create_date_list_chofu(target_months_list, public_holiday, cfg)
    target_year_month_list = reserve_tools.create_year_month_list(target_months_list)
    logger.info(f'target_year_month_list: {target_year_month_list}')

    # 空き予約ページにアクセスし、cookieを取得する
    ( cookies , response )= get_cookie(cfg)
    # 検索方法選択ページ、施設リストページにアクセスする
    ( response, pre_url ) = go_to_search_menu(cfg, cookies, response, logger=logger)
    # 空き予約検索を開始する
    reserves_list = get_reserves(cfg, target_year_month_list, date_list, reserves_list, cookies, response, pre_url, logger=logger)
    logger.info(json.dumps(reserves_list, indent=2, ensure_ascii=False))
    # 空きコート予約メッセージを送信する
    ## メッセージ本体を作成する
    message_bodies = reserve_tools.create_message_body(reserves_list, message_bodies, cfg, logger=logger)
    ## LINEに空き予約情報を送信する
    # reserve_tools.send_line_notify(message_bodies, cfg['line_token'], logger=logger)
    # Discordに空き予約情報のメッセージを送信する
    reserve_tools.send_discord_channel(message_bodies, cfg['discord_token'], cfg['discord_channel_id'], logger=logger)
    #exit()
    return logger
    
if __name__ == '__main__':
    # 実行時間を測定する
    start = time.time()
    # メイン処理
    logger = main()
    # デバッグ用(HTTPリクエスト回数を表示する)
    logger.debug(f'HTTP リクエスト数 whole(): {http_req_num} 回数')
    # 実行時間を表示する
    elapsed_time = time.time() - start
    logger.debug(f'whole() duration time: {elapsed_time} sec')
    exit()
