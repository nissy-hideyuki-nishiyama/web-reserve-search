# web-reserve-search for tama

# 多摩市施設予約検索と予約プログラム

## プログラムの目的
- 多摩市の施設予約でテニスコートの空きコートを探し通知する
- 登録している利用者IDを使って空きコートを予約する

## 機能概要
- cronジョブで起動される
- 非同期処理で空きコートを検索し、dict型リストに空きコートを登録する
  - 空きコート予約のdict型リストの構造
   ```bash
  { 
    date: {
        time: [
            court
        ]
    }
  }
  ```
  - 空きコート予約の検索が完了すると、所定のLINEグループに空きコート予約情報を通知する
- 上記のdict型リストを使って、予約処理を開始する
  - 空きコート予約リストが空(0件)の場合は予約処理を中止し、プログラムを終了する
  - コートの優先度を考慮して、空き予約リストから予約対象リストを生成する
  - 登録された利用者IDを使って予約処理を始める
  - 利用者IDの既存の予約済みリストと件数(全体件数と翌月土日件数)を取得し、予約上限数を超えている場合は次のIDで予約処理をする
  - 予約対象リストに従って、日付と時間で昇順に実施される
  - 予約ができた場合、所定のLINEグループに通知する

## 仕様
- 設定ファイル(cfg.json、ファイル名固定)でプログラムの定義する
- 祝日は祝日定義ファイル(public_holiday.json)で定義する
- コート名とコートのコードの対応ファイル(court_map.json)で定義する
- 非同期処理の同時実行数(threads_num)を指定できる
- 空き予約コート検索において、次を設定できる
  - 検索対象日は曜日で指定する。月曜日(0)から日曜日(6)で、曜日コードで指定する
  - 個別に検索したい日は設定ファイルの"want_month_days"で指定する
  - 検索から除外するコートをコートのコード("0040:00004")で指定する
  - 検索から除外する時間帯(06:00～08:00、16:00～17:00)を指定する
- 予約処理において、次を設定できる
  - 予約したい時間帯(06:00～08:00、16:00～17:00)を指定する
  - 予約したいコート(多摩東公園庭球場Ｄ（人工芝）)をフルネームで指定する。リストの順がコートの優先順位となる
  - 予約処理に使う利用者ID(複数可能)を指定する。利用者IDは次のタイプに分かれる
    - admin: 福島さん(1つのみ)
    - inners: 市内在住者(複数可能)
    - outers: 市外居住者(複数可能)
    - 利用者IDは、admin, inner, outerの順で予約処理に利用される
  - 今日から〇日以降を予約したい場合、この〇日(days_later)を設定する。これはキャンセル料が発生する予約は取らないために作った
  - 予約開放日(open_day、多摩市の場合は16日)を指定する。予約開放日によって挙動が変わる
    - 予約開放日前と以降では予約上限数と翌月土日予約上限数が変わる。それぞれ指定する
    - 予約開放日前はadminとinnersの利用者IDを使うが、以降は全てのIDを使う
  - 予約処理は日付と時間帯で昇順に実施される。1つのIDでは同日同時間帯では一つのコートのみ予約する
  - 次回の予約処理で残っている場合は他のコートを予約できる
  - 予約上限数、翌月予約上限数を超えた場合、その利用者IDでの予約処理を終了し、次の予約者IDで予約処理を継続する
  - 予約処理ができると1件毎に所定のLINEグループに予約完了を通知する

