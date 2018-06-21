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

<script type="text/javascript">
  updateRenameButton = function() {
    if (current_selection && $('#inpStart').val()) {
      $('#btnRename').removeClass('w3-disabled');
    } else {
      $('#btnRename').addClass('w3-disabled');
      $('#btnRename').prop('disabled',true);
    }
  };

  // one-time initializations
  $(document).ready(function() {
    $('#inpStart').on('input',function() {
      updateRenameButton();
    });
  });

</script>

<div class="w3-bar w3-border w3-card-4 w3-blue">
  <div id="Start">
    <input id="inpStart" class="w3-bar-item w3-input" placeholder="name" />
    <a id="btnStart" href="#" class="w3-bar-item w3-button w3-border-right
                w3-mobile w3-green" onclick="doStart()">Start</a>
  </div>
  <a id="btnStop" href="#" style="display:none"
     class="w3-bar-item w3-button w3-border-right
                 w3-mobile w3-red" onclick="doStop()">Stop</a>

  <a id="btnRename" href="#" class="w3-bar-item w3-button w3-border-right
                w3-mobile w3-pale-green w3-disabled" onclick="doRename()">Rename</a>

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
  <div id="msgarea" class="w3-bar-item w3-margin-left"></div>
</div>
