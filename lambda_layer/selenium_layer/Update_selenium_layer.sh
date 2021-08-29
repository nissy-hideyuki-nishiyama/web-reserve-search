#!/bin/bash
set -xeu

# 定数
Root_Work_Dir=/home/hnishi/workdir/webscribe
Work_Dir=${Root_Work_Dir}/selenium_layer
Zip_Filename=selenium_layer.zip
Region=ap-northeast-1
Profile=default
AWSCMD="aws --region ${Region} --profile ${Profile}"
LayerName=selenium_layer
S3Bucket=nissy-jp-distfiles-tky
S3Path=build_lambda/lambda_layer


# カレントディレクトリのパス取得と変数設定
Current_Dir=$(pwd)

# 作業ディレクトリへの移動
cd ${Work_Dir}

# 古いzipファイルと作業ディレクトリの削除
echo "Delete older work directory and zip file."
rm -rf python ${Zip_Filename}

# 八王子のrequirements.txtから必要なpipパッケージをダウンロードする
echo "Get requirements.txt and create library zip."
mkdir -p ${Work_Dir}/python
pip install -t  ${Work_Dir}/python -r ${Root_Work_Dir}/hachioji/requirements.txt 

# zipファイルを作成する
zip -ry ${Zip_Filename} ./python

# zipファイルを所定のディレクトリにアップロードする
${AWSCMD} s3 cp ./${Zip_Filename} s3://${S3Bucket}/${S3Path}/
exit

# 所定のLambdaレイヤーに登録する
${AWSCMD} lambda publish-layer-version --layer-name ${LayerName} \
  --description "selenium_and_other_etc_pip_lib" \
  --license-info "BSD" --compatible-runtimes python3.6 python3.7 python3.8 \
  --content S3Bucket=${S3Bucket},S3Key=${S3Path}/${Zip_Filename}
