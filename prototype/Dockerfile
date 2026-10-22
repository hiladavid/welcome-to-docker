#use python.
FROM python:3.11-slim

WORKDIR /app

#copy project files into the container.
COPY . /app

#download opencv.
RUN pip install opencv-python-headless

# default command.
CMD ["python", "tryAccessCamera.py"]