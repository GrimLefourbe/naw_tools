set dotenv-load

default:
    @just --list

requirements:
    poetry export -f requirements.txt -o requirements.txt --with flask_app

build:
    docker build -t naw_tools .

run: build
    docker run --rm -it -w /home naw_tools /bin/bash

deploy:
    scp -r app.py server.py naw_tools templates requirements.txt $SSH_USERNAME@$SSH_HOST:www
    ssh $SSH_USERNAME@$SSH_HOST ls
    ssh $SSH_USERNAME@$SSH_HOST "cd www;\source venv/bin/activate;\python -m pip install --upgrade pip;\pip install -r requirements.txt"
    ssh $SSH_USERNAME@$SSH_HOST touch www/tmp/restart.txt

