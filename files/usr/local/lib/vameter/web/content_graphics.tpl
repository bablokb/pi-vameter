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
}</script>

 <div class="w3-bar w3-black">
  <button class="w3-bar-item w3-button" onclick="openTab('ipng')">Current</button>
  <button class="w3-bar-item w3-button" onclick="openTab('upng')">Voltage</button>
  <button class="w3-bar-item w3-button" onclick="openTab('ppng')">Power</button>
  <button class="w3-bar-item w3-button" onclick="openTab('data')">Data</button>
</div> 

<div id="content_graphics" class="content">
  <div id="ipng" class="tab" style="display:none">
    <h2>Current</h2>
    <img src="img/loading.png" />
  </div>

  <div id="upng" class="tab" style="display:none">
    <h2>Voltage</h2>
    <img src="img/loading.png" />
  </div>

  <div id="ppng" class="tab" style="display:none">
    <h2>Power</h2>
    <img src="img/loading.png" />
  </div>

  <div id="data" class="tab" style="display:none">
    <h2>Data</h2>
    <p>Here is the data</p>
  </div>

</div>        <!-- id=content_graphics   -->
