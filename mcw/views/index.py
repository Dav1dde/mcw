from flask import (
    Blueprint, request, session, g, render_template,
    url_for, redirect, abort, jsonify, current_app
)

index = Blueprint('index', __name__)


MENUS = [
    ('overview', 'Overview', 'fa fa-line-chart', 'overview.html'),
    ('console', 'Console', 'fa fa-terminal', 'console.html')
]

@index.route('/')
def site_index():
    if not session.get('loggedin', False):
        return render_template('login.html')

    return render_template('backend.html', menus=MENUS, default='overview')


@index.route('/login', methods=['POST'])
def login():
    pw = request.form.get('password', None)

    if pw == current_app.config.password:
        session['loggedin'] = True
        return jsonify({'success': True})

    return jsonify({
        'success': False, 'error': 'Login Failed: Invalid password'
    })


@index.route('/logout')
def logout():
    if session.get('loggedin', False):
        session['loggedin'] = False
        return redirect(url_for('index.site_index'))

    return abort(401)




