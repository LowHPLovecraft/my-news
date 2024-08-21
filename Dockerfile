FROM arm64v8/python

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY certs/*.* /usr/local/share/ca-certificates
RUN update-ca-certificates

COPY . .

WORKDIR /app/certs
RUN python patch-certs.py

WORKDIR /app

CMD ["python", "app.py", "--no-web"]