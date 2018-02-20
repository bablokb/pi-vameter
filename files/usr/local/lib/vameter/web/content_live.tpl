<!--
# ----------------------------------------------------------------------------
# Simple web-interface for the results of vameter.py
#
# This file defines the display of live values
#
# Author: Bernhard Bablok
# License: GPL3
#
# Website: https://github.com/bablokb/pi-vameter
#
# ----------------------------------------------------------------------------
-->

<div id="Live" style="display:none" class="w3-panel">
  <div class="w3-center w3-cell w3-card-4">
    <table class="w3-table w3-striped w3-border">
      <tr>
        <th></th>
        <th>I (mA)</th>
        <th>U (V)</th>
        <th>P (W)</th>
      </tr>
      <tr>
        <td>actual</td>
        <td id="I_act"></td>
        <td id="U_act"></td>
        <td id="P_act"></td>
      </tr>
      <tr>
        <td>maximal</td>
        <td id="I_max"></td>
        <td id="U_max"></td>
        <td id="P_max"></td>
      </tr>
      <tr>
        <td>total</td>
        <td id="s_tot" colspan="2"></td>
        <td id="P_tot"></td>
      </tr>
    </table>
  </div>
</div>
