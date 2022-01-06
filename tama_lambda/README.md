Lambdaのローカル開発環境の構築
[参考]
- python-lambda-local と lambda-uploader を使ってローカル環境で Lambda 開発を行う
  https://sig9.hatenablog.com/entry/2020/02/08/000000

[概要]
1. venv 環境の構築
cd [work_dir] : 例: web-reserve-search/martgd
python3 -m venv venv
. venv/bin/activate

2. python-lambda-local lambda-uploaderモジュールのインストール
pip3 install python-lambda-local lambda-uploader

3. 作業環境の構築
cd /home/hnishi/workdir/lambda-local/web-reserve-search/martgd

3-1. 設定ファイルの作成
- event.json
{}


- requirement.txt
空: 必要なライブラリはLambda-Layerで読み込んでいるため、個別にはインストールしない


3-2. 設定ファイルと祝日リストファイルを/tmpにコピーする
上記ファイルがない場合、S3からダウンロードするコードなので、それを代替する。
本番環境のS3にアクセスさせないようにできる。
cp cfg.json public_holiday.json /tmp/


4. コーディング・デバッグ


5. Lambdaのローカル実行
タイムアウト時間を明確に定義しないとデフォルトの3秒が適用されてしまう。
python-lambda-local -t 180 -f lambda_handler lambda_function.py event.json

(venv) [hnishi@gd41amzlx2 martgd]$ python-lambda-local -h
usage: python-lambda-local [-h] [-l LIBRARY_PATH] [-f HANDLER_FUNCTION]
                           [-t TIMEOUT] [-a ARN_STRING] [-v VERSION_NAME]
                           [-e ENVIRONMENT_VARIABLES] [--version]
                           FILE EVENT

Run AWS Lambda function written in Python on local machine.

positional arguments:
  FILE                  lambda function file name
  EVENT                 event data file name

optional arguments:
  -h, --help            show this help message and exit
  -l LIBRARY_PATH, --library LIBRARY_PATH
                        path of 3rd party libraries
  -f HANDLER_FUNCTION, --function HANDLER_FUNCTION
                        lambda function handler name, default: "handler"
  -t TIMEOUT, --timeout TIMEOUT
                        seconds until lambda function timeout, default: 3
  -a ARN_STRING, --arn-string ARN_STRING
                        ARN string for lambda function
  -v VERSION_NAME, --version-name VERSION_NAME
                        lambda function version name
  -e ENVIRONMENT_VARIABLES, --environment-variables ENVIRONMENT_VARIABLES
                        path to flat json file with environment variables
  --version             print the version of python-lambda-local and exit
You have mail in /var/spool/mail/hnishi

4. Lambdaコードのアップロードと登録
4-0. 以前のzipファイルを削除する
rm lambda_function.zip

4-1. lambda-uploaderの設定ファイル
- lambda.json
{
  "name": "webscribe-martgd",
  "description": "webscribe martgd search empty reserver",
  "region": "ap-northeast-1",
  "runtime": "python3.7",
  "handler": "lambda_function.lambda_handler",
  "role": "arn:aws:iam::500421251886:role/webscribe-lambda-role",
  "timeout": 180,
  "memory": 128,
  "requirements": [
    
  ],
  "ignore": [
    "circle\\.yml$",
    "\\.git$",
    "/.*\\.pyc",
    "bin",
    "lib",
    "lib64",
    "__pycache__",
    "pyenv.cfg",
    "public_holiday.*",
    "cfg.json",
    "event.json",
    "get_empty_reserves.py",
    "org_.*",
    "lambda.json",
    "\\.gitignore"
  ]
}

4-2. Lambdaにアップロードするファイルを作成する
zip lambda_function.zip lambda_function.py reserve_tools.py

4-3. lambda-uploaderを利用してアップロードする
lambda-uploader --no-build -V

2回目以降は、下記のようなメッセージが表示されるが、最新版としてLambdaにアップロードされている。
```bash
botocore.errorfactory.ResourceConflictException: An error occurred (ResourceConflictException) when calling the UpdateFunctionConfiguration operation: The operation cannot be performed at this time. An update is in progress for resource: arn:aws:lambda:ap-northeast-1:500421251886:function:webscribe-kawasaki
```

4-4. Lambda Layerをアタッチする(初回のみ必要)
selenium_layerの最新版をアタッチする。

4-5. Lambda上での動作確認
テストボタンをクリックして、動作確認する。
コンソールが表示されるので、ログを確認する

4-6. Lambdaのバージョンを発行する
動作確認完了後、正式なものとして、新しいバージョンを発行する

4-7. Lambdaのバージョンにエイリアスを紐づける
発行したLambdaのバージョンに対して、現在本番稼働しているEventBridgeルールに紐づけられているエイリアスを新しいバージョンに付け替える

5. Lambdaのチューニング
Lambdaのメモリ割り当てを自動で最適化！！AWS Lambda Power Tuning
https://dev.classmethod.jp/articles/aws-lambda-power-tuning/#toc-5