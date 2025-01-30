import uuid
import requests
from flask import Flask, render_template, session, request, redirect, url_for, Response
from flask_session import Session  # https://pythonhosted.org/Flask-Session
import msal
import yaml
import logging
import msmcharters
import msmevents
import msmsquareweb
import msmmembership

# Load configuration
try:
    with open("config-passport.yaml", 'r') as stream:
        try:
            passportConfig=yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
except IOError:
    print("Could not read config-passport.yaml file")

app = Flask(__name__)
# Translate yaml config to flask config for session type
app.config['SESSION_TYPE'] = passportConfig['sessionType']
app.config['SERVER_NAME'] = passportConfig['serverName']
app.config['PREFERRED_URL_SCHEME'] = 'https'

Session(app)

# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/
from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

logging.basicConfig(level=logging.INFO)

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template('index.html', user=session["user"], passportConfig=passportConfig, roles=session['user']['roles'], version=msal.__version__)

@app.route("/login")
def login():
    # Technically we could use empty list [] as scopes to do just sign in,
    # here we choose to also collect end user consent upfront
    session["flow"] = _build_auth_code_flow(scopes=passportConfig['permissionScope'])
    return render_template("login.html", auth_url=session["flow"]["auth_uri"], version=msal.__version__)

@app.route(passportConfig['redirectPath'])  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    try:
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args)
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    except ValueError:  # Usually caused by CSRF
        pass  # Simply ignore them
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        passportConfig['authorityURI'] + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))

@app.route("/charters/createInvoice", methods = ['POST', 'GET'])
def createCharterInvoice():
    token = _get_token_from_cache(passportConfig['permissionScope'])
    if not token:
        return redirect(url_for("login"))
    if not 'CharterInvoice.Create' in session['user']['roles']:
        return redirect(url_for("index"))
    if request.method == 'POST':
        result = msmcharters.processCharterInvoiceForm(request.form)
        return render_template('charterInvoiceCreated.html', user=session["user"], result=result)
    else:
        return render_template('charterInvoiceForm.html', user=session["user"], locations=msmcharters.getCharterLocations())
    
@app.route("/events/customers", methods = ['POST', 'GET'])
def eventCustomers():
    token = _get_token_from_cache(passportConfig['permissionScope'])
    if not token:
        return redirect(url_for("login"))
    if not 'SpecialEvents.Purcases.Get' in session['user']['roles']:
        return redirect(url_for("index"))
    if request.method == 'POST':
        data = msmevents.processEventCustomersForm(request.form)
        return render_template('eventList.html', eventDetails=data['eventDetails'], customers=data['customers'])
    else:
        return render_template('eventListForm.html', user=session["user"], events=msmevents.getEventList(), urls=msmevents.getURLs())
    
@app.route("/events/ajax", methods = ['POST'])
def eventAjax():
    token = _get_token_from_cache(passportConfig['permissionScope'])
    if not token:
        return redirect(url_for("login"))
    if not 'SpecialEvents.Purcases.Get' in session['user']['roles']:
        return redirect(url_for("index"))
    else:
        return render_template('eventVariations.html', variations=msmevents.getVariations(request.form))

@app.route("/square/reports", methods = ['GET'])
def squareReports():
    token = _get_token_from_cache(passportConfig['permissionScope'])
    if not token:
        return redirect(url_for("login"))
    if not 'Square.DailyReports.Get' in session['user']['roles']:
        return redirect(url_for("index"))
    elif 'pdf' in request.args:
        return Response(msmsquareweb.getReport(request), mimetype="application/pdf")
    else:
        return Response(msmsquareweb.getReport(request), mimetype="text/html")
    
@app.route("/square/reports/select", methods = ['GET'])
def squareReportsSelect():
    token = _get_token_from_cache(passportConfig['permissionScope'])
    if not token:
        return redirect(url_for("login"))
    if not 'Square.DailyReports.Get' in session['user']['roles']:
        return redirect(url_for("index"))
    else:
        return render_template('squareReportsSelect.html', user=session["user"])
    
@app.route("/memberdb/tclmailing", methods = ['GET'])
def getTCLMailingList():
    token = _get_token_from_cache(passportConfig['permissionScope'])
    if not token:
        return redirect(url_for("login"))
    if not 'MembershipDB.TCLAddresses.Get' in session['user']['roles']:
        return redirect(url_for("index"))
    else:
        #Generate the list and return it as a CSV
        csvData = msmmembership.getTCLAllAddressesCSV()
        tclFile = Response(csvData, mimetype='text/csv', headers={'Content-disposition': 'attachment; filename=TCLAddresses.csv'})
        #return render_template('squareReportsSelect.html', user=session["user"])
        return tclFile

def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache

def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()

def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        passportConfig['clientID'], authority=authority or passportConfig['authorityURI'],
        client_credential=passportConfig['clientSecret'], token_cache=cache)

def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [],
        redirect_uri=url_for("authorized", _external=True, _scheme='https'))

def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result

app.jinja_env.globals.update(_build_auth_code_flow=_build_auth_code_flow)  # Used in template

if __name__ == "__main__":
    app.run()