## 設定ファイル(cfg.json)の説明
### 設定ファイルのパラメータ説明
上から順に説明する
- first_url: プログラム内で参照される値なので原則さわらない
- second_url: 同上
- third_url: 同上
- day_search_url: 同上
- court_search_url: 同上
- login_url: 同上
- reserve_url: 同上
- input_reserve_url: 同上
- result_reserve_url: 同上
- confirm_reserve_url: 同上
- cookie_sessionid: 同上
- cookie_starturl: 同上
- cookie_auth: 同上
- search_params: 同上(奈良原公園(0041)とそれ以外(0040)で検索区分が異なる)
- discord_token: 同上。通知に利用するDiscordアプリのトークンコード(固定値)を指定する
- discord_channel_id: 同上。通知先のDiscordチャンネルのチャンネルIDを指定する
- discord_reserved_channel_id: 同上。予約確定に対する通知先のDiscordチャンネルのチャンネルIDを指定する
- discord_max_message_size: 同上。Discordの最大文字数(2000文字固定)を指定する
- exclude_courts: 空き予約コート検索から除外したいコート(一の宮公園)のコードを記述する。コードはコート名とコートのコードの対応ファイル(court_map.json)を参照のこと
- exclude_times: 空き予約コート検索から除外したい時間帯を指定する
- line_token: 通知先のLINEグループに参加しているLINE Notifyのトークンコードを指定する
- line_token_reserved: 予約確定に対する通知先のLINEグループに参加しているLINE Notifyのトークンコードを指定する
- line_max_message_size: LINE Notifyの最大文字数(1000文字固定)を指定する
- threads_num: 非同期処理の同時実行数を指定する
- month_period: 空きコート予約検索の検索対象月期間を指定する。多摩市は2か月先の2となる
- start_day: 次の予約期間が開始される日を指定する。多摩市は毎月1日なので、1となる
- open_day: 予約開放日を指定する。多摩市は毎月16日なので、16となる
- want_weekdays: 空きコート予約で検索したい曜日を指定する。月曜日(0)から日曜日(6)で、曜日コードで指定する
- want_month_days: 上記の空きコート予約で検索したい曜日および祝日以外で空きコート予約で検索したい日を指定する
- exclude_month_days: 検索処理から除外したい日を指定する。検索できないため、空き予約処理もできない。
- exclude_want_month_days: 予約処理から除外したい日を指定する。空き予約コート検索はできるが、予約処理はしなくなる。(変更点)
- exclude_location: 予約処理から除外したいコートを指定する。空き予約コート検索はできるが、予約処理はしなくなる。
- days_later: プログラム起動日から〇日以降は予約処理対象とする〇日を指定する
- reserved_limit: 予約上限数(予約開放日前)を指定する
- reserved_limit_after_open_day: 予約上限数(予約開放日以降)を指定する
- reserved_limit_for_next_month: 翌月土日予約上限数(予約開放日前)を指定する
- reserved_limit_for_next_month_after_open_day: 翌月土日予約上限数(予約開放日以降)を指定する
- reserved_limit_in_same_day: 同日予約できる上限数を指定する。多摩市は同日で2件まで。
- userauth: 予約処理に使う利用者IDとパスワードを指定する。admin(管理者), inner(市内在住者), outer(市外居住者)のタイプがある。ID:PASSWORDとなっている
- want_location_list: 予約したいコート名を指定する。優先順位の高いものから並べる
- want_hour_list: 予約したい時間帯を指定する。


### 設定ファイルのサンプル
```bash
{
    "first_url": "https://www.task-asp.net/cu/ykr132241/app/ykr00000/ykr00001.aspx?y=132241",
    "second_url": "https://www.task-asp.net/cu/ykr132241/app/ykr00000/ykr00001.aspx",
    "third_url": "https://www.task-asp.net/cu/ykr132241/app/ykr30000/ykr30001.aspx",
    "day_search_url": "https://www.task-asp.net/cu/ykr132241/app/ykr30000/ykr31101.aspx",
    "court_search_url": "https://www.task-asp.net/cu/ykr132241/app/ykr30000/ykr31103.aspx",
    "login_url": "https://www.task-asp.net/cu/ykr132241/app/ykr00000/ykr00001.aspx?CMD=Login&EJS=1",
    "reserve_url": "https://www.task-asp.net/cu/ykr132241/app/ykr30000/ykr31104.aspx",
    "input_reserve_url": "https://www.task-asp.net/cu/ykr132241/app/ykr30000/ykr31105.aspx",
    "result_reserve_url": "https://www.task-asp.net/cu/ykr132241/app/ykr30000/ykr32001.aspx",
    "confirm_reserve_url": "https://www.task-asp.net/cu/ykr132241/app/ykr30000/ykr32002.aspx",
    "cookie_sessionid": "taskasp_cu_ykr_sessionid",
    "cookie_starturl" : "taskasp_cu_ykr_starturl",
    "cookie_auth": "taskasp_cu_ykr_auth",
    "search_params" : [
      "0040",
      "0041"
    ],
    "exclude_courts": [
      "0040:00004",
      "0040:00005"
    ],
    "exclude_times": [
      "16:00～17:00",
      "17:00～19:00",
      "18:00～19:00",
      "19:00～21:00"
    ],
    "line_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "line_token_reserved": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "line_max_message_size": 1000,
    "threads_num": 5,
    "month_period": 2,
    "start_day": 1,
    "open_day": 16,
    "want_weekdays": [ 1 ],
    "want_month_days": {
        "1": [],
        "2": [],
        "3": [],
        "4": [],
        "5": [],
        "6": [],
        "7": [],
        "8": [],
        "9": [],
        "10": [],
        "11": [],
        "12": []
    },
    "exclude_month_days": {
        "1": [],
        "2": [],
        "3": [],
        "4": [],
        "5": [],
        "6": [],
        "7": [],
        "8": [ 30 ],
        "9": [ 19 ],
        "10": [],
        "11": [],
        "12": []
    },
    "exclude_location": [
      "一ノ宮公園庭球場Ａ",
      "一ノ宮公園庭球場Ｂ"
    ],
    "userid": 123456,
    "password": 1234,
    "securityid": "",
    "days_later": 14,
    "reserved_limit": 10,
    "reserved_limit_after_open_day": 15,
    "reserved_limit_for_next_month": 2,
    "reserved_limit_for_next_month_after_open_day": 15,
    "reserved_limit_in_same_day": 2,
    "userauth": {
      "admin": {
        "1234": "password"
      },
      "inners": {
        "22222": "password",
        "33333": "password"
      },
      "outers": {
        "44444": "password"
      }
    },
    "want_location_list": [
      "多摩東公園庭球場Ａ（人工芝）",
      "多摩東公園庭球場Ｂ（人工芝）",
      "多摩東公園庭球場Ｃ（人工芝）",
      "多摩東公園庭球場Ｄ（人工芝）",
      "多摩東公園庭球場Ｅ（人工芝）",
      "多摩東公園庭球場Ｆ（人工芝）",
      "諏訪北公園庭球場Ａ",
      "諏訪北公園庭球場Ｂ",
      "永山南公園庭球場Ａ",
      "永山南公園庭球場Ｂ",
      "貝取北公園庭球場Ａ",
      "貝取北公園庭球場Ｂ",
      "一本杉公園庭球場Ａ",
      "一本杉公園庭球場Ｂ",
      "一本杉公園庭球場Ｃ",
      "一本杉公園庭球場Ｄ",
      "愛宕東公園庭球場Ａ",
      "愛宕東公園庭球場Ｂ",
      "愛宕東公園庭球場Ｃ",
      "奈良原公園庭球場Ａ",
      "奈良原公園庭球場Ｂ",
      "奈良原公園庭球場Ｃ",
      "奈良原公園庭球場Ｄ",
      "連光寺公園庭球場Ａ",
      "連光寺公園庭球場Ｂ",
      "多摩東公園庭球場Ｇ（クレー）"
    ],
    "want_hour_list": [
        "08:00～10:00",
        "10:00～12:00",
        "12:00～14:00",
        "14:00～16:00",
        "16:00～18:00"
    ]
}

```

