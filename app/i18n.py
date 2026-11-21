"""Minimal interface translations: Russian (default) and Kazakh.

Messages are looked up by short keys. Missing Kazakh text falls back to Russian,
and a missing Russian key falls back to the key itself.
"""

from urllib.parse import urlsplit

from flask import Blueprint, has_request_context, redirect, request, session

DEFAULT_LANG = "ru"
LANGS = ("ru", "kk")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "site.name": "Волонтёрские часы",
        "nav.logout": "Выйти",
        "lang.switch": "Язык",
        "login.title": "Вход ученика",
        "login.email": "Школьный email",
        "login.submit": "Получить код",
        "login.not_on_list": "вас нет в списке, обратитесь к координатору",
        "code.page_title": "Код входа",
        "code.title": "Введите код",
        "code.sent": "Мы отправили 6-значный код на {email}. Код действует 10 минут.",
        "code.label": "Код",
        "code.submit": "Войти",
        "code.request_again": "Запросить код заново",
        "code.bad": "Неверный или просроченный код. Запросите новый код на странице входа.",
        "admin_login.title": "Вход администратора",
        "admin_login.bad": "Неверный логин или пароль.",
        "field.login": "Логин",
        "field.password": "Пароль",
        "cabinet.title": "Кабинет ученика",
        "cabinet.approved_total": "Подтверждённые часы:",
        "cabinet.add": "Добавить запись",
        "cabinet.empty": "Записей пока нет.",
        "comment.prefix": "Комментарий:",
        "table.student": "Ученик",
        "table.class": "Класс",
        "table.period": "Период",
        "table.description": "Описание",
        "table.hours": "Часы",
        "table.status": "Статус",
        "table.decision": "Решение",
        "status.pending": "на проверке",
        "status.approved": "подтверждено",
        "status.rejected": "отклонено",
        "action.edit": "Изменить",
        "action.delete": "Удалить",
        "action.save": "Сохранить",
        "action.cancel": "Отмена",
        "action.approve": "Подтвердить",
        "action.reject": "Отклонить",
        "action.filter": "Фильтровать",
        "action.reset": "Сбросить",
        "entry.new_title": "Новая запись",
        "entry.edit_title": "Изменить запись",
        "entry.start": "Начало периода",
        "entry.end": "Конец периода",
        "entry.description": "Описание работы (до 500 символов)",
        "admin.title": "Проверка записей",
        "admin.empty": "Записей нет.",
        "admin.comment_placeholder": "Комментарий",
        "flash.added": "Запись добавлена и отправлена на проверку.",
        "flash.updated": "Запись обновлена.",
        "flash.deleted": "Запись удалена.",
        "flash.decision_saved": "Решение сохранено.",
        "flash.error": "Ошибка",
        "flash.not_editable": "Эту запись нельзя изменить или удалить: изменять можно только записи на проверке.",
        "flash.not_editable_approved": "Подтверждённую запись нельзя изменить или удалить.",
        "err.bad_decision": "Выберите решение: подтвердить или отклонить.",
        "err.not_pending": "Запись уже проверена и не может быть изменена.",
        "val.date": "Укажите дату не позже сегодняшней.",
        "val.period": "Дата начала не может быть позже даты конца.",
        "val.description": "Опишите работу (не более {max} символов).",
        "val.hours": "Часы: не меньше 0.5, с шагом 0.5.",
        "mail.subject": "Код входа на сайт учёта волонтёрских часов",
        "mail.body": (
            "Ваш код для входа: {code}\n\n"
            "Код действует 10 минут. Если вы не запрашивали код, просто проигнорируйте это письмо.\n"
        ),
    },
    "kk": {
        "site.name": "Еріктілік сағаттары",
        "nav.logout": "Шығу",
        "lang.switch": "Тіл",
        "login.title": "Оқушы кіруі",
        "login.email": "Мектеп email",
        "login.submit": "Код алу",
        "login.not_on_list": "сіз тізімде жоқсыз, үйлестірушіге хабарласыңыз",
        "code.page_title": "Кіру коды",
        "code.title": "Кодты енгізіңіз",
        "code.sent": "Біз {email} поштасына 6 таңбалы код жібердік. Код 10 минут ішінде жарамды.",
        "code.label": "Код",
        "code.submit": "Кіру",
        "code.request_again": "Кодты қайта сұрау",
        "code.bad": "Код қате немесе мерзімі өткен. Кіру бетінде жаңа код сұраңыз.",
        "admin_login.title": "Әкімші кіруі",
        "admin_login.bad": "Логин немесе құпия сөз қате.",
        "field.login": "Логин",
        "field.password": "Құпия сөз",
        "cabinet.title": "Оқушы кабинеті",
        "cabinet.approved_total": "Расталған сағаттар:",
        "cabinet.add": "Жазба қосу",
        "cabinet.empty": "Әзірге жазбалар жоқ.",
        "comment.prefix": "Пікір:",
        "table.student": "Оқушы",
        "table.class": "Сынып",
        "table.period": "Кезең",
        "table.description": "Сипаттама",
        "table.hours": "Сағаттар",
        "table.status": "Мәртебе",
        "table.decision": "Шешім",
        "status.pending": "тексеруде",
        "status.approved": "расталды",
        "status.rejected": "қабылданбады",
        "action.edit": "Өзгерту",
        "action.delete": "Жою",
        "action.save": "Сақтау",
        "action.cancel": "Бас тарту",
        "action.approve": "Растау",
        "action.reject": "Қабылдамау",
        "action.filter": "Сүзу",
        "action.reset": "Тазалау",
        "entry.new_title": "Жаңа жазба",
        "entry.edit_title": "Жазбаны өзгерту",
        "entry.start": "Кезең басы",
        "entry.end": "Кезең соңы",
        "entry.description": "Жұмыс сипаттамасы (500 таңбаға дейін)",
        "admin.title": "Жазбаларды тексеру",
        "admin.empty": "Жазбалар жоқ.",
        "admin.comment_placeholder": "Пікір",
        "flash.added": "Жазба қосылып, тексеруге жіберілді.",
        "flash.updated": "Жазба жаңартылды.",
        "flash.deleted": "Жазба жойылды.",
        "flash.decision_saved": "Шешім сақталды.",
        "flash.error": "Қате",
        "flash.not_editable": "Бұл жазбаны өзгертуге немесе жоюға болмайды: тек тексеруде тұрған жазбаларды өзгертуге болады.",
        "flash.not_editable_approved": "Расталған жазбаны өзгертуге немесе жоюға болмайды.",
        "err.bad_decision": "Шешімді таңдаңыз: растау немесе қабылдамау.",
        "err.not_pending": "Жазба бұрын тексерілген, оны өзгерту мүмкін емес.",
        "val.date": "Бүгіннен кешіктірмей күнді көрсетіңіз.",
        "val.period": "Кезең басының күні кезең соңынан кейін бола алмайды.",
        "val.description": "Жұмысты сипаттаңыз ({max} таңбадан аспауы керек).",
        "val.hours": "Сағаттар: 0.5-тен кем емес, 0.5 қадамымен.",
        "mail.subject": "Еріктілік сағаттарын есепке алу сайтына кіру коды",
        "mail.body": (
            "Сіздің кіру кодыңыз: {code}\n\n"
            "Код 10 минут ішінде жарамды. Егер кодты сіз сұрамаған болсаңыз, бұл хатты елемеңіз.\n"
        ),
    },
}

