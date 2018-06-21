// ---------------------------------------------------------------------------
// JS support functions.
//
// Author: Bernhard Bablok
// License: GPL3
//
// Website: https://github.com/bablokb/pi-vameter
//
// ---------------------------------------------------------------------------


/**
  Show message in message-area
*/

showMsg=function(text,time) {
  $("#msgarea").text(text);
  setTimeout(function() {
               $("#msgarea").empty();
             }, time);
};

/**
  Setup SSE
*/

setup_SSE=function() {
  if (!!window.EventSource) {
    var source = new EventSource('/update');
    source.addEventListener('message', function(e) {
      data = JSON.parse(e.data);
      $("#I_act").text(data.I);
      $("#U_act").text(data.U);
      $("#P_act").text(data.P);
      $("#I_max").text(data.I_max);
      $("#U_max").text(data.U_max);
      $("#P_max").text(data.P_max);
      $("#s_tot").text(data.s_tot);
      $("#P_tot").text(data.P_tot);
     }, false);
  }
};

/**
  Handle action start
*/

doStart=function() {
  var name = $('#inpStart').val();
  $.ajax({
    type: "POST",
        data : {name: name},
    cache: false,
    url: "/start",
    success: function(data){
      showMsg("Starting data-collection ...",2000);
      $('#Start').hide();
      $('#btnRename').hide();
      $('#inpStart').val('');
      $('#btnStop').show();
      setup_SSE();
      $('#Live').show();
    }
  });
};

/**
  Handle action stop
*/

doStop=function() {
  $.post("/stop");
  showMsg("Stopping data-collection ...",3000);
  $('#Start').show();
  $('#btnRename').show();
  $('#btnStop').hide();
  $('#Live').hide();
  setTimeout(function() { get_results();},3000);
};

/**
  Handle rename start
*/

doRename=function() {
  var new_name = $('#inpStart').val();
  var name     = current_selection.name;
   showMsg("Starting rename ...",2000);
   $('#Start').hide();
   $('#inpRename').hide();
   $('#inpStart').val('');
  $.ajax({
    type: "POST",
        data : {name:     name,
                new_name: new_name},
    cache: false,
    url: "/rename",
    success: function(data){
      $('#Start').show();
      $('#inpRename').show();
      setTimeout(function() { get_results();},500);
    },
    error: function(err) {
      $('#Start').show();
      $('#inpRename').show();
      showMsg(err);
    }
  });
};

/**
  Handle action shutdown
*/

doShutdown=function() {
  $.post("/shutdown");
  showMsg("Shutting down the system ...",2000);
};

/**
  Handle action reboot
*/

doReboot=function() {
  $.post("/reboot");
  showMsg("Rebooting the system ...",2000);
};

/**
  Handle action delete
*/

doDelete=function(name) {
  $.ajax({
    type: "POST",
        data : {name: name},
    cache: false,
    url: "/delete",
    success: function(data){
      showMsg(data.msg,3000);
      get_results();
    },
    error: function(data){
      showMsg(data.msg,3000);
  },
  });
};

/**
  Handle action download
*/

doDownload=function(name) {
  window.location="/download?name="+name;
};

/**
 * Handle author info.
 */

function onAuthor() {
  showMsg("Copyright Lothar Hiller, Bernhard Bablok, bablokb@gmx.de",3000);
}

/**
 * Handle license info.
 */

function onLicense() {
  showMsg("Unless otherwise noted, the code of this project is realeased under the GPL3",3000);
}
