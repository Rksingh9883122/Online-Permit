<<<<<<< HEAD
=======


>>>>>>> 4a11c62ea7e50656edc948c4cbd28582c80c822c
FROM python:3.10

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["streamlit", "run", "app.py", "--server.port=8000", "--server.address=0.0.0.0"]
