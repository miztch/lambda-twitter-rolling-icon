import logging
import json
import os
import re
import boto3

import tweepy
from tweepy.errors import TweepyException

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource('s3')
s3client = boto3.Session().client('s3')


def auth():
    '''
    Twitter APIのOAuth認証を行います。
    '''

    CK = os.environ['TWITTER_CONSUMER_KEY']
    CS = os.environ['TWITTER_CONSUMER_SECRET']
    AT = os.environ['TWITTER_ACCESS_TOKEN']
    AS = os.environ['TWITTER_ACCESS_SECRET']

    auth = tweepy.OAuthHandler(CK, CS)
    auth.set_access_token(AT, AS)

    api = tweepy.API(auth)

    return api


def list_object_keys(bucket_name):
    '''
    指定したS3バケット内のオブジェクトをリストし、ソートして返します。

    Parameters
    ----------
    bucket_name : str
        アイコンに設定する画像が保存されているS3バケット名
    '''
    keys = sorted([key['Key'] for key in s3client.list_objects(
        Bucket=bucket_name)['Contents']])
    return keys


def get_icon_indicator(bucket_name):
    '''
    現在のプロフィールアイコン画像を示すS3オブジェクト名を返します。

    Parameters
    ----------
    bucket_name : str
        アイコンに設定する画像が保存されているS3バケット名
    '''
    # S3からファイル名のリストを取得し、現在のアイコン画像を示す空ファイルを取得する
    # 画像ファイル名: YYYYMMDD-(TwitterID).(拡張子) の形式
    # 空ファイル名: 画像ファイル名の頭に"0_"を付与することで、昇順で0番目にする
    # keys[0]が今のアイコン画像に設定されたファイル名
    # ex. "20200102-awesome-irrustlator.jpg"
    # TODO: ファイルが何も無ければIndexErrorになるので、なにもせず終了させたい
    keys = list_object_keys(bucket_name)
    icon_indicator = keys[0]

    return icon_indicator


def get_icon_image(bucket_name):
    '''
    新しいプロフィールアイコン画像のファイル名を返します。

    Parameters
    ----------
    bucket_name : str
        アイコンに設定する画像が保存されているS3バケット名
    '''
    # 現在のアイコン画像のKeyを取得する
    keys = list_object_keys(bucket_name)
    tmp_icon = get_icon_indicator(bucket_name).split('0_')[1]

    # ファイル名順に並んだ、次のアイコンを選ぶことにする
    # 現在のアイコンが最後の画像ファイルの場合、最初の画像ファイルを選ぶ
    # 現在アイコンに設定されている画像のファイル名が変わった場合、
    # keys.index() がValueErrorとなるため、最後の画像ファイルを選ぶ
    try:
        if keys.index(tmp_icon)+1 == len(keys):
            new_icon = keys[1]  # keys[0]は現在のアイコン画像を示す空ファイル
        else:
            new_icon = keys[keys.index(tmp_icon)+1]
    except ValueError:
        new_icon = keys[-1]
        logger.error(e)

    return new_icon


def set_icon_image(api, bucket_name, new_icon):
    '''
    新しいプロフィールアイコンを設定します。

    Parameters
    ----------
    api : <class 'tweepy.api.API'>
        Twitter APIのwrapper
    bucket_name : str
        アイコンに設定する画像が保存されているS3バケット名
    new_icon : str
        新しくアイコンに設定する画像のファイル名
    '''

    filename = new_icon
    file_path = '/tmp/' + filename
    bucket = s3.Bucket(bucket_name)

    bucket.download_file(filename, file_path)

    author = filename.split('-')[1].split('.')[0]

    try:
        api.update_profile_image(file_path)
        # 現在設定されているアイコンを示すオブジェクトを置き換える
        # delete -> copy from new_icon
        s3client.delete_object(
            Bucket=bucket_name, Key=get_icon_indicator(bucket_name))
        s3client.copy_object(Bucket=bucket_name, Key='0_' + new_icon,
                             CopySource={'Bucket': bucket_name, 'Key': new_icon})
    except TweepyException:
        logger.error(
            'There was a problem when invoking Twitter API', exc_info=True)

    return author


def update_bio(api, author):
    '''
    新しいプロフィール文字列を設定します。

    Parameters
    ----------
    api : <class 'tweepy.api.API'>
        Twitter APIのwrapper
    author : str
        新しいプロフィール文字列に指定するアイコン画像作者のTwitter ID
    '''

    try:
        user = api.verify_credentials()
        bio = user.description
    except TweepyException:
        logger.error(
            'There was a problem when invoking Twitter API', exc_info=True)

    logger.info('former bio: {}'.format(bio))

    # プロフィール文字列のアイコン作者Twitter IDを置換する(画像ファイル名から取る)
    # アイコン画像のクレジット表記は 'i: @xxx' という形式になっている前提
    icon_credit_pattern = 'i: @' + '[a-zA-Z0-9_]{1,15}'
    tmp_icon_credit = re.findall(icon_credit_pattern, bio)[0]

    # クレジット表記の前後を分割しておいて、後で結合する
    bio_prefix = bio.split(tmp_icon_credit)[0]  # may end with space
    bio_suffix = bio.split(tmp_icon_credit)[1]  # may start with space

    new_icon_author = 'i: @{}'.format(author)
    new_bio = bio_prefix + new_icon_author + bio_suffix

    # プロフィール文字列を更新する
    try:
        execute = api.update_profile(description=new_bio)
        logger.info(
            'successfully updated description. new_bio: {}'.format(new_bio))
        return new_bio

    except TweepyException as e:
        logger.error(
            'There was a problem when invoking Twitter API', exc_info=True)


def lambda_handler(event, context):
    logger.info('event: ' + json.dumps(event))

    api = auth()

    bucket_name = os.environ['BUCKET_NAME']

    new_icon = get_icon_image(bucket_name)
    author = set_icon_image(api, bucket_name, new_icon)
    new_bio = update_bio(api, author)

    response = {
        'new_icon': new_icon,
        'new_author': author,
        'new_bio': new_bio
    }

    logger.info(response)

    return response
