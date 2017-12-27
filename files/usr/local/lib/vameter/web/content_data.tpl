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
        order: [[ 0, "asc" ]],
        columns: [
            { data: "name",     title: "Name",
              className: "dt-left" },
            { data: "ts_start", title: "Start",
              className: "dt-left",
              render: function(data,type,raw,meta) {
                        return (new Date(1000*data)).toLocaleString();
                      }
            },
            { data: "ts_end",   title: "End",
              className: "dt-left",
              render: function(data,type,raw,meta) {
                        return (new Date(1000*data)).toLocaleString();
                      }
             },
            { data: "I_avg",    title: "I (mA) avg",
              className: "dt-right" },
            { data: "I_max",    title: "I (mA) max",
              className: "dt-right" },
            { data: "U_avg",    title: "U (V) avg",
              className: "dt-right" },
            { data: "U_max",    title: "U (V) max",
              className: "dt-right" },
            { data: "P_avg",    title: "P (W) avg",
              className: "dt-right" },
            { data: "P_max",    title: "P (W) max",
              className: "dt-right" },
            { data: "P_tot",    title: "P (Wh) total",
              className: "dt-right" }
        ]
      });
      get_results();
      table.on('select', function(e,dt,type,indexes) {
        var data = table.rows(indexes).data();
        setTabData(data[0]);
      });
  });
</script>


<section class="w3-container" id="content_data">
  <h3>Measurements</h3>
  <table id="result_list" class="display"
         width="100%" cellspacing="0"></table>
</section>
