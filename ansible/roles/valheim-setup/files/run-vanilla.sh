#!/bin/sh
export templdpath=$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=./linux64:$LD_LIBRARY_PATH
export SteamAppID=892970

echo "Starting server PRESS CTRL-C to exit"
exec ./valheim_server.x86_64 -name "Mablivion" -port 2456 -nographics -batchmode -world "Mablivion" -password "123123" -public 1 -logFile valheimds.log -modifier raids more -modifier resources muchmore -modifier Portals veryhard
export LD_LIBRARY_PATH=$templdpath