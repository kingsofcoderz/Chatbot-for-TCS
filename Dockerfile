FROM ubuntu:22.04

RUN apt update && apt install -y \
    curl \
    python3 \
    python3-pip \
    zstd

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app
COPY . /app

RUN pip3 install -r requirements.txt

# pull model
RUN ollama pull gemma:1b

CMD ollama serve & python3 bot.py
