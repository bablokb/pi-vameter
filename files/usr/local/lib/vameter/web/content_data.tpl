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

  get_results = function() {
    $.ajax({
      type: "POST",
      cache: false,
      url: "/results",
      success: function(data){
        data.forEach(function(row) {
          row.ts_start = (new Date(1000*row.ts_start)).toLocaleString();
          row.ts_end   = (new Date(1000*row.ts_end)).toLocaleString();
        });
        var table = $('#result_list').DataTable();
        table.clear();
        table.rows.add(data).draw();
      }
    });
     return false;
  };

  $(document).ready(function() {
      var table = $("#result_list").DataTable( {
        select: {style: 'single'},
        columns: [
            { data: "name",     title: "Name" },
            { data: "ts_start", title: "Start" },
            { data: "ts_end",   title: "End" },
            { data: "I_avg",    title: "I (mA) avg" },
            { data: "I_max",    title: "I (mA) max" },
            { data: "U_avg",    title: "U (V) avg" },
            { data: "U_max",    title: "U (V) max" },
            { data: "P_avg",    title: "P (W) avg" },
            { data: "P_max",    title: "P (W) max" },
            { data: "P_tot",    title: "P (Wh) total" }
        ]
      });
      get_results();
      table.on('select', function(e,dt,type,indexes) {
        var data = table.rows(indexes).data();
        setTabData(data[0]);
      });
  });
</script>


<div id="content_data">

  <h2>Available Results</h2>
  <table id="result_list" 
         width="100%" cellspacing="0"></table>
</div>
