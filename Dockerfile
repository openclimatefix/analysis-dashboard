# code from a streamlit app Peter made. the commands should be relevant to what I'm doing but stuff inside

FROM python:3.9-slim

WORKDIR /app
# copy everything in to the app folder (which we're already in)
COPY . .
# start building the environment that the app will run in
RUN pip3 install -r requirements.txt
# this the port that will be used in the container like here locally
EXPOSE 8501
#runs the command I'd run to start the app
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]