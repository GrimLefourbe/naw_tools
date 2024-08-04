set dotenv-load

default:
    @just --list

requirements:
    poetry export -f requirements.txt -o requirements.txt --with gradio_app

build:
    docker build -t nawminator .

run: build
    docker run --rm -it -p 7860:7860 --log-driver local nawminator

deploy_remote:
    scp -r app.py server.py naw_tools templates requirements.txt $SSH_USERNAME@$SSH_HOST:www
    ssh $SSH_USERNAME@$SSH_HOST ls
    ssh $SSH_USERNAME@$SSH_HOST "cd www;\source venv/bin/activate;\python -m pip install --upgrade pip;\pip install -r requirements.txt"
    ssh $SSH_USERNAME@$SSH_HOST touch www/tmp/restart.txt

deploy_debug: build
    docker run --rm -it -p 5000:5000 naw_tools python server.py

deploy_edit: build
    docker run --rm -it -p 5000:5000 -v $(pwd):/workspace naw_tools python /workspace/server.py

lint:
    poetry run black .

