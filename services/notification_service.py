"""
Сервис уведомлений.
Отвечает за отправку уведомлений пользователям через различные каналы.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict

from models.user import User
from models.request import Request
from repositories.user_repository import UserRepository
from repositories.request_repository import RequestRepository
from config import Config


class NotificationService:
    """
    Сервис для отправки уведомлений.

    Поддерживает уведомления через:
    - Email
    - Telegram (опционально)
    - Логирование действий
    """

    def __init__(self):
        """Инициализация сервиса уведомлений"""
        self.user_repo = UserRepository()
        self.request_repo = RequestRepository()
        self.logger = logging.getLogger(__name__)

        # Настройки email (из конфига или переменных окружения)
        self.smtp_host = getattr(Config, 'SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = getattr(Config, 'SMTP_PORT', 587)
        self.smtp_user = getattr(Config, 'SMTP_USER', None)
        self.smtp_password = getattr(Config, 'SMTP_PASSWORD', None)
        self.from_email = getattr(Config, 'FROM_EMAIL', 'noreply@synergy.ru')

        # Включение/отключение каналов
        self.email_enabled = all([self.smtp_host, self.smtp_user, self.smtp_password])
        self.telegram_enabled = False  # По умолчанию отключено

    # ==================== УВЕДОМЛЕНИЯ О ЗАЯВКАХ ====================

    def notify_new_request(self, request_id: int, request_data: Request = None):
        """
        Уведомление о создании новой заявки.

        Args:
            request_id: ID заявки
            request_data: Объект заявки (опционально)
        """
        try:
            if not request_data:
                request_data = self.request_repo.find_by_id(request_id)

            if not request_data:
                return

            # Получаем информацию о заявителе
            requester = self.user_repo.find_by_id(request_data.requester_id)

            # Получаем список исполнителей для уведомления
            executors = self.user_repo.find_executors()

            subject = f"🆕 Новая заявка #{request_id}: {request_data.title}"
            message = self._format_new_request_message(request_data, requester)

            # Отправка уведомлений исполнителям
            for executor in executors:
                self.send_notification(executor, subject, message, 'new_request')

            # Логирование
            self.logger.info(f"Уведомления о новой заявке #{request_id} отправлены {len(executors)} исполнителям")

        except Exception as e:
            self.logger.error(f"Ошибка при отправке уведомлений о новой заявке #{request_id}: {e}")

    def notify_status_change(self, request_id: int, old_status_id: int,
                             new_status_id: int, comment: Optional[str] = None):
        """
        Уведомление об изменении статуса заявки.

        Args:
            request_id: ID заявки
            old_status_id: Старый статус
            new_status_id: Новый статус
            comment: Комментарий к изменению
        """
        try:
            request = self.request_repo.find_by_id(request_id)
            if not request:
                return

            # Получаем информацию о статусах
            from repositories.status_repository import StatusRepository
            status_repo = StatusRepository()
            old_status = status_repo.find_by_id(old_status_id)
            new_status = status_repo.find_by_id(new_status_id)

            # Получаем получателей
            recipients = self._get_status_change_recipients(request)

            subject = f"🔄 Статус заявки #{request_id} изменен"
            message = self._format_status_change_message(
                request, old_status, new_status, comment
            )

            # Отправка уведомлений
            for user in recipients:
                self.send_notification(user, subject, message, 'status_change')

            self.logger.info(f"Уведомления об изменении статуса заявки #{request_id} отправлены")

        except Exception as e:
            self.logger.error(f"Ошибка при отправке уведомлений об изменении статуса: {e}")

    def notify_assignment(self, request_id: int, assignee_id: int):
        """
        Уведомление о назначении заявки.

        Args:
            request_id: ID заявки
            assignee_id: ID исполнителя
        """
        try:
            request = self.request_repo.find_by_id(request_id)
            if not request:
                return

            assignee = self.user_repo.find_by_id(assignee_id)
            requester = self.user_repo.find_by_id(request.requester_id)

            if not assignee:
                return

            subject = f"👤 Вам назначена заявка #{request_id}"
            message = self._format_assignment_message(request, assignee, requester)

            # Уведомление исполнителя
            self.send_notification(assignee, subject, message, 'assignment')

            # Уведомление заявителя (опционально)
            if requester:
                subject_requester = f"👤 По заявке #{request_id} назначен исполнитель"
                message_requester = self._format_assignment_requester_message(request, assignee)
                self.send_notification(requester, subject_requester, message_requester, 'assignment_info')

            self.logger.info(f"Уведомление о назначении заявки #{request_id} отправлено {assignee.full_name}")

        except Exception as e:
            self.logger.error(f"Ошибка при отправке уведомления о назначении: {e}")

    def notify_new_comment(self, request_id: int, user_id: int, comment: str):
        """
        Уведомление о новом комментарии.

        Args:
            request_id: ID заявки
            user_id: ID автора комментария
            comment: Текст комментария
        """
        try:
            request = self.request_repo.find_by_id(request_id)
            if not request:
                return

            comment_author = self.user_repo.find_by_id(user_id)
            requester = self.user_repo.find_by_id(request.requester_id)
            assignee = self.user_repo.find_by_id(request.assignee_id) if request.assignee_id else None

            subject = f"💬 Новый комментарий к заявке #{request_id}"
            message = self._format_comment_message(request, comment_author, comment)

            # Определяем получателей (все участники, кроме автора)
            recipients = []
            if requester and requester.id != user_id:
                recipients.append(requester)
            if assignee and assignee.id != user_id:
                recipients.append(assignee)

            # Отправка уведомлений
            for user in recipients:
                self.send_notification(user, subject, message, 'new_comment')

            self.logger.info(f"Уведомления о новом комментарии к заявке #{request_id} отправлены")

        except Exception as e:
            self.logger.error(f"Ошибка при отправке уведомления о комментарии: {e}")

    def notify_sla_breach(self, request_id: int, sla_info: Dict[str, any]):
        """
        Уведомление о нарушении SLA.

        Args:
            request_id: ID заявки
            sla_info: Информация о SLA
        """
        try:
            request = self.request_repo.find_by_id(request_id)
            if not request:
                return

            assignee = self.user_repo.find_by_id(request.assignee_id) if request.assignee_id else None
            requester = self.user_repo.find_by_id(request.requester_id)

            subject = f"⚠ КРИТИЧНО: Нарушение SLA по заявке #{request_id}"
            message = self._format_sla_breach_message(request, sla_info)

            # Уведомление исполнителя
            if assignee:
                self.send_notification(assignee, subject, message, 'sla_breach', priority='high')

            # Уведомление заявителя
            if requester:
                self.send_notification(requester, subject, message, 'sla_breach_info')

            # Уведомление администраторов
            admins = self.user_repo.find_admins()
            for admin in admins:
                self.send_notification(admin, subject, message, 'sla_breach_admin', priority='high')

            self.logger.warning(f"Уведомления о нарушении SLA по заявке #{request_id} отправлены")

        except Exception as e:
            self.logger.error(f"Ошибка при отправке уведомления о нарушении SLA: {e}")

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def send_notification(self, user: User, subject: str, message: str,
                          notification_type: str = 'general', priority: str = 'normal'):
        """
        Отправка уведомления пользователю через доступные каналы.

        Args:
            user: Пользователь
            subject: Тема уведомления
            message: Текст уведомления
            notification_type: Тип уведомления
            priority: Приоритет ('normal', 'high')
        """
        # Email уведомление
        if self.email_enabled and user.email:
            self._send_email(user.email, subject, message, priority)

        # Telegram уведомление (если настроено и есть telegram_id)
        if self.telegram_enabled and user.telegram_id:
            self._send_telegram(user.telegram_id, message, priority)

        # Логирование для отладки
        self.logger.debug(f"Уведомление '{subject}' для {user.full_name} ({notification_type})")

    def _send_email(self, to_email: str, subject: str, message: str, priority: str = 'normal'):
        """
        Отправка email уведомления.
        """
        if not self.email_enabled:
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Добавление заголовков приоритета
            if priority == 'high':
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'

            msg.attach(MIMEText(message, 'plain', 'utf-8'))

            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()

        except Exception as e:
            self.logger.error(f"Ошибка отправки email на {to_email}: {e}")

    def _send_telegram(self, chat_id: str, message: str, priority: str = 'normal'):
        """
        Отправка Telegram уведомления.
        Заглушка - требует настройки Telegram Bot API.
        """
        # TODO: Реализовать отправку через Telegram Bot API
        pass

    def log_user_action(self, user_id: int, action: str, details: Optional[Dict] = None):
        """
        Логирование действия пользователя.

        Args:
            user_id: ID пользователя
            action: Действие
            details: Детали действия
        """
        user = self.user_repo.find_by_id(user_id)
        user_name = user.full_name if user else f"User#{user_id}"

        log_message = f"USER ACTION [{user_name}]: {action}"
        if details:
            log_message += f" - {details}"

        self.logger.info(log_message)

    def _get_status_change_recipients(self, request: Request) -> List[User]:
        """
        Получение списка получателей уведомления об изменении статуса.
        """
        recipients = []

        # Заявитель
        requester = self.user_repo.find_by_id(request.requester_id)
        if requester:
            recipients.append(requester)

        # Исполнитель
        if request.assignee_id:
            assignee = self.user_repo.find_by_id(request.assignee_id)
            if assignee:
                recipients.append(assignee)

        return recipients

    # ==================== ФОРМАТИРОВАНИЕ СООБЩЕНИЙ ====================

    def _format_new_request_message(self, request: Request, requester: User) -> str:
        """Форматирование сообщения о новой заявке"""
        return f"""
