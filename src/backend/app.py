import os

import dash

external_stylesheets = [
    # Dash CSS
    'https://codepen.io/chriddyp/pen/bWLwgP.css',
    # Loading screen CSS
    'https://codepen.io/chriddyp/pen/brPBPO.css',
    # Bootstrap
    'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@9.13.1/build/styles/tomorrow-night-eighties.min.css'
]

entity = os.getenv('LOCALHOST_OR_DOCKER')

app = dash.Dash(__name__,
                assets_folder='./assets/',
                external_stylesheets=external_stylesheets,
                meta_tags=[{'name': 'viewport',
                            'content': 'width=device-width, initial-scale=1'}]
                )
app.config.suppress_callback_exceptions = True
app.server.secret_key = os.environ.get('SECRET_KEY')
app.title = 'Opera'
