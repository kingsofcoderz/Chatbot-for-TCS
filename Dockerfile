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

# ❌ DO NOT pull model here

CMD ollama serve & sleep 5 && ollama pull gemma:1b && python3 bot.py
