# -*- encoding: utf-8 -*-

import pprint

from django.db.models.fields.related import ManyToManyField, ForeignKey
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.contrib.sites.models import Site
from django.template import Template, Context
from django.core.mail import get_connection
from django.utils.html import strip_tags
from django.utils import translation
from django.core.cache import cache
from django.conf import settings

from dbmail.models import MailTemplate, MailLog, MailGroup
from dbmail.defaults import SHOW_CONTEXT


class SendMail(object):
    def __init__(self, slug, recipient, *args, **kwargs):
        self._slug = slug

        self._recipient_list = self.__get_recipient_list(recipient)
        self._cc = self.__email_to_list(kwargs.pop('cc', None))
        self._bcc = self.__email_to_list(kwargs.pop('bcc', None))
        self._user = kwargs.pop('user', None)
        self._language = kwargs.pop('language', None)

        self._template = self.__get_template()
        self._context = self.__get_context(args)

        self._subject = self.__get_subject()
        self._message = self.__get_message()
        self._files = kwargs.pop('files', [])
        self._kwargs = kwargs
        self._num = 1
        self._err_msg = None

        self._kwargs.pop('retry', None)
        self._kwargs.pop('max_retries', None)
        self._kwargs.pop('retry_delay', None)

        self._from_email = self.__get_from_email()
        self.__update_bcc_from_template_settings()

    def __get_connection(self):
        auth_credentials = cache.get(self._from_email, version=1)
        if auth_credentials:
            return self._kwargs.pop('connection', None) or get_connection(
                **auth_credentials)
        return self._kwargs.pop('connection', None)

    def __get_template(self):
        return MailTemplate.get_template(slug=self._slug)

    def __get_context(self, context_list):
        data = self.__model_to_dict(Site.objects.get_current())

        for context in context_list:
            if isinstance(context, dict):
                data.update(context)
            else:
                data.update(self.__model_to_dict(context))
                data.update({context._meta.module_name: context})

        if settings.DEBUG and SHOW_CONTEXT:
            pprint.pprint(data)
        return data

    def __get_str_by_language(self, field):
        template = getattr(self._template, field)
        if self._language is not None:
            field = '%s_%s' % (field, self._language)
            if hasattr(self._template, field):
                if getattr(self._template, field):
                    template = getattr(self._template, field)
        return template

    def __get_subject(self):
        return self.__render_template(
            self.__get_str_by_language('subject'), self._context)

    def __get_message(self):
        return self.__render_template(
            self.__get_str_by_language('message'), self._context)

    def __attach_files(self, mail):
        for file_object in self._template.files.all():
            mail.attach_file(file_object.filename.path)

        for filename in self._files:
            mail.attach_file(filename)

    def __send_html_message(self):
        msg = EmailMultiAlternatives(
            self._subject, strip_tags(self._message), cc=self._cc,
            from_email=self._from_email, to=self._recipient_list,
            bcc=self._bcc, connection=self.__get_connection(), **self._kwargs
        )
        msg.attach_alternative(self._message, "text/html")
        self.__attach_files(msg)
        msg.send()

    def __send_plain_message(self):
        msg = EmailMessage(
            self._subject, self._message, from_email=self._from_email,
            to=self._recipient_list, cc=self._cc, bcc=self._bcc,
            connection=self.__get_connection(), **self._kwargs
        )
        self.__attach_files(msg)
        msg.send()

    def __get_recipient_list(self, recipient):
        if not isinstance(recipient, list) and '@' not in recipient:
            return self.__group_emails(recipient)
        return self.__email_to_list(recipient)

    def __update_bcc_from_template_settings(self):
        template_bcc = cache.get(self._slug, version=2)
        if template_bcc is not None:
            if self._bcc:
                self._bcc.extend(template_bcc)
            else:
                self._bcc = template_bcc

    def __get_from_email(self):
        if self._kwargs.get('from_email'):
            return self._kwargs['from_email']
        elif not self._template.from_email:
            return settings.DEFAULT_FROM_EMAIL
        return self._template.from_email.get_mail_from

    @staticmethod
    def __group_emails(recipient):
        email_list = []
        for slug in recipient.split(','):
            for obj in MailGroup.get_emails(slug):
                email_list.append(obj.email.strip())
        return email_list

    @staticmethod
    def __email_to_list(recipient):
        if recipient is None:
            return None
        elif not isinstance(recipient, list):
            recipient = [d.strip() for d in recipient.split(',') if d.strip()]
        return recipient

    def __render_template(self, template, context):
        translation.activate(self._language or settings.LANGUAGE_CODE)
        return Template(template).render(Context(context))

    @staticmethod
    def __model_to_dict(instance):
        opts, data = getattr(instance, '_meta'), dict()
        for f in opts.fields + opts.many_to_many:
            if isinstance(f, ManyToManyField):
                if instance.pk is None:
                    data[f.name] = []
                else:
                    data[f.name] = list(f.value_from_object(
                        instance).values_list('pk', flat=True))
            elif isinstance(f, ForeignKey):
                if getattr(instance, f.name):
                    data[f.name] = getattr(instance, f.name).__unicode__()
            else:
                data[f.name] = f.value_from_object(instance)
        return data

    def __send(self):
        if self._template.is_active:
            if self._template.is_html:
                return self.__send_html_message()
            return self.__send_plain_message()

    def __store_log(self, is_sent):
        MailLog.store(
            self._recipient_list, self._cc, self._bcc,
            is_sent, self._template, self._user,
            self._num, self._err_msg
        )

    def send(self):
        try:
            self.__send()
            self.__store_log(True)
        except Exception:
            self.__store_log(False)
            raise
