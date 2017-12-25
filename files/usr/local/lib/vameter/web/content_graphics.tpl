<!--
# ----------------------------------------------------------------------------
# Simple web-interface for the results of pi-vameter.py 
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
  function openTab(tabName) {
    var i;
    var x = document.getElementsByClassName("tab");
    for (i = 0; i < x.length; i++) {
        x[i].style.display = "none";
    }
    document.getElementById(tabName).style.display = "block";
  };

  function setTabData(line) {
    console.error("setting src for ipng",line);
    $('#I_img').attr('src',line['I_img']);
    $('#U_img').attr('src',line['U_img']);
    $('#P_img').attr('src',line['P_img']);
  };
</script>

<section class="w3-container">
 <h3>Details</h3>
 <div class="w3-bar w3-black">
  <button class="w3-bar-item w3-button" onclick="openTab('ipng')">Current</button>
  <button class="w3-bar-item w3-button" onclick="openTab('upng')">Voltage</button>
  <button class="w3-bar-item w3-button" onclick="openTab('ppng')">Power</button>
</div> 

<div id="content_graphics" class="content">
  <div id="ipng" class="tab" style="display:none">
    <h2>Current</h2>
    <img id="I_img" src="img/loading.png" />
  </div>

  <div id="upng" class="tab" style="display:none">
    <h2>Voltage</h2>
    <img id="U_img" src="img/loading.png" />
  </div>

  <div id="ppng" class="tab" style="display:none">
    <h2>Power</h2>
    <img id="P_img" src="img/loading.png" />
  </div>
</div>        <!-- id=content_graphics   -->
</section>