bp = Blueprint("i18n", __name__)


def session_lang() -> str:
    """The language of the current session, or Russian outside a request."""
    if not has_request_context():
        return DEFAULT_LANG
    lang = session.get("lang")
    return lang if lang in LANGS else DEFAULT_LANG


def lookup(key: str, lang: str) -> str:
    """Text for `key` in `lang`, then in Russian, then the key itself. Needs no request context."""
    for code in (lang, DEFAULT_LANG):
        text = TRANSLATIONS.get(code, {}).get(key)
        if text is not None:
            return text
    return key


def translate(key: str, **params) -> str:
    """Translate `key` for the current session language. Returns the key outside a request context."""
    if not has_request_context():
        return key
    text = lookup(key, session_lang())
    return text.format(**params) if params else text


def _safe_return_path(referrer: str) -> str:
    """Turn a Referer into a local path. Anything off-site or unusual becomes "/"."""
    if not referrer or "\\" in referrer:
        return "/"
    parts = urlsplit(referrer)
    if parts.scheme or parts.netloc:
        # Absolute URL: only plain http(s) on the same host as this site.
        if parts.scheme not in ("http", "https") or parts.netloc != request.host:
            return "/"
    elif not referrer.startswith("/") or referrer.startswith("//"):
        return "/"
    target = parts.path or "/"
    # A path like "//host" would become a scheme-relative redirect to another site.
    if target.startswith("//") or "\\" in target:
        return "/"
    if parts.query:
        target += "?" + parts.query
    return target


@bp.get("/lang/<code>")
def set_lang(code: str):
    session["lang"] = code if code in LANGS else DEFAULT_LANG
    return redirect(_safe_return_path(request.referrer or ""))
