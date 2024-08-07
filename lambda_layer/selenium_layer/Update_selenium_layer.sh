#!/bin/bash
set -xeou

# 定数
# Root_Work_Dir=/home/hnishi/workdir/web-reserve-search
Root_Work_Dir=/workspace
Work_Dir=${Root_Work_Dir}/lambda_layer/selenium_layer
Zip_Filename=selenium_layer.zip
Region=ap-northeast-1
Profile=default
AWSCMD="aws --no-cli-pager --no-paginate --region ${Region} --profile ${Profile}"
LayerName=selenium_layer
S3Bucket=nissy-jp-distfiles-tky
S3Path=build_lambda/lambda_layer
Date=$(date +%Y%m%d-%H%M)

# カレントディレクトリのパス取得と変数設定
Current_Dir=$(pwd)

# スクリプト終了後の事後処理
trap "cd ${Work_Dir} && rm ${Zip_Filename}" 0

# 作業ディレクトリへの移動
cd ${Work_Dir}

# 古いzipファイルと作業ディレクトリの削除
echo "Delete older work directory and zip file."
rm -rf python ${Zip_Filename}

# 多摩市のrequirements.txtから必要なpipパッケージをダウンロードする
echo "Get requirements.txt and create library zip."
mkdir -p ${Work_Dir}/python
pip3.12 install -t  ${Work_Dir}/python -r ${Root_Work_Dir}/tama/requirements.txt --use-pep517

# zipファイルを作成する
zip -ry ${Zip_Filename} ./python

# zipファイルを所定のディレクトリにアップロードする
${AWSCMD} s3 cp ./${Zip_Filename} s3://${S3Bucket}/${S3Path}/
#exit

# 所定のLambdaレイヤーに登録する
${AWSCMD} lambda publish-layer-version --layer-name ${LayerName} \
  --description "selenium_and_other_etc_pip_lib at ${Date}" \
  --license-info "BSD" --compatible-runtimes python3.11 python3.12\
  --content S3Bucket=${S3Bucket},S3Key=${S3Path}/${Zip_Filename}
