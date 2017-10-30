# -*- encoding: utf-8 -*-

from django.utils.html import strip_tags

from dbmail import import_module


def premailer_transform(text):
    try:
        from premailer import transform

        return transform(text)
    except Exception as err:
        print(err)
        return text


def get_ip(request):
    try:
        from ipware.ip import get_real_ip

        ip = get_real_ip(request)
        if ip is not None:
            return ip.strip()
    except ImportError:
        pass

    return request.META['REMOTE_ADDR'].split(',')[-1].strip()


def html2text(message):
    try:
        from html2text import html2text

        return html2text(message)
    except ImportError:
        return strip_tags(message)


def clean_html(message):
    from dbmail.defaults import MESSAGE_HTML2TEXT

    module = import_module(MESSAGE_HTML2TEXT)
    return module.html2text(message)


def dotval(obj, dottedpath, default=None):
    """
    Возвращает значение аттрибута объекта или элемента словаря по его пути в формате 'a.b.c'
    Примеры:
    obj = {'item1': {'nested': 123, 'other': 456}}
    >>> dotval(obj, 'item1.nested')
    123
    >>> dotval(obj, 'item2')
    None
    """
    val = obj
    sentinel = object()
    for attr in dottedpath.split('.'):
        if isinstance(val, dict):
            val = val.get(attr, sentinel)
            if val is sentinel:
                return default
        elif not hasattr(val, attr):
            return default
        else:
            val = getattr(val, attr, sentinel)
            if val is sentinel:
                return default
            if callable(val):
                val = val()
    return val
