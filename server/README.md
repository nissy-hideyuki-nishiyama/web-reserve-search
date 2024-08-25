# WEBスクライブの開発環境の備忘録


## 開発環境

- WEBスクライブ専用ミニPC(Ubuntu22.04LTS、DockerのDEVコンテナ(開発環境)とLambda開発コンテナ、常時稼働型コンテナ(WEBスクライブ専用))
- 上記のマシンのDockerコンテナに接続して、開発する
- vsCode(Thinkpad T480で起動し、上記のミニPCにSSH接続後、DEVコンテナを起動する

## DEVコンテナと常時稼働型コンテナ、Lambda開発コンテナの共通仕様

- HostOS: Ubuntu 24.04 LTS
- Docker 27.1.1
- docker-composer 1.29.2

### DEVコンテナ

- $HOME/workddir/develop/web-reserve-search/.devcontainer 以下のファイルでDEVコンテナが起動される
- ubuntu 24.04 のDockerイメージ
- Dockerイメージのタグ: web-reserve-search_devcontainer_dev_webscribe
- Dockerコンテナ名: develop2023

### DEVコンテナへの接続

1. 手元のPCでvsCodeを起動し、リモート(トンネル/SSH)でミニPCに接続する
2. (Ubuntu:) $HOME/workddir/develop/web-reserve-search に移動して、.devcontainer/以下のファイルでDEVコンテナを起動する
3. (DEVコンテナ:) 上記の $HOME/workddir/develop/web-reserve-search が /workspace としてマウントされた状態でDEVコンテナに接続された状態となる


### Lambda開発コンテナ (TBD)

- $HOME/workddir/develop/web-reserve-search/(TBD) 以下のファイルでDEVコンテナが起動される
- aws/lambda/python:3.10-rapid-x86_64 のDockerイメージ
- Dockerイメージのタグ: public.ecr.aws/lambda/python:3.10-rapid-x86_64
- Dockerコンテナ名:  amazonlinux2023/webscribe_dev:latest　？
- AWS SAM にてローカル環境にLambdaの開発環境を準備する？

## 常時稼働型コンテナ(WEBスクライブ専用)

- $HOME/workddir/develop/web-reserve-search/server/ 以下のdocker-compose.ymlとDockerfileでコンテナを起動する
- AmazonLinux 2023 のDockerイメージ
- Dockerイメージのタグ: amazonlinux2023/webscribe_prod:latest
- Dockerコンテナ名: prod_amzlx2024

### 常時稼働型コンテナのビルドと起動

#### 常時稼働型コンテナの稼働状態の確認

1. 下記のコマンドをホストOS上で実行し、「/prod_amzlx2023 always」と表示されることを確認する。
```bash
$ docker inspect -f "{{.Name}} {{.HostConfig.RestartPolicy.Name}}" $(docker ps -aq) | grep always
/prod_amzlx2024 always
$
```
2. 表示されたコンテナは常時稼働型コンテナとして、自動起動に登録されていることになる
3. 上記のコンテナにログインし、稼働プロセス、サービス状態、cronジョブの登録状況を確認する
```bash
$ docker exec -it <container_name> /bin/bash
$ top
$ ps aux
$ systemctl status
$ crontab -l # rootアカウントで登録されたcronジョブを表示し、期待したスケジュールが登録されていればよい
$
```

#### 常時稼働型コンテナのコンテナイメージのビルド

1. (Ubuntu:) 作業ディレクトリ($HOME/workdir/webscribe)に移動し、gitリポジトリをCloneする
```bash
$ cd ~/workdir/webscribe
$ git clone git@github.com:nissy-hideyuki-nishiyama/web-reserve-search.git

$ cd web-reserve-search
$ git checkout main
$ git pull
```

2. (Ubuntu:) 常時稼働型コンテナのdocker-compose.ymlとDockerfile、cronjobファイルを作業ディレクトリにコピーする(bindがうまく解決できなかった)
```bash
$ cd ~/workdir/webscribe
$ cp -rf ./web-reserve-search/server/* ./
```

3. (Ubuntu:) serverディレクトリのdocker-compose.ymlを指定して、docker-composeコマンドで常時稼働型コンテナイメージをビルドする
```bash
$ docker compose -f ./docker-compose.yml up --build -d
```


#### 常時稼働型コンテナの起動準備

- 各予約サイト用の設定ファイルの配置と共通ライブラリディレクトリと祝祭日ファイルへのシンボリックリンク作成
- 各予約サイトのvenv環境の構築(近日中に開発ルートディレクトリのvenv環境に全て統合する(TBD))
- cronジョブファイルのインストール
- ローカル環境では下記の予約サイトが稼働している
  - 調布市
  - 八王子市
  - 町田市
  - 多摩市(開放日のみ)
  - 川崎市(開放日のみ)

1. (Ubuntu:) 各予約サイト用の設定ファイルの配置と共通ライブラリディレクトリと祝祭日ファイルへのシンボリックリンク作成
```bash
$ cd ~/workdir/webscribe/web-reserve-search/<city_name>
$ ln -s ../reserve_tools/public_holiday.json ./public_holiday.json
$ ln -s ../reserve_tools ./reserve_tools
$ cp ~/workdir/develop/web-reserve-search/config/<city_name>/cfg.json ./
[八王子市のみ]
$ cp ~/workdir/develop/web-reserve-search/config/<city_name>/menu_map.json ./
[多摩市のみ]
$ cp ~/workdir/develop/web-reserve-search/config/<city_name>/court_map.json ./
```

2. (Container:) 各予約サイトのvenv環境の構築(近日中に開発ルートディレクトリのvenv環境に全て統合した(2023/12/03))
```bash
# cd /web-reserve-search
# python3 -m venv .venv
# source .venv/bin/activate
# pip install -r tama_lambda/requirements.txt
# pip-review --auto

[動作確認]
# .venv/bin/python3 ./<prog_name>.py
```

3. (Container:) cronジョブファイルのインストール
```bash
# cd /webscribe
# crontab -u root /web-reserve-search/server/cron.d/root.cron
```

4. (Container:) 空き予約プログラムの稼働状態確認
```bash
# systemctl status
# crontab -l 
# ps aux
# top
# ls -l /var/log/webscribe/*
# tail -30 /var/log/webscribe/*
# tail -f /var/log/cron
```
