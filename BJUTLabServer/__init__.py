def create_app():
    from flask import Flask, render_template
    from datetime import datetime
    from pathlib import Path
    from .utilities.SqlHandler import SQLHandler
    from .utilities.Crypto import Crypto

    STARTUP_TIME = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    app = Flask('BJUTLabServer')
    ConfigPath = Path(app.root_path).resolve().parent.joinpath('config.py')
    app.config.from_pyfile(ConfigPath)
    DB_CONFIG = {
        'host': app.config['DB_HOST'],
        'user': app.config['DB_USER'],
        'useDB': app.config['DB_NAME'],
        'password': app.config['DB_PASSWORD'],
        'charset': app.config['DB_CHARSET']
    }
    SECRET_KEYS = {
        'aes': app.config['AES_KEY'],
        'rsa': app.config['RSA_PRI_KEY'],
        'nonce': app.config['AES_NONCE']
    }
    SQLHandler.load_config(DB_CONFIG)
    Crypto.load_config(SECRET_KEYS)

    from flask_cors import CORS
    from .exception import ParameterException, WerkzeugException
    from .utilities import make_error_response, jsonify
    from .blueprints import BPList
    from .utilities.Log import Log

    VERSION_CODE = '0.1.1'
    for bp in BPList:
        app.register_blueprint(bp)
    CORS(app, supports_credentials=True)
    rules = app.url_map.iter_rules()

    APIs = {}
    for rule in rules:
        pair = str(rule).split('/', 2)
        if pair[1] in APIs:
            if pair[2] not in APIs[pair[1]]:
                APIs[pair[1]].append(pair[2])
        else:
            APIs[pair[1]] = [pair[2]]

    @app.route('/')
    def hi():
        return render_template('index.html', time=STARTUP_TIME, APIs=APIs, ver=VERSION_CODE)

    @app.errorhandler(ParameterException)
    def handle_parameter_exception(e):
        return make_error_response(e)

    @app.errorhandler(WerkzeugException.NotFound)
    def handle_not_found(e):
        return make_error_response(e)

    @app.errorhandler(WerkzeugException.Unauthorized)
    def handle_not_found(e):
        return make_error_response(e)

    return app
