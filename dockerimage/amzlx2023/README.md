# WEBスクライブ専用Dockerコンテナ
## 経緯

‐ Chrome が バージョン 112 以降で、GUIモードとヘッドレスモードが統合され、ヘッドレスモードの互換性が向上した
‐ その影響で、ヘッドレスモードのバイナリサイズが増え、Lambda の外部ライブラリの上限値を超えてしまい、Lambda レイヤーに登録できなくなった
‐ これを解消するために、本コンテナをビルドした

## 本コンテナのアーキテクチャー

- Amazon Linux 2023 ベースコンテナ
‐ Selenium 4.15.2 + その時点の Chrome の安定版( chrome-headless-shell, chromedriver )
- 2024/8時点で、Dockerコンテナのイメージサイズは1.49GB
  ‐ Docker Image Name : lambda_with_amzlx2023_selenium
  - Docker Container Name : amzlx2024_webscribe

## 制限事項

‐ Lambda ではマルチスレッドで動作させることができていないため、現在はシングルスレッドで稼働させている
  ‐ ローカルPCの Docker コンテナ上ではChrome-headless-sell をマルチスレッドで稼働できている
‐ このため、コードにはスレッド動作のためのコードがあるが、設定ファイル( cfg.json )の thread_num で 1 に制限している
‐ また、本体コードの Chrome のオプション設定で、options.add_argument('--single-process') を追加している。

## Docker イメージのビルド

1. 所定ディレクトいに移動し、ビルドスクリプトを実行する
```bash
$ cd dockerimage/amzlx2023
$ bash ./BuildDockerImage_Lambda_with_Selenium.sh
```

## Docker コンテナの起動と headless-shell の動作確認

1. ビルドしたDocker イメージを指定して、Docker コンテナを起動する
```bash
$ docker run -it lambda_with_amzlx2023_selenium -t amzlx2024_webscribe /bin/bash

[上記で失敗したら次を試す]
$ docker start amzlx2024_webscribe 
```

2. Docker コンテナの bash コンソールにログインする
```bash
$ docker exec -it amzlx2024_webscribe /bin/bash
```

3. Docker コンテナで headless-shell を実行し、正常動作を確認する。コンソールにWEBサイトのデータが表示されたら、正常動作していることになる
```bash
bash-5.2# /usr/lib64/chromium-browser/headless_shell --no-sandbox --disable-gpu --disable-bluetooth --disable-dev-shm-usage --dump-dom https://www.google.com/
```

4. この時にコンソールに下記のエラーメッセージが表示されるが、既知のエラーであり、WEBスクライブ地震には問題ない
```bash
bash-5.2# /usr/lib64/chromium-browser/headless_shell --no-sandbox --disable-gpu --disable-bluetooth --disable-dev-shm-usage --dump-dom https://www.google.com/
--- 下記がそのエラーメッセージ
[0812/102759.809143:WARNING:sandbox_linux.cc(430)] InitializeSandbox() called with multiple threads in process gpu-process.
[0812/102759.851592:WARNING:bluez_dbus_manager.cc(248)] Floss manager not present, cannot set Floss enable/disable.
<!DOCTYPE html>　<---- ここからWEBサイトのコンテンツが表示されている
```
5. Docker コンテナのコンソールからログアウトする
```bash
bash-5.2# exit
```
