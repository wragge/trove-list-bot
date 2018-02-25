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
LISTS = os.environ.get('LISTS')
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

def choose_list():
  lists = [id.strip() for id in LISTS.split(',')]
  return random.choice(lists)

        
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

  
def truncate(message, length):
  if len(message) > length:
    message = '{}...'.format(message[:length])
  return message


def prepare_message(item, message_type):
    if message_type == 'new':
        message = 'New item added! {}: {}'
    elif message_type == 'random':
        message = 'Another interesting item! {}: {}'
    details = None
    if item['zone'] == 'work':
        try:
            details = '{} ({})'.format(truncate(item['title'], 200), item['issued'])
        except KeyError:
            details = '{}'.format(truncate(item['title'], 200))
    elif item['zone'] == 'article':
        date = arrow.get(item['date'], 'YYYY-MM-DD')
        details = '{}, \'{}\''.format(date.format('D MMM YYYY'), truncate(item['heading'], 200))
    if details:
        message = message.format(details, item['troveUrl'].replace('ndp/del', 'newspaper'))
    else:
        message = None
    return message


def update_ids(list, ids, new_ids):
    ids += new_ids
    if not os.path.exists('.data'):
        os.makedirs('.data')
    with open(os.path.join('.data', '{}-ids.json'.format(list)), 'wb') as ids_file:
        json.dump(ids, ids_file)


def get_ids(list):
    try:
        with open(os.path.join('.data', '{}-ids.json'.format(list)), 'rb') as ids_file:
            ids = json.load(ids_file)
    except IOError:
        print 'NOT FOUND'
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
    list = choose_list()
    if authorised(request):
        url = 'http://api.trove.nla.gov.au/list/{}?include=listItems&encoding=json&key={}'.format(list, API_KEY)
        print url
        response = requests.get(url)
        data = response.json()
        new_ids = []
        new_items = []
        ids = get_ids(list)
        for result in data['list'][0]['listItem']:
            for zone, item in result.items():
              if zone in ['article', 'work']:
                if item['id'] not in ids:
                    new_ids.append(item['id'])
                    if zone in ['article', 'work']:
                        item['zone'] = zone
                        new_items.append(item)
        update_ids(list, ids, new_ids)
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
    list = choose_list()
    if authorised(request):
        url = 'http://api.trove.nla.gov.au/list/{}?include=listItems&encoding=json&key={}'.format(list, API_KEY)
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
