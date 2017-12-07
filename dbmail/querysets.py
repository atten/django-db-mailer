import re

from django.db.models import QuerySet


class MailCredentialQuerySet(QuerySet):
     def get_by_from_email(self, from_email):
         """
         tries to fetch aproptiate credentials for current sender
         :param from_email: строка вида aaa@mail.ru или John <aaa@mail.ru>
         :return: MailCredential instance or None
         """

         usernames = [
             [from_email],
             re.findall(r'<(\S+)>', from_email),  # ищет то, что внутри < >
             re.findall(r'\S+\@(\S+)', from_email),  # ищет то, что после @
             re.findall(r'\S+\@(\S+)>', from_email),  # ищет то, что между @ и >
         ]

         usernames = filter(lambda x: x, usernames)
         usernames = map(lambda x: x[0], usernames)

         for username in usernames:
             try:
                return self.get(username__contains=username)
             except self.model.DoesNotExist:
                 pass
