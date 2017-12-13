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
        $.each(data,function(row) {
          row.start_ts = (new Date(row.start_ts)).toLocaleString();
          row.end_ts = (new Date(row.end_ts)).toLocaleString();
        });
        var table = $('#result_list').DataTable();
        table.clear();
        table.rows.add(data).draw();
      }
    });
     return false;
  };

  $(document).ready(function() {
      $("#result_list").DataTable( {
        select: {style: 'single'},
        columns: [
            { data: "start_ts", title: "Start" },
            { data: "end_ts",   title: "End" },
            { data: "I_avg",    title: "I (mA) avg" },
            { data: "I_max",    title: "I (mA) max" },
            { data: "U_avg",    title: "U (V) avg" },
            { data: "U_max",    title: "U (V) max" },
            { data: "P_avg",    title: "P (W) avg" },
            { data: "P_tot",    title: "P (WH) total" }
        ]
      });
      get_results();
  });
</script>


<div id="content_data">

  <h2>Available Results</h2>
  <table id="result_list" 
         width="100%" cellspacing="0"></table>
</div>
