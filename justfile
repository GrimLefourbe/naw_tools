set dotenv-load

default:
    @just --list

requirements:
    poetry export -f requirements.txt -o requirements.txt --with gradio_app

build:
    docker build -t nawminator .

run: build
    docker run --rm -it -p 7860:7860 --log-driver local nawminator

lint:
    poetry run black .

