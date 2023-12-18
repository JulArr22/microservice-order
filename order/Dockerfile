FROM python:3.10-slim
ADD ./requirements.txt /code/requirements.txt
COPY app /code/app
WORKDIR /code/app
RUN pip install -r ../requirements.txt
ENTRYPOINT uvicorn --host 0.0.0.0 --port ${UVICORN_PORT} main:app
