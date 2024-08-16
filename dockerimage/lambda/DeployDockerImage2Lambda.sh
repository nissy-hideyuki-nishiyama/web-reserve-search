#!/bin/bash

set -xeou

# アーカイブ世代。これ以上前のバージョンは削除する
GEN=3
#
AWSCMD=( aws --no-cli-pager --no-paginate )

# 必要な変数
AWS_ACCOUNT_ID=''
AWS_REGION=''
ECR_REPOSITORY_NAME=''
DOCKER_IMAGE_NAME=''
LAMBDA_FUNCTION_NAME=''

# コマンド引数を確認する
while [[ "$#" -gt 0 ]]
do
    case $1 in
        -r|--region) AWS_REGION="$2"; shift;;
        -e|--ecrrepo) ECR_REPOSITORY_NAME="$2"; shift;;
        -i|--dockerimg) DOCKER_IMAGE_NAME="$2"; shift;;
        -f|--lambdafunc) LAMBDA_FUNCTION_NAME="$2"; shift;;
    esac
    shift
done

if [ -z "${AWS_REGION}" ] || [ -z "${ECR_REPOSITORY_NAME}" ] || [ -z "${DOCKER_IMAGE_NAME}" ] ||  [ -z "${LAMBDA_FUNCTION_NAME}" ]; then
    echo 'not found args'
    echo 'bash DeployDockerImage2Lambda.sh --region ${AWS_REGION} --ecrrepo ${ECR_REPOSITORY_NAME} --dockerimg ${DOCKER_IMAGE_NAME} --lambdafunc ${LAMBDA_FUNCTION_NAME}'
    echo '  -r|--region)       AWS Region Name'
    echo '  -e|--ecrrepo)      AWS ECR Repository Name'
    echo '  -i|--dockerimg)    upload Docker Image Name to ECR Repository'
    echo '  -f|--lambdafunc)   deploy Lambda Function Name with registed Docker Image'
    echo '  ex) bash DeployDockerImage2Lambda.sh --region ap-northeast-1 --ecrrepo ecr_repository_name --dockerimg dockerimage_name:tag --lambdafunc lambda_fuction_name'
    exit 1
fi

# AWSのクレデンシャル情報に関する環境変数が設定されているかを確認する
if [ -z "${AWS_ACCESS_KEY_ID}" ] || [ -z "${AWS_SECRET_ACCESS_KEY}" ]; then
    echo "AWSクレデンシャル情報が設定されていません。"
    exit 1
else
    echo "AWSクレデンシャル情報が設定されています。"
fi

# AWSアカウントIDを取得する
AWS_ACCOUNT_ID="$("${AWSCMD[@]}" sts get-caller-identity --query "Account" --output text)"

# ビルド前の準備
WORK_DIR="$(pwd)"
echo "WORK_DIR: ${WORK_DIR}"

# docker 認証を AWS の ECR レポジトリのログインと紐づける
"${AWSCMD[@]}" ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# ECR リポジトリを作成する
REPO_EXISTS="$("${AWSCMD[@]}" ecr describe-repositories --repository-names "${ECR_REPOSITORY_NAME}" 2>&1)"

if [[ $REPO_EXISTS == *"RepositoryNotFoundException"* ]]; then
  "${AWSCMD[@]}" ecr create-repository --repository-name "${ECR_REPOSITORY_NAME}" --region "${AWS_REGION}" --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
  echo "Repository ${ECR_REPOSITORY_NAME} created."
else
  echo "Repository ${ECR_REPOSITORY_NAME} already exists."
fi

# アップロード対象の Docker イメージにタグをつける
docker tag "${DOCKER_IMAGE_NAME}" "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:latest"

# Docker イメージを ECR レポジトリにアップロードする
docker push "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:latest"

# アップロードが完了するまで待機する
#"${AWSCMD[@]}" ecr wait image-scan-complete --repository-name "${ECR_REPOSITORY_NAME}" 

# ECR レポジトリでタグが付いていない古い Docker イメージを削除する
IMAGES="$("${AWSCMD[@]}" ecr list-images --repository-name "${ECR_REPOSITORY_NAME}" --filter tagStatus=UNTAGGED --output text --query ImageIds[].ImageDigest)"
IMAGE_ARRAY=(${IMAGES})
if [ ! -z "${IMAGE_ARREY[@]}" ]; then
    DIGEST_IDS=''
    for imgid in ${IMAGE_ARREY[@]}
    do
        DIGEST_IDS+="ImageDigest=${imageid} "
    done
    "${AWSCMD[@]}" ecr batch-delete-image --repository-name "${ECR_REPOSITORY_NAME}" --image-ids "${DIGEST_IDS}"
fi

# Lambda にデプロイする
"${AWSCMD[@]}" lambda update-function-code --function-name "${LAMBDA_FUNCTION_NAME}" --image-uri "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:latest"

# Lambdaの更新が完了するまで待機する
"${AWSCMD[@]}" lambda wait function-updated --function-name "${LAMBDA_FUNCTION_NAME}"

# 新しい Lambda のバージョンを発行する
NEW_VERSION="$("${AWSCMD[@]}" lambda publish-version --function-name "${LAMBDA_FUNCTION_NAME}" --query 'Version' --output text)"
echo "New version published: $NEW_VERSION"

# 古いバージョンを取得する
VERSIONS="$("${AWSCMD[@]}" lambda list-versions-by-function --function-name "${LAMBDA_FUNCTION_NAME}" --query 'Versions[?Version!=`$LATEST`].Version' --output text)"

# バージョンを配列に変換
VERSIONS_ARRAY=(${VERSIONS})

# N 世代以上前の古い Lambda のバージョンを削除する
for ((i=0; i< "${#VERSIONS_ARRAY[@]}" - "${GEN}"; i++)); do
  "${AWSCMD[@]}" lambda delete-function --function-name "${LAMBDA_FUNCTION_NAME}" --qualifier "${VERSIONS_ARRAY[$i]}"
  echo "Deleted version: ${VERSIONS_ARRAY[$i]}"
done