## 祝日定義ファイル(public_holiday.json)
祝日を定義する。1年に1回メンテナンスする必要がある。下記は2021年のサンプルとなる
```bash
{
    "1": [ 1, 11 ],
    "2": [ 11, 23 ],
    "3": [ 20 ],
    "4": [ 29 ],
    "5": [ 3, 4, 5 ],
    "6": [],
    "7": [ 22, 23 ],
    "8": [ 9 ],
    "9": [ 20, 23 ],
    "10": [],
    "11": [ 3, 23 ],
    "12": []
}
```
## コート名とコートのコードの対応ファイル(court_map.json)
コート名とコートのコードを定義する。新しいコートや廃止されたコートがあった場合メンテナンスする
```bash
{
    "愛宕東公園庭球場Ａ": "0040:00001",
    "愛宕東公園庭球場Ｂ": "0040:00002",
    "愛宕東公園庭球場Ｃ": "0040:00003",
    "一ノ宮公園庭球場Ａ": "0040:00004",
    "一ノ宮公園庭球場Ｂ": "0040:00005",
    "一本杉公園庭球場Ａ": "0040:00006",
    "一本杉公園庭球場Ｂ": "0040:00007",
    "一本杉公園庭球場Ｃ": "0040:00008",
    "一本杉公園庭球場Ｄ": "0040:00009",
    "永山南公園庭球場Ａ": "0040:00010",
    "永山南公園庭球場Ｂ": "0040:00011",
    "貝取北公園庭球場Ａ": "0040:00012",
    "貝取北公園庭球場Ｂ": "0040:00013",
    "諏訪北公園庭球場Ａ": "0040:00014",
    "諏訪北公園庭球場Ｂ": "0040:00015",
    "多摩東公園庭球場Ａ（人工芝）": "0040:00016",
    "多摩東公園庭球場Ｂ（人工芝）": "0040:00017",
    "多摩東公園庭球場Ｃ（人工芝）": "0040:00018",
    "多摩東公園庭球場Ｄ（人工芝）": "0040:00019",
    "多摩東公園庭球場Ｅ（人工芝）": "0040:00020",
    "多摩東公園庭球場Ｆ（人工芝）": "0040:00021",
    "多摩東公園庭球場Ｇ（クレー）": "0040:00022",
    "連光寺公園庭球場Ａ": "0040:00026",
    "連光寺公園庭球場Ｂ": "0040:00027",
    "奈良原公園庭球場Ａ": "0041:00001",
    "奈良原公園庭球場Ｂ": "0041:00002",
    "奈良原公園庭球場Ｃ": "0041:00003",
    "奈良原公園庭球場Ｄ": "0041:00004"
}
```