FROM python:3.11

WORKDIR /workspaces/TopBottomBot

RUN apt-get -y upgrade
RUN apt-get update && apt-get install -y \
    init \
    systemctl \
    sudo \
    curl \
    locales \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
#ENV LC_ALL ja_JP.UTF-8
ENV TZ Asia/Tokyo
ENV TERM xterm

COPY requirements.txt ./
COPY ignore ./ignore
COPY *.py ./    

RUN pip install --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt
#CMD [ "python3", "./Main.py" ]