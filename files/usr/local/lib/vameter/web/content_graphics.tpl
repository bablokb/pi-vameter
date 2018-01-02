<!--
# ----------------------------------------------------------------------------
# Simple web-interface for the results of vameter.py
#
# This file defines the content area for graphical output
#
# Author: Bernhard Bablok
# License: GPL3
#
# Website: https://github.com/bablokb/pi-vameter
#
# ----------------------------------------------------------------------------
-->

<script  type="text/javascript">
  var selected_tab = null;
  function openTab(button,tabName) {
    $(".tab").css("display","none");
    $(tabName).css("display","block");
    $(".detail").removeClass("w3-blue-gray");
    $(button).addClass("w3-blue-gray");
    selected_tab = button;
  };

  function setTabData(line) {
    if (!selected_tab) {
      $("#btnCurrent").click();
    }
    $('#I_img').attr('src',line['I_img']);
    $('#U_img').attr('src',line['U_img']);
    $('#P_img').attr('src',line['P_img']);
  };
</script>

<section class="w3-container">
 <h3>Details</h3>
 <div class="w3-bar w3-black">
  <button id="btnCurrent" class="detail w3-bar-item w3-button"
          onclick="openTab(this,'#ipng')">Current</button>
  <button id="btnVoltage" class="detail w3-bar-item w3-button"
          onclick="openTab(this,'#upng')">Voltage</button>
  <button id="btnPower" class="detail w3-bar-item w3-button"
          onclick="openTab(this,'#ppng')">Power</button>
</div> 

<div id="content_graphics" class="content">
  <div id="ipng" class="tab" style="display:none">
    <img id="I_img" />
  </div>

  <div id="upng" class="tab" style="display:none">
    <img id="U_img" />
  </div>

  <div id="ppng" class="tab" style="display:none">
    <img id="P_img" />
  </div>
</div>        <!-- id=content_graphics   -->
</section>
