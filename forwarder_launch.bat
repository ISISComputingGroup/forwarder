call C:\Instrument\Apps\EPICS\isis\forwarder\master\.venv\scripts\activate

set "EPICS_CA_ADDR_LIST=127.255.255.255 130.246.55.255"
set "EPICS_CA_AUTO_ADDR_LIST=NO"

if "%INSTRUMENT%" == "HIFI" (
    set "BROKER=130.246.55.29:9092"
) else (
    set "BROKER=livedata.isis.cclrc.ac.uk:31092"
)

echo "starting forwarder"
python C:\Instrument\Apps\EPICS\isis\forwarder\master\forwarder_launch.py --status-topic=%BROKER%/%INSTRUMENT%_forwarderStatus --config-topic=%BROKER%/%INSTRUMENT%_forwarderConfig --storage-topic=%BROKER%/%INSTRUMENT%_forwarderStorage  --output-broker=%BROKER%