Новая заявка #{request.id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Тема: {request.title}
Описание: {request.description or 'Нет описания'}
Категория: {request.category_id}
Приоритет: {request.get_priority_display()}

Заявитель: {requester.full_name if requester else 'Неизвестно'}
Отдел: {requester.department if requester else '-'}
Email: {requester.email if requester else '-'}

Дата создания: {request.created_at.strftime('%d.%m.%Y %H:%M') if request.created_at else '-'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Для работы с заявкой войдите в систему.
"""

    def _format_status_change_message(self, request: Request, old_status,
                                      new_status, comment: Optional[str]) -> str:
        """Форматирование сообщения об изменении статуса"""
        return f"""
Изменение статуса заявки #{request.id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Тема: {request.title}

Статус изменен:
{old_status.name if old_status else 'Неизвестно'} → {new_status.name if new_status else 'Неизвестно'}

{f'Комментарий: {comment}' if comment else ''}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _format_assignment_message(self, request: Request, assignee: User,
                                   requester: User) -> str:
        """Форматирование сообщения о назначении заявки"""
        return f"""
Вам назначена заявка #{request.id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Тема: {request.title}
Описание: {request.description or 'Нет описания'}
Приоритет: {request.get_priority_display()}

Заявитель: {requester.full_name if requester else 'Неизвестно'}
Отдел: {requester.department if requester else '-'}

Дата создания: {request.created_at.strftime('%d.%m.%Y %H:%M') if request.created_at else '-'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Пожалуйста, приступите к работе над заявкой.
"""

    def _format_assignment_requester_message(self, request: Request,
                                             assignee: User) -> str:
        """Форматирование сообщения заявителю о назначении исполнителя"""
        return f"""
По вашей заявке #{request.id} назначен исполнитель

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Тема: {request.title}

Исполнитель: {assignee.full_name}
Отдел: {assignee.department}

Статус заявки: В работе
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _format_comment_message(self, request: Request, author: User,
                                comment: str) -> str:
        """Форматирование сообщения о новом комментарии"""
        return f"""
Новый комментарий к заявке #{request.id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Тема: {request.title}

Автор: {author.full_name if author else 'Неизвестно'}
Комментарий:
{comment}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _format_sla_breach_message(self, request: Request, sla_info: Dict[str, any]) -> str:
        """Форматирование сообщения о нарушении SLA"""
        return f"""
⚠ ВНИМАНИЕ! НАРУШЕНИЕ SLA ⚠

Заявка #{request.id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Тема: {request.title}
Приоритет: {request.get_priority_display()}

Лимит SLA: {sla_info['sla_limit']} ч.
Прошло времени: {sla_info['elapsed_hours']} ч.
Превышение: {sla_info['overrun_hours']} ч.

Дата создания: {request.created_at.strftime('%d.%m.%Y %H:%M') if request.created_at else '-'}
Крайний срок: {sla_info['due_date'].strftime('%d.%m.%Y %H:%M') if sla_info['due_date'] else '-'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ТРЕБУЕТСЯ НЕМЕДЛЕННОЕ ВМЕШАТЕЛЬСТВО!
"""