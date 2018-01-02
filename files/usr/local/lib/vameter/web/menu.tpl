<!--
# ----------------------------------------------------------------------------
# Simple web-interface for the results of vameter.py
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
  <div id="Start">
  <input id="inpStart" class="w3-bar-item w3-input" placeholder="name" />
  <a id="btnStart" href="#" class="w3-bar-item w3-button w3-border-right
                w3-mobile w3-green" onclick="doStart()">Start</a>
  </div>
  <a id="btnStop" href="#" style="display:none"
     class="w3-bar-item w3-button w3-border-right
                 w3-mobile w3-red" onclick="doStop()">Stop</a>

  <a id="btnReboot" href="#" class="w3-bar-item w3-button w3-border-right
                 w3-mobile" onclick="doReboot()">Reboot</a>
  <a id="btnShutdown" href="#" class="w3-bar-item w3-button w3-border-right
                 w3-mobile" onclick="doShutdown()">Shutdown</a>

  <a id="btnProject" href="https://github.com/bablokb/pi-vameter"
                     target="_blank"
                     class="w3-bar-item w3-button w3-border-right
                            w3-mobile w3-light-blue">Project</a>
  <a id="btnAuthor" href="#" class="w3-bar-item w3-button w3-border-right
                w3-mobile w3-light-blue" onclick="onAuthor()">Author</a>
  <a id="btnLicense" href="#" class="w3-bar-item w3-button w3-border-right
                w3-mobile w3-light-blue" onclick="onLicense()">License</a>
</div>
