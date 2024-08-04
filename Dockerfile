FROM python:3.12.4

WORKDIR /home

COPY requirements.txt requirements.txt

RUN python -m pip install --upgrade pip; \
    python -m pip install -r requirements.txt


COPY nawminator nawminator

ENV PYTHONPATH=/home
CMD ["python", "nawminator/app.py"]
