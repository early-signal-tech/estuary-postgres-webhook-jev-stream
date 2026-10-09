FROM python:3.12-slim

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

COPY . .

CMD ["python", "-u", "datagen.py"]
