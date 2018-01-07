pi-vameter
==========

This is a little circuit to measure current and voltage of a Raspberry Pi
or other small computers using 5V input In contrast to ready to use
USB-dongles which you just plug in between the power source and the consumer,
this circuit feeds it's measurement into the SPI-interface  of a (second) Pi,
therefore you can record current, voltage and power over time.


Hardware
========

The Circuit
-----------

The circuit ![](doc/circuit.gif "circuit") mainly uses two components

  - a ADC converter with at least two channels (e.g. MCP3002)
  - a Hall sensor

The ADC will read the voltage on it's first channel directly. In the
Hall sensor the current induces a magnetic field, which in turn induces
some voltage which we feed into the ADC's second channel. We therefore
measure the current indirectly.


The Display
-----------

The measurement software supports a LCD display with 4 rows and 20 columns
attached to the I2C-interface of the Pi running the measurements. The display
is not strictly necessary, since it only displays live data. The recording
of the data is independent of the display.

When the measurement is started from a terminal (e.g. using ssh), the
live data is also displayed in the terminal.


Software
========

This project contains a number of software-components for the measurement
of the ADC values:

  - **vameter.py**: This script reads the values of the ADC using the SPI
    interface and records the data in a round-robin-database (RRD-database)
  - **vameterctrl**: A wrapper script for starting data-collection using
    a button attached to a GPIO-pin
  - **vameter-web.py**: A small webserver for starting and stopping the data
    collection and for the presentation of the results.


Installation
------------

The installation assumes that you have a freshly installed
Raspbian-Lite installation (Jessie and Stretch are fine).

Use the following commands to install the software:

    git clone https://github.com/bablokb/pi-vameter.git
    cd pi-vameter.git
    sudo tools/install
    cd ..
    git clone https://github.com/bablokb/gpio-poll-service.git
    cd gpio-poll-service
    sudo tools/install

The second set of installation commands is only necessary if you wish to
use buttons attached to GPIOs to control the measurement. In this case
you should check the file `/etc/gpio-poll.conf`. This file contains the
configuration of the pin for the button.

The install command will copy all scripts, install additional software
(mainly the required python-modules), modify `/boot/config.txt`, add a
system-user for the web-service and add a number of system-services. Due
to the changes to `/boot/config.txt` you have to reboot your system to
activate the changes.

Besides the configuration of the GPIO for the start/stop-button you also
have to check the script `/usr/local/bin/vameter.py`. Sadly, every ADC-converter
needs it's special read commands and you have to configure the data
for the ADC you are using. The script already contains some values for
widely used ADCs (check variable `ADC_BYTES` at the beginning of the script).
The variable contains two triplets, one for channel 0 and one for channel 1.


The database
------------

Data is stored in a round-robin-database using the **rrdtools**. The size
of the database does not grow with measurement time, since only a limited
amount of data is saved while older data is saved only in aggregated form.
The `vameter.py` script saves one hour of data with seconds-resolution,
24 hours of data with minute-resolution and so on.


Usage
=====

Script-based
------------

The command

    vameter.py -g IUP mydata.rrd

will start recording measurements and save the results in file `mydata.rrd`.
To stop the data-collection, hit CTRL-C. Since we passed the option `-g IUP`,
the script will generate after termination three graphics for current, voltage
and power.

You can use

    vameter.py -p mydata.rrd

to print existing data.

