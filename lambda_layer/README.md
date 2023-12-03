# Lambdaレイヤーのビルド

下記の2つの Lambda レイヤーを作成する

- selenimu_layer : Webスクレイピングするための selenium や beautifulsoup などのPIPパッケージ。
  - tama/requirements.txt を利用して PIP パッケージをビルドする
- headless-chromium : headless_chrome_shell の実行ファイルとライブラリ(今は利用していない)
  - chrome の headless_shell と chromedriver の Beta 版のバイナリ―パッケージを取得し、Lambda レイヤー用にビルドする
  - Stable 版は headless_shell 単体で公開されていないので、Beta 版を取得している
  - Chromium 版の自己ビルドするよりもフットプリントサイズが小さいため、2023/11時点ではこちらを採用している
  - また、Chromium 版の自己ビルドに戻すことは検討する

## selenimu_layer

下記のコマンドを実行すると、zipファイル作成後、S3バケットにアップロードした後、Lambdaレイヤーに登録する。

```bash
$ cd lambda_layer/selenium_layer
$ Update_selenium_layer.sh
```

## headless-chromium

下記のコマンドを実行すると、zipファイル作成後、S3バケットにアップロードした後、Lambdaレイヤーに登録する。

```bash
$ cd lambda_layer/headless-chromium
$ Update_headless_chrome_shell.sh
```

------------------------

# Chromiumのビルド＆コンパイル

- インストールオプションを設定する
```bash
build_chromium/chromium/src/build/install-build-deps.py
```

- 日本語ローケール : Chromiumのビルド時に日本語ローケルを含めるためには必要
```bash
$ sudo apt -y install language-pack-ja-base language-pack-ja
--- 下記は不要 ---
$ sudo localectl set-locale LANG=ja_JP.UTF-8 LANGUAGE="ja_JP:ja"
$ source /etc/default/locale
```

- Chromiumのビルドは出力先のディレクトリを指定して、区分する。出力先ディレクトリ以下ビルド設定ファイやビルド結果Chromeが保存される
- 下記のコマンドでビルド出力を作成し、設定する
  - gn gen out/Default : out/Default以下に設定する
  - gn gen out/Mini: out/Mini以下に設定する
  - コンパイル後は各種のオブジェクトファイルやライブラリファイルなどが生成されるため35GB となり、コンパイル前は、372MB程度
    - headless_shell をターゲットとしてコンパイルした場合、5GBとなった
- ビルドオプションを確認する
  - gn args --list out/${build_target_directory}
    - gn args --list out/Default
- ビルドオプションを編集する
  - gn args out/${build_target_directory}
    - gn args out/Default
    - エディタ(vim)が立ち上がり、編集できる。
    - 編集対象ファイルは、out/${build_target_directory}/args.gn となる
- headlessのビルドオプションを読み込ませるには下記の行をargs.gnに追加する
  - import("//build/args/headless.gn")'  を先頭に追加する
  - 上記ファイルはChromiumプロジェクトがheadlessとして適当であるという設定を書いたファイルであり、これをimportする
- headless_shellのフットプリントサイズは327MB、out/Defaultでコンパイルしたchromeは1.2GBになる
  - strip -o コマンド実行後はheadlless_shellは230MB、 chromeは310MBに減少する
- 下記の情報はchromeium 118の時の情報
  - headless_shellのフットプリントサイズは、非圧縮で230MB 、圧縮で97MB
  - chromedriverのフットプリントサイズは、非圧縮で15MB、圧縮で7MB
- seleniumレイヤーのフットプリントサイズは、非圧縮で60MB、圧縮で20MB


## 1. headless_chromiumのコンパイルオプション
build_chromium/chromium/src/build/args/headless.gn　のファイルに必要なオプションが記述されたファイルがある
このファイルをインポートすることで、headlessに必要なビルドオプションが設定される。これにいくつかのオプションを追加する

```bash
# Set build arguments here. See `gn help buildargs`.
import("//build/args/headless.gn")

is_debug = false
symbol_level = 0
blink_symbol_level = 0
v8_symbol_level = 0
is_component_build = false
enable_nacl = false

use_debug_fission = false
```

## 2. headless_shellをコンパイルする
headless_shellをターゲットとして、コンパイルしないと

In file included from ../../chrome/browser/platform_util_linux.cc:32:
../../dbus/bus.h:8:10: fatal error: 'dbus/dbus.h' file not found
#include <dbus/dbus.h>

でエラーとなり、ビルドできない。下記のコマンドでビルドを開始する

autoninja -C out/${build_target_directory} headless_shell  ※ ターゲットで headless_shell を指定する。それ以外はNG


## 参考:
- chromiumのビルド: https://chromium.googlesource.com/chromium/src.git/+/HEAD/docs/linux/build_instructions.md
- headless_chromeのビルド: https://chromium.googlesource.com/chromium/src/+/lkgr/headless/README.md
- gnコマンド: https://gn.googlesource.com/gn/+/main/docs/quick_start.md
