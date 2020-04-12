from flask import Blueprint, request

from ..api import BJUTLabAPI
from ..utilities import Log, get_form_data_by_key
from ..utilities.misc import login_required

AuthBP = Blueprint('Auth', __name__, url_prefix='/Auth')

api = BJUTLabAPI.get_instance()
logger = Log.get_logger(__name__)


@AuthBP.route('/register', methods=['POST'])
def register():
    form = request.form
    school_id = get_form_data_by_key(form, 'school_id')
    name = get_form_data_by_key(form, 'name')
    password = get_form_data_by_key(form, 'password')
    user_type = int(get_form_data_by_key(form, 'type'))
    return api.auth.register(school_id, name, password, user_type)


@AuthBP.route('/login', methods=['POST'])
def login():
    form = request.form
    school_id = get_form_data_by_key(form, 'school_id')
    password = get_form_data_by_key(form, 'password')
    user_type = int(get_form_data_by_key(form, 'type'))
    return api.auth.login(school_id, password, user_type)


@AuthBP.route('/change_password', methods=['POST'])
@login_required
def change_password():
    form = request.form
    old = get_form_data_by_key(form, 'old')
    new = get_form_data_by_key(form, 'new')
    return api.auth.change_password(old, new)


@AuthBP.route('/test_session', methods=['GET'])
@login_required
def test_session():
    return api.auth.test_session()