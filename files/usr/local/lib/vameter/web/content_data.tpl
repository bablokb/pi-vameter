<!--
# ----------------------------------------------------------------------------
# Simple web-interface for the results of vameter.py
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

  var current_selection;

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

  getDelButton = function(name) {
    var head =  '<img class = "w3-border" src="images/trash.png" alt="delete" onClick="doDelete(\'';
    var end  =  '\')">';
    return head + name + end;
  };

  getDldButton = function(name) {
    var head =  '<img class = "w3-border" src="images/download.png" alt="download" onClick="doDownload(\'';
    var end  =  '\')">';
    return head + name + end;
  };

  $(document).ready(function() {
      var table = $("#result_list").DataTable( {
        select: {style: 'single'},
        order: [[ 1, "desc" ]],
        columns: [
            { data: "name",     title: "Name",
              className: "dt-left" },
            { data: "ts_start", title: "Start",
              className: "dt-left",
              render: function(data,type,raw,meta) {
                        if (type === 'display') {
                          return (new Date(1000*data)).toLocaleString();
                        } else {
                          return data;
                        }
                      }
            },
            { data: "ts_end",   title: "End",
              className: "dt-left",
              render: function(data,type,raw,meta) {
                        if (type === 'display') {
                          return (new Date(1000*data)).toLocaleString();
                        } else {
                          return data;
                        }
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
              className: "dt-right" },
            { data: null,    title: "Del",
              className: "dt-right",
              render: function(data,type,raw,meta) {
                   return getDelButton(data.name);
              }
             },
            { data: null,    title: "Save",
              className: "dt-right",
              render: function(data,type,raw,meta) {
                   return getDldButton(data.name);
              }
             },
        ]
      });
      get_results();
      table.on('select', function(e,dt,type,indexes) {
        var data = table.rows(indexes).data();
        current_selection = data[0];
        setTabData(data[0]);
      });
  });
</script>


<section class="w3-container" id="content_data">
  <h3>Measurements</h3>
  <table id="result_list" class="display"
         width="100%" cellspacing="0"></table>
</section>
