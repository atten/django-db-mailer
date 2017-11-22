# -*- coding: utf-8 -*-

from django.core import urlresolvers
from django.contrib import admin
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.text import Truncator


truncate_words = lambda value, length: Truncator(value).words(length, html=True)


def uni_tr_10(field_name):
    """
    Возвращает фунцию, которая преобразует название поля Django модели в строку и обрезает её до 10 слов.
    Для функции устанавливается пара атрибутов - short_description и admin_order_field (используются Django Admin).
    :param field_name: str, название поля модели
    :return: callable with some attributes.
    """
    def func(obj):
        return truncate_words(str(getattr(obj, field_name)), 10)

    func.short_description = field_name
    func.admin_order_field = field_name

    return func


def uni_fk_tr_10(field_name, order_field=None):
    """
    Возвращает фунцию, которая преобразует название ForeignKey поля Django модели
    в html ссылку и обрезает её до 10 слов.
    У функции устанавливается пара атрибутов -
    short_description, admin_order_field и allow_tags (используются Django Admin).
    :param field_name: str, название поля модели
    :param order_field: str, если True - устанавливается атрибут admin_order_field
    :return: callable with some attributes.
    """
    fnparts = field_name.split('__')

    def func(obj):
        f = getattr(obj, fnparts[0])
        for part in fnparts[1:]:
            f = getattr(f, part)
        name = escape(truncate_words(force_text(f), 10))

        try:
            url_name = 'admin:%s_%s_change' % (f._meta.app_label, f._meta.model_name)
            url = urlresolvers.reverse(url_name, args=(f.pk,))
            return '<a href="%s">%s</a>' % (url, name)
        except Exception:
            return name

    func.allow_tags = True
    func.short_description = fnparts[-1]

    if order_field is not False:
        func.admin_order_field = order_field or field_name

    return func


def admin_field(field_name, field_title=None, order_field=None):
    """
    Возвращает фунцию, которая преобразует название поля или функции Django модели в её значение.
    :param field_name: str, название поля модели
    :param field_title: str, заголовок для колонки значений в админке
    :param order_field: str, название поля, по которому будет сортироваться колонка
    :return: callable with some attributes.
    """
    fnparts = field_name.split('__')

    def func(obj):
        f = getattr(obj, fnparts[0])
        for part in fnparts[1:]:
            f = getattr(f, part)
        if callable(f):
            f = f()
        return force_text(f)

    func.short_description = field_title or fnparts[-1]

    if order_field is not False:
        func.admin_order_field = order_field or field_name

    return func


def admin_bool_icon(field_name):
    """
    Возвращает фунцию, которая преобразует название поля Django модели в html-код с картинкой (да/нет)
    для наглядного отображения булевых значений.
    :param field_name: str, название поля модели
    :return: callable with some attributes.
    """
    fnparts = field_name.split('__')

    def func(obj):
        f = getattr(obj, fnparts[0])
        for part in fnparts[1:]:
            f = getattr(f, part)

        img_name = 'yes' if bool(f) else 'no'
        return '<img src="/static/admin/img/icon-{0}.gif" alt="{0}">  '.format(img_name)

    func.allow_tags = True
    func.short_description = fnparts[-1]
    return func


class SortedRelatedFieldListFilter(admin.RelatedFieldListFilter):
    def __init__(self, *args, **kwargs):
        """
        сортируем choices по алфавиту, если в дефолтном менеджере модели это по каким-то причинам нельзя сделать
        """
        super(SortedRelatedFieldListFilter, self).__init__(*args, **kwargs)
        self.lookup_choices = sorted(self.lookup_choices, key=lambda x: x[1])
