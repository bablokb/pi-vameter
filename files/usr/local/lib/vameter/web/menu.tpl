<!--
# ----------------------------------------------------------------------------
# Simple web-interface for the results of pi-vameter.py 
#
# This file defines the navigation-menu
#
# Author: Bernhard Bablok
# License: GPL3
#
# Website: https://github.com/bablokb/pi-vameter
#
# ----------------------------------------------------------------------------
-->

<div class="w3-bar w3-border w3-card-4 w3-blue">
  <a href="#" class="w3-bar-item w3-button w3-border-right 
                w3-mobile w3-green" onclick="doStart()">Start</a>
  <a href="#" class="w3-bar-item w3-button w3-border-right
                 w3-mobile w3-red" onclick="doStop()">Stop</a>

  <a href="#" class="w3-bar-item w3-button w3-border-right
                 w3-mobile">System-Info</a>
  <a href="#" class="w3-bar-item w3-button w3-border-right
                 w3-mobile" onclick="doReboot()">Reboot</a>
  <a href="#" class="w3-bar-item w3-button w3-border-right
                 w3-mobile" onclick="doShutdown()">Shutdown</a>

  <a href="#" class="w3-bar-item w3-button w3-border-right
                w3-mobile w3-light-blue">Project</a>
  <a href="#" class="w3-bar-item w3-button w3-border-right
                w3-mobile w3-light-blue" onclick="onAuthor()">Author</a>
  <a href="#" class="w3-bar-item w3-button w3-border-right
                w3-mobile w3-light-blue" onclick="onLicense()">License</a>
</div>
