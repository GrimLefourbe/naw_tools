set dotenv-load

default:
    @just --list

requirements:
    poetry export -f requirements.txt -o requirements.txt --with gradio_app

build:
    docker build -t $IMAGE_NAME .

dev_run:
    poetry run gradio nawminator/app.py

run: build
    docker run --rm -it -p 7860:7860 --log-driver local $IMAGE_NAME

push: build
    docker push $IMAGE_NAME

remote_run: build push
    ssh $SSH_USERNAME@$SSH_HOST "cd grim-infra/nawminator && docker pull $IMAGE_NAME && docker compose up -d"

lint:
    poetry run black .

test:
    poetry run pytest tests -vv

