# -*- coding: utf-8 -*-
from __future__ import with_statement
import os
import re
import sys
sys.path.append('/home2/u5625/dartzspbru/www/cgi-bin/dartz-shop')
sys.path.append('/home2/u5625/dartzspbru/www/cgi-bin/dartz-shop/src')

import csv
from functools import wraps

from flask import Flask, request, Response, g, render_template, Request

from mail import send_mail
import dartzshop_settings as settings

DEBUG_MODE = settings.DEBUG_MODE


DIRNAME = os.path.dirname(__file__)
if not DIRNAME:
    DIRNAME = '/home/ki/my_projects/dartz_spb_ru__shop/dartz_shop/src'
DB_NAME = '%s/items.csv' % DIRNAME
LOCKFILE = '%s/items.lock' % DIRNAME


class CyrillicRequest(Request):
    url_charset = 'cp1251'

app = Flask(__name__)
if not DEBUG_MODE:
    app.request_class = CyrillicRequest

# Turn of on production
app.debug = DEBUG_MODE


#=============================
#           UTILS
#=============================
def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(unicode_csv_data,
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]


def utf_8_encoder(string_list):
    return [element.encode('utf-8') for element in string_list]


def _lock(lock_file):
    with open(lock_file, 'w'):
        pass


def _release_lock(lock_file):
    os.remove(lock_file)


#===============================
#       AUTHENTICATION
#===============================
def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'admin' and password == 'secret'


def authenticate():
    """Sends a 401 response that enables basic auth.
    Unfoturnately doesn't work when deployed via CGI.

    """
    return Response(
            'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


#=============================
#           MODELS
#=============================
class Item(object):

    def __init__(self, pk, name, image_url, description, count, price):
        self.pk = pk
        self.name = name
        self.image_url = image_url
        self.description = description
        self.count = int(count)
        self.price = int(price)

    def as_csv_row(self):
        return (self.name, self.image_url, self.description,
                str(self.count), self.price)

    def __repr__(self):
        return '<Item %r>' % self.name


class ItemStorage(object):
    """CSV storage for shop items.

    By default storage is readonly.

    """

    def __init__(self):
        pass

    def connect(self, readonly=True):
        if not readonly:
            _lock(LOCKFILE)

        self.items = []
        with open(DB_NAME, 'r') as f:
            reader = unicode_csv_reader(f.readlines())
        for pk, row in enumerate(reader):
            name, image_url, description, count, price = row
            self.items.append(
                Item(pk=pk, name=name, image_url=image_url,
                     description=description, count=count, price=price))

    def close(self, readonly=True):
        if not readonly:
            with open(DB_NAME, 'w') as f:
                writer = csv.writer(f)
                for item in self.items:
                    writer.writerow(utf_8_encoder(item.as_csv_row()))
            _release_lock(LOCKFILE)

    def all(self):
        return self.items

    def get_item(self, pk):
        return self.items[pk]


#============================
#          SIGNALS
#===========================
@app.before_request
def before_request():
    g.db = ItemStorage()
    g.db.connect()


@app.teardown_request
def teardown_request(exception):
    g.db.close()


#============================
#     VALIDATION TOOLS
#============================
def is_valid_email(value):
    if re.match('^[\.a-zA-Z0-9_-]+@[a-z0-9_-]+\.[a-z]+$', value):
        return True


def is_valid_phone(value):
    if re.match('^\+[0-9]+$', value):
        return True


def clean_field(key, value, validator, context, empty_msg, not_valid_msg):
    """Checks field value for validity and populates context.

    :key:            form field name
    :value:          form field value
    :validator:      function that accepts ``value`` as argument and returns
                         True if ``value`` is valid
    :context:        request context, will be passed to template
    :empty_msg:      error message to display in case form field value is empty
    :not_valid_msg:  error message in case form value is not valid

    """
    if not value:
        context['errors'].append(empty_msg)
    else:
        context[key] = value
        if not validator(value):
            context['errors'].append(not_valid_msg)


#============================
#          ROUTES
#============================
@app.route('/')
def index():
    items = g.db.all()
    context = {
        'items': items,
    }
    response = render_template('index.html', **context)
    if DEBUG_MODE:
        return response
    return response.encode('cp1251')


@app.route('/result/')
def result():
    context = {
        'order': [],
        'errors': [],
        'email': '',
        'phone': '',
        'delivery_info': ''
        }

    for key, value  in request.args.items():
        # Email
        if key == 'email':
            clean_field(key, value, is_valid_email, context,
                        u'Введите email',
                        u'Неправильный формат email адреса. Пример: '
                        u'hobbit@shire.com')
        # Phone
        if key == 'phone':
            clean_field(key, value, is_valid_phone, context,
                        u'Введите телефон',
                        u'Неправильный формат телефона. Пример: +78121234567')
        # Address
        if key == 'delivery_info':
            clean_field(key, value, lambda *args: True, context,
                        u'Заполните пожалуйста информацию о доставке',
                        u'')

        # Order
        if key.startswith('item_'):
            _, pk_str = key.split('_')
            pk = int(pk_str)
            item = g.db.get_item(pk)
            try:
                amount = int(value) if value else 0
            except ValueError:
                context['errors'].append(u'Количество заказываемых '
                                         u'ништяков должно быть цифрой '
                                         u'больше нуля и меньше бесконечности')
            else:
                # validation
                # now we just don't check the amount present
                if item.count <= 0 and amount:
                    context['errors'].append(u'%s нет в наличии' %
                                             item.name)
                elif amount > 0:
                    context['order'].append((item, amount))

    # If order is empty, show some message
    if not context['order'] and not context['delivery_info']:
        context['errors'] = (u'Ну закажите же что нибудь',)

    if context['delivery_info'] and not context['order']:
        context['errors'].append(u'Вы забыли указать количество '
                                 u'заказываемых ништяков')

    if not context['errors']:
        context['order_total'] = sum([item.price * amount
                                      for item, amount in context['order']])
        # Send email and render template
        if not DEBUG_MODE:
            subject = u'Dartz интернет магазин: Новый заказ'
            body = render_template('new_order.txt', **context)
            # Also send message to the customer
            recipients = settings.MANAGERS + (context['email'],)
            messages = [(recipient, subject, body) for recipient in recipients]
            email_error = send_mail(messages)
            if email_error:
                context['errors'].append(email_error)
        response = render_template('result.html', **context)
        if DEBUG_MODE:
            return response
        return response.encode('cp1251')

    # Render order form and show errors
    context['items'] = g.db.all()
    context['order'] = dict([(item.pk, amount)
                             for item, amount in context['order']])
    response = render_template('index.html', **context)
    if DEBUG_MODE:
        return response
    return response.encode('cp1251')


if __name__ == '__main__':
    app.run(debug=DEBUG_MODE)
