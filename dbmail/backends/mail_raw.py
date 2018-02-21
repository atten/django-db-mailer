# -*- encoding: utf-8 -*-
from dbmail.backends.mail import Sender as SenderBase, SenderDebug as SenderDebugBase
from dbmail.utils import clean_html, premailer_transform


class Sender(SenderBase):

    def __init__(self, slug, recipient, *args, **kwargs):
        self._body = args[0].pop('body')
        self._subject = args[0].pop('subject')

        super(Sender, self).__init__(slug, recipient, *args, **kwargs)

    def _get_subject(self):
        return self._subject

    def _get_message(self):
        return premailer_transform(self._body)


class SenderDebug(SenderDebugBase, Sender):
    pass
