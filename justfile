set dotenv-load

default:
    @just --list

requirements:
    poetry export -f requirements.txt -o requirements.txt --with gradio_app

build:
    docker build -t $IMAGE_NAME .

run: build
    docker run --rm -it -p 7860:7860 --log-driver local $IMAGE_NAME

remote_run: build
    docker push $IMAGE_NAME
    ssh $SSH_USERNAME@$SSH_HOST "cd nawminator && docker pull $IMAGE_NAME && docker compose up -d"

lint:
    poetry run black .

test:
    poetry run pytest tests -vv

