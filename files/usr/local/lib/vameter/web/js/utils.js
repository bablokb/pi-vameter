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
  $("#msgarea").html("<div class='msg_info'>"+text+"</div><br>");
  setTimeout(function() {
               $("#msgarea").empty();
             }, time);
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
      $('#inpStart').val('');
      $('#btnStop').show();
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
  $('#btnStop').hide();
  setTimeout(function() { get_results();},3000);
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
