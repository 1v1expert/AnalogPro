from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand

from app.models import MainLog
from catalog.internal.messages import _get_connection


class Command(BaseCommand):
    help = 'Generate a stat info'

    def handle(self, *args, **options):

        dt_now = datetime.now().date() - timedelta(days=1)
        
        logs = MainLog.objects.filter(action_time__date=dt_now, raw__request__raw_request__method__in=['GET', 'POST'])
        authorized_users_logs = logs.exclude(user=None)
        
        body = f'Today({datetime.now()}) - {logs.count()} events:\n' \
               f'authorized users - {authorized_users_logs.count()}, ' \
               f'unauthorized users - {logs.count() - authorized_users_logs.count()}\n\n'
        
        if authorized_users_logs.count():
            for log in logs.order_by('user').distinct('user').values('user'):

                if log['user'] is None:
                    continue

                user_obj = User.objects.get(pk=log['user'])
                body += f'User ' \
                        f'{user_obj.username}, ' \
                        f'{user_obj.email} - ' \
                        f'{logs.filter(user=user_obj, raw__request__raw_request__method="GET", raw__request__raw_request__path_info="/").count()}\n'
                body += f'search analog - ' \
                        f'{logs.filter(user=user_obj, raw__request__raw_request__method="POST", raw__request__raw_request__path_info="/api/search/").count()},' \
                        f' input article - ' \
                        f'{logs.filter(user=user_obj, raw__request__raw_request__method="GET", raw__request__raw_request__path_info="/api/search/").count()}' \
                        f'\n========\n'

        msg = EmailMessage(
            subject='ACTIVITY',
            body=body,
            from_email='info@analogpro.ru',
            to=['1v1expert@gmail.com', 'mojaev-a@yandex.ru'],
            connection=_get_connection())

        response = msg.send()

# logs.order_by('user').distinct('user').filter(raw__request__raw_request__path_info='/').values('user__username', 'user__email', 'pk').annotate(c_houme=Count('pk'))