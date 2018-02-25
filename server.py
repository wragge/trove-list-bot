from flask import Flask, render_template, request, Response, jsonify
import requests
import tweepy
import os
import json
import random
import arrow
import time

app = Flask(__name__)

APP_KEY = os.environ.get('APP_KEY')
API_KEY = os.environ.get('TROVE_API_KEY')
LIST_ID = os.environ.get('LIST_ID')
CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')


def tweet(message, image=None):
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    if image:
        api.update_with_media(image, message)
    else:
        api.update_status(message)


def get_image(item):
    url = None
    image = None
    try:
        for identifier in item['identifier']:
            if identifier['linktype'] == 'thumbnail':
                url = identifier['value']
                break
        if url:
            thumbnail = 'thumbnail.jpg'
            request = requests.get(url, stream=True)
            if request.status_code == 200:
                with open(thumbnail, 'wb') as image:
                    for chunk in request:
                        image.write(chunk)
                image = 'thumbnail.jpg'
    except KeyError:
        pass
    return image


def prepare_message(item, message_type):
    if message_type == 'new':
        message = 'New item added! {}: {}'
    elif message_type == 'random':
        message = 'Another interesting item! {}: {}'
    details = None
    if item['zone'] == 'work':
        details = '{} ({})'.format(item['title'], item['issued'])
    elif item['zone'] == 'article':
        date = arrow.get(item['date'], 'YYYY-MM-DD')
        details = '{}, \'{}\''.format(date.format('D MMM YYYY'), item['heading'])
    if details:
        message = message.format(details, item['troveUrl'].replace('ndp/del', 'newspaper'))
    else:
        message = None
    return message


def update_ids(ids, new_ids):
    ids += new_ids
    if not os.path.exists('.data'):
        os.makedirs('.data')
    with open(os.path.join('.data', 'ids.json'), 'wb') as ids_file:
        json.dump(ids, ids_file)


def get_ids():
    try:
        with open(os.path.join('.data', 'ids.json'), 'rb') as ids_file:
            ids = json.load(ids_file)
    except IOError:
        ids = []
    return ids


def authorised(request):
    if request.args.get('key') == APP_KEY:
        return True
    else:
        return False


@app.route('/')
def home():
    return 'hello, I\'m ready to tweet'


@app.route('/new/')
def tweet_new():
    status = 'nothing new to tweet'
    if authorised(request):
        url = 'http://api.trove.nla.gov.au/list/{}?include=listItems&encoding=json&key={}'.format(LIST_ID, API_KEY)
        response = requests.get(url)
        data = response.json()
        new_ids = []
        new_items = []
        ids = get_ids()
        for result in data['list'][0]['listItem']:
            for zone, item in result.items():
                if item['id'] not in ids:
                    new_ids.append(item['id'])
                    if zone in ['article', 'work']:
                        item['zone'] = zone
                        new_items.append(item)
        update_ids(ids, new_ids)
        if new_items:
            new_item = random.choice(new_items)
            message = prepare_message(new_item, 'new')
            image = get_image(new_item)
            if message:
                print message
                tweet(message, image)
                status = 'ok, I tweeted something new'
    else:
        status = 'sorry, not authorised to tweet'
    return status


@app.route('/random/')
def tweet_random():
    status = 'nothing to tweet'
    if authorised(request):
        url = 'http://api.trove.nla.gov.au/list/{}?include=listItems&encoding=json&key={}'.format(LIST_ID, API_KEY)
        response = requests.get(url)
        data = response.json()
        items = []
        for result in data['list'][0]['listItem']:
            for zone, item in result.items():
                if zone in ['article', 'work']:
                    item['zone'] = zone
                    items.append(item)
        if items:
            item = random.choice(items)
            message = prepare_message(item, 'random')
            image = get_image(item)
            if message:
                print message
                tweet(message, image)
                status = 'ok, I tweeted something random'
    else:
        status = 'sorry, not authorised to tweet'
    return status
