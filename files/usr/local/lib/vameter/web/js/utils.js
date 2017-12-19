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
  $.post("/start");
  showMsg("Starting data-collection ...",2000);
  $('#inpStart').val('');
  $('#Start').hide();
  $('#btnStop').show();
};

/**
  Handle action stop
*/

doStop=function() {
  $.post("/stop");
  showMsg("Stopping data-collection ...",2000);
  $('#Start').show();
  $('#btnStop').hide();
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
