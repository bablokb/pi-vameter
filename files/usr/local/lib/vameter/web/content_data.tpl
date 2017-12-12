<!--
# ----------------------------------------------------------------------------
# Simple web-interface for the results of pi-vameter.py 
#
# This file defines the content area for data (table of available results)
#
# Author: Bernhard Bablok
# License: GPL3
#
# Website: https://github.com/bablokb/pi-vameter
#
# ----------------------------------------------------------------------------
-->

<script  type="text/javascript">
  $(document).ready(function() {
      $("#result_list").DataTable( {
        select: {style: 'single'},
        columns: [
            { data: "START_DT", title: "Start" },
            { data: "END_DT",   title: "End" },
            { data: "NAME",     title: "Name" },
            { data: "DELETE",   title: "Delete" },
            { data: "DOWNLOAD", title: "Download" }
        ]
      });
  });
</script>


<div id="content_data">

  <h2>Available Results</h2>
  <table id="result_list" 
         width="100%" cellspacing="0"></table>
</div>
