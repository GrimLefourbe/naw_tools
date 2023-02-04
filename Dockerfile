FROM python:3.8.16

WORKDIR home

COPY requirements.txt requirements.txt

RUN python -m pip install --upgrade pip; \
    python -m pip install -r requirements.txt


COPY naw_tools naw_tools
COPY server.py server.py
COPY templates templates
COPY app.py app.py

CMD ["bash"]
