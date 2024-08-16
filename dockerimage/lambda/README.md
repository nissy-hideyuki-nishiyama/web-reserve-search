# Lambda 向け WEBスクライブ専用Dockerコンテナ
## 経緯

‐ Chrome が バージョン 112 以降で、GUIモードとヘッドレスモードが統合され、ヘッドレスモードの互換性が向上した
‐ その影響で、ヘッドレスモードのバイナリサイズが増え、Lambda の外部ライブラリの上限値を超えてしまい、Lambda レイヤーに登録できなくなった
‐ これを解消するために、本コンテナをビルドした

## 本コンテナのアーキテクチャー

- public.ecr.aws/lambda/python:3.12　をベースにする
‐ Selenium 4.15.2 + その時点の Chrome の安定版( chrome-headless-shell, chromedriver )
- 2024/8時点で、Dockerコンテナのイメージサイズは1.49GB
  ‐ Docker Image Name : lambda_whith_python3.12_selenium
  - Docker Container Name : lambda_webscribe

## 制限事項

‐ Lambda ではマルチスレッドで動作させることができていないため、現在はシングルスレッドで稼働させている
  ‐ ローカルPCの Docker コンテナ上ではChrome-headless-sell をマルチスレッドで稼働できている
‐ このため、コードにはスレッド動作のためのコードがあるが、設定ファイル( cfg.json )の thread_num で 1 に制限している
‐ また、本体コードの Chrome のオプション設定で、options.add_argument('--single-process') を追加している
- 本ディレクトリには、Dockerfile, docker-compose.yml, requirements.txt, DeployDockerImage2Lambda.sh と利用するデプロイスクリプトのシンボリックリンクのみ存在する

# WEBスクライブ用の Lambda をデプロイする
## 事前準備

1. 該当ディレクトリを作成後、本ディレクトリをコピーする
```bash
$ mkdir site_lambda
$ cp -rf dockerimage/lambda/* site_lambda
```

2. アプリケーションディレクトリ(site_lambda/app/) 以下に、WEBスクライブのアプリケーションソースと設定ファイルを保存する
```bash
cp app.py config.json site_lambda/app/
```

3. (オプション)必要であれば、PIPパッケージのリストファイル(requirements.txt)を該当ディレクトリにコピーする
```bash
cp requirements.txt site_lambda/
```

4. 次のようなディレクトリ構造になっていればよい
```bash
./
├── BuildDockerImage_Lambda_with_Selenium.sh -> ../dockerimage/amzlx2023/BuildDockerImage_Lambda_with_Selenium.sh
├── DeployDockerImage2Lambda.sh -> ../dockerimage/lambda/DeployDockerImage2Lambda.sh
├── Dockerfile
├── GetLatestChromeVersion.sh -> ../dockerimage/amzlx2023/GetLatestChromeVersion.sh
├── app
│   ├── check_empty_reserves_multi_threads.py
│   └── reserve_tools
│       └── reserve_tools.py
├── docker-compose.yml
└── requirements.txt
```

## Docker イメージのビルド

1. 所定ディレクトリに移動し、ビルドスクリプトを実行する
```bash
$ cd site_lambda
$ bash ./BuildDockerImage_Lambda_with_Selenium.sh
```

## ローカル環境でのDocker コンテナの起動と Lambda としての動作確認

1. ビルドしたDocker イメージを指定して、Lambda 関数として、Docker コンテナを起動する。これによって、ローカルエンドポイントとして、
   `localhost:9000/2015-03-31/functions/function/invocations` が作成される。現在、所定のS3から cfg.json と public_holiday.json を
   /tmp以下のダウンロードするようにしているため、ローカル環境ではこのファイルを手動で作成する必要がある
```bash
$ docker run --platform linux/amd64 -p 9000:8080 lambda_whith_python3.12_selenium:latest
```

2. 新しいターミナルを開いて、イベントをローカルエンドポイントにポストする
```bash
$ curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
```

3. (デバッグ) Docker コンテナの bash コンソールにログインする
```bash
$ docker exec -it lambda_webscribe /bin/bash
```

4. (デバッグ) Docker コンテナで headless-shell を実行し、正常動作を確認する。コンソールにWEBサイトのデータが表示されたら、正常動作していることになる
```bash
bash-5.2# /usr/lib64/chromium-browser/headless_shell --no-sandbox --disable-gpu --disable-bluetooth --disable-dev-shm-usage --dump-dom https://www.google.com/
```

5. (デバッグ) この時にコンソールに下記のエラーメッセージが表示されるが、既知のエラーであり、WEBスクライブ地震には問題ない
```bash
bash-5.2# /usr/lib64/chromium-browser/headless_shell --no-sandbox --disable-gpu --disable-bluetooth --disable-dev-shm-usage --dump-dom https://www.google.com/
--- 下記がそのエラーメッセージ
[0812/102759.809143:WARNING:sandbox_linux.cc(430)] InitializeSandbox() called with multiple threads in process gpu-process.
[0812/102759.851592:WARNING:bluez_dbus_manager.cc(248)] Floss manager not present, cannot set Floss enable/disable.
<!DOCTYPE html>　<---- ここからWEBサイトのコンテンツが表示されている
```
6. Docker コンテナのコンソールからログアウトする
```bash
bash-5.2# exit
```

## ECR のプライベートリポジトリに登録し、Lambda にデプロイする

1. デプロイスクリプトの書式
```bash
bash DeployDockerImage2Lambda.sh --region ${AWS_REGION} --ecrrepo ${ECR_REPOSITORY_NAME} --dockerimg ${DOCKER_IMAGE_NAME} --lambdafunc ${LAMBDA_FUNCTION_NAME}

  -r|--region)       AWS Region Name
  -e|--ecrrepo)      AWS ECR Repository Name
  -i|--dockerimg)    upload Docker Image Name to ECR Repository
  -f|--lambdafunc)   deploy Lambda Function Name with registed Docker Image

  ex) bash DeployDockerImage2Lambda.sh --region ap-northeast-1 --ecrrepo ecr_repository_name --dockerimg dockerimage_name:tag --lambdafunc lambda_fuction_name'
```

2. 所定ディレクトリに移動し、デプロイスクリプトを実行する
```bash
$ cd site_lambda
$ bash DeployDockerImage2Lambda.sh --region ${AWS_REGION} --ecrrepo ${ECR_REPOSITORY_NAME} --dockerimg ${DOCKER_IMAGE_NAME} --lambdafunc ${LAMBDA_FUNCTION_NAME}
```

## Lamdab で 定期的に実行できるように Event Bridge に登録する

1. Lambda にデプロイしたバージョンについて、エイリアスを発行する
2. EventBridge で、所定のエイリアスのLambdaについて、定期実行するようにイベントのスケジュールルールを登録する

## 参考
- [コンテナイメージで Python Lambda 関数をデプロイする](https://docs.aws.amazon.com/ja_jp/lambda/latest/dg/python-image.html)
