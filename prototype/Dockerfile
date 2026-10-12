#use docker server.
FROM ://microsoft.com

#determines python version.
ENV PYTHON_VERSION=3.11.5

#download python installer.
RUN powershell -Command \
    Invoke-WebRequest -Uri "https://python.org" -OutFile "python-installer.exe" ; \
    Start-Process "python-installer.exe" -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait ; \
    Remove-Item "python-installer.exe"

#defines work folder for container.
WORKDIR C:/app

# default command.
CMD ["python"]
