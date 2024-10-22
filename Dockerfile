# code from a streamlit app Peter made. the commands should be relevant to what I'm doing but stuff inside

FROM python:3.11-slim

# install unzip
RUN apt-get update && apt-get install -y unzip postgresql-dev

WORKDIR /app
# copy everything in to the app folder (which we're already in)

COPY requirements.txt requirements.txt
# start building the environment that the app will run in
RUN pip3 install -r requirements.txt

COPY src .
# this the port that will be used in the container like here locally
EXPOSE 8501

EXPOSE 5433
#runs the command I'd run to start the app -- these are called "flags" and they're like arguments but they're not
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--browser.serverAddress=0.0.0.0", "--server.address=0.0.0.0", "–server.enableCORS False"]
