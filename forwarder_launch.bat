setlocal
call %~dp0..\..\..\config_env_base.bat
@echo on
set "GETMACRO=%EPICS_KIT_ROOT%\support\icpconfig\master\bin\%EPICS_HOST_ARCH%\icpconfigGetMacro.exe"
set "MYIOCNAME=FORWARDER"
set "KAFKA_BROKER=livedata.isis.cclrc.ac.uk:31092"
REM allow local config override in globals.txt
for /f %%a in ( '%GETMACRO% "KAFKA_BROKER" %MYIOCNAME%'  ) do ( set "KAFKA_BROKER=%%a" )

call %~dp0.venv\scripts\activate

set "EPICS_CA_ADDR_LIST=127.255.255.255 130.246.55.255"
set "EPICS_CA_AUTO_ADDR_LIST=NO"

echo "starting forwarder"
python %~dp0forwarder_launch.py --status-topic=%KAFKA_BROKER%/%INSTRUMENT%_forwarderStatus --config-topic=%KAFKA_BROKER%/%INSTRUMENT%_forwarderConfig --storage-topic=%KAFKA_BROKER%/%INSTRUMENT%_forwarderStorage  --output-broker=%KAFKA_BROKER%

