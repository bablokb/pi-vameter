#!/usr/bin/python
# Measure voltage and curent using a Hall-sensor and an ADC.
#
# This script just displays a logo on the display. It is started by the
# systemd-service vameter-logo.service
#
# Author: Bernhard Bablok, Lothar Hiller
# License: GPL3
#
# Website: https://github.com/bablokb/pi-vameter
#
# ----------------------------------------------------------------------------

try:
  import lcddriver
  from time import *
  lcd = lcddriver.lcd()
  lcd.lcd_clear()

  lcd.lcd_display_string("Project Pi-VA-Meter", 1)
  lcd.lcd_display_string("Authors:", 2)
  lcd.lcd_display_string("Bernhard Bablok ", 3)
  lcd.lcd_display_string("Lothar Hiller",4)
except:
  pass

