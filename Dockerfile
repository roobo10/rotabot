FROM python:3-slim
ADD . /src
WORKDIR /src
RUN pip install -r requirements.txt
CMD python ./rotabot.py
