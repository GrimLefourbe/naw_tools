FROM python:3.12.11

WORKDIR /home

COPY requirements.txt requirements.txt

RUN python -m pip install --upgrade pip; \
    python -m pip install -r requirements.txt


COPY src src

ENV PYTHONPATH=/home/src
CMD ["python", "src/nmsite/app.py"]
