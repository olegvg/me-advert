# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

import encodings.idna
import re
import datetime
from wtforms import widgets
from wtforms import TextField, PasswordField, BooleanField, IntegerField, \
    DateField, FloatField, SelectField, TextAreaField
from wtforms.validators import Required, Length, Email, EqualTo, ValidationError
from wtforms.ext.i18n.utils import get_translations
from flask_wtf import Form as BaseForm
from flask_wtf.file import FileField, FileAllowed
from sqlalchemy.orm.exc import NoResultFound
from commonlib.model import Person, Organization, Campaign


translations_cache = {}


class Form(BaseForm):
    def _get_translations(self):
        """
        Reintroduce i18n approach which is reduced in flask-wtforms but exist in original WTForms.
        """
        languages = ('ru_RU', 'ru')
        if languages not in translations_cache:
            translations_cache[languages] = get_translations(languages)
        return translations_cache[languages]


class FileInputWidget(widgets.Input):
    input_type = 'file'


class Select2_HiddenField(IntegerField):
    """
    There is a special WTForms Field type, which aims to work around strange bug in JS Select2 plugin. Bug connects
    with occasional duplication of field in POST request. We explicitly remove an empty one.
    """
    widget = widgets.HiddenInput()

    def process_formdata(self, valuelist):
        if valuelist:
            # try:
            #     valuelist.remove('')
            # except ValueError:
            #     pass
            try:
                self.data = valuelist[1]
            except IndexError:
                pass


class UniqueSqlRelation(object):
    """
    Check value uniqueness against specified field in SQL relation (table).
    """
    def __init__(self, relation, field_name):
        self.relation = relation
        self.field_name = field_name

    def __call__(self, *args, **kwargs):
        form, field = args[0:2]
        try:
            self.relation.query.filter(getattr(self.relation, self.field_name) == field.data).one()
        except NoResultFound:
            return
        raise ValidationError(u'Значение уже существует в базе данных.')


class NonIdnaURLOrEmpty(object):
    """
    Check whether domain is IDNA (includes international symbols). We have not supported IDNA domains yet.
    """
    def __call__(self, *args, **kwargs):
        form, field = args[0:2]
        if field.data == u'':
            return
        try:
            query = re.search('(https?://)(.*)', unicode(field.data)).group(2)
        except AttributeError:
            raise ValidationError(u'Разрешены только http:// и https:// ссылки.')
        try:
            if query != encodings.idna.ToASCII(query):
                raise ValidationError(u'Кириллические домены запрещены.')
        except UnicodeError:
            pass


class NotSoEarlyDate(object):
    def __call__(self, *args, **kwargs):
        form, field = args[0:2]
        if not isinstance(field.data, datetime.date):
            raise ValidationError(u'Должна быть указана дата.')
        if field.data < datetime.date(1900, 1, 1):
            raise ValidationError(u'Дата должна быть позднее 01.01.1900')


class LoginForm(Form):
    email = TextField(u"Email", validators=[Required(), Email(), Length(min=5, max=64)])
    plain_password = PasswordField(u"Пароль", validators=[Required(), Length(min=4, max=20)])
    remember_me = BooleanField(u"Запомни меня")


class RegistrationForm(Form):
    pass


class PersonForm(Form):
    first_name = TextField(u"Имя", validators=[Required(), Length(min=1, max=64)])
    surname = TextField(u"Фамилия")
    password = TextField(u"Пароль", validators=[Required(),
                                                Length(min=4, max=20),
                                                EqualTo('retry_password', message='Passwords must match')])
    retry_password = TextField(u"Ещё раз", validators=[Required(), Length(min=4, max=20)])
    organization_id = Select2_HiddenField(u"Рекламодатель")
    contractor_id = Select2_HiddenField(u"Подрядчик")
    role = SelectField(u'Роль', validators=[Required()], choices=[
        ('manager', u' супер-менеджер'),
        ('customer', u'клиент'),
        ('contractor', u'подрядчик')])
    is_blocked = BooleanField(u"Заблокирован?")


class NewPersonForm(PersonForm):
    email = TextField(u"Email", validators=[Required(), Email(), Length(min=5, max=64),
                      UniqueSqlRelation(Person, 'email')])


class EditPersonForm(PersonForm):
    email = TextField(u"Email", validators=[Required(), Email(), Length(min=5, max=64)])


class OrganizationForm(Form):
    full_name = TextField(u"Полное название")


class NewOrganizationForm(OrganizationForm):
    name = TextField(u"Название", validators=[Required(), Length(min=1, max=64),
                     UniqueSqlRelation(Organization, 'name')])


class EditOrganizationForm(OrganizationForm):
    name = TextField(u"Название", validators=[Required(), Length(min=1, max=64)])


class CampaignForm(Form):
    organization_id = Select2_HiddenField(u"Рекламодатель", validators=[Required()])
    start_date = DateField(u"Дата начала", validators=[Required(), NotSoEarlyDate()], format='%d.%m.%Y')
    due_date = DateField(u"Дата окончания", validators=[Required(), NotSoEarlyDate()], format='%d.%m.%Y')
    state = SelectField(u'Статус кампании', validators=[Required()], choices=[
        ('active', u'активная'),
        ('paused', u'приостановлена'),
        ('completed', u'закончена')])
    target_impressions = IntegerField(u'Целевые показы')
    sites = TextAreaField(u'Новые площадки')


class NewCampaignForm(CampaignForm):
    name = TextField(u"Название", validators=[Required(), Length(min=1, max=64),
                     UniqueSqlRelation(Campaign, 'name')])


class EditCampaignForm(CampaignForm):
    name = TextField(u"Название", validators=[Required(), Length(min=1, max=64)])
    is_archived = BooleanField(u"Архивировать?")


class CreativeForm(Form):
    creative_format_id = Select2_HiddenField(u"Формат", validators=[Required()])
    name = TextField(u"Название", validators=[Length(min=0, max=64)])
    geo_countries = Select2_HiddenField(u"Таргет на страны")
    geo_cities = Select2_HiddenField(u"Таргет на города")
    frequency = FloatField(u'Частота', validators=[Required()])
    target_impressions = IntegerField(u'Целевые показы', validators=[Required()])
    impression_target_url = TextField(u'Ссылка на zero-пиксел', validators=[NonIdnaURLOrEmpty()])
    click_target_url = TextField(u'Ссылка на клик', validators=[Required(), NonIdnaURLOrEmpty()])


class CounterForm(Form):
    contractor_id = Select2_HiddenField(u"Площадка", validators=[Required()])
    creative_file_swf = FileField(u"Креатив в формате Adobe Flash (SWF)",
                                  widget=FileInputWidget,
                                  validators=[FileAllowed(["swf"], u"Неправильный тип файла!")])
    creative_file_gif = FileField(u'Креатив в формате GIF, JPG',
                                  widget=FileInputWidget,
                                  validators=[FileAllowed(["gif", "jpg"], u"Неправильный тип файла!")])
    mu_ctr = TextField(u'Целевой CTR')
    sigma_ctr = TextField(u'Разброс CTR')
    description = TextField(u'Комментарий')
