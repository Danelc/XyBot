@ECHO OFF
START java -jar lavalink.jar
ECHO Giving Lavalink time to start...
TIMEOUT /t 5 /nobreak
START python "SigmaBot.py"