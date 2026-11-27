# OkeyDocu - okeydocu/devices/climate/__init__.py
# Climate sensors over Bluetooth Low Energy: air temperature and relative humidity.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A climate sensor tells its readings in its advertisements; which way it words them is its
protocol. `protocols` decodes the ways known, `bluez` listens to the adapter and talks to a
sensor, the driver puts both behind the instrument interface of the application."""
