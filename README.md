# myblog

## Deploying
This app is deployed via Heroku:
`git push heroku master`

The app can then be accessed via `heroku open`

## Running server locally
First, run `python manage.py collectstatic`. Then run, `heroku local web`. The app should be accessible on 127.0.0.1:5000/