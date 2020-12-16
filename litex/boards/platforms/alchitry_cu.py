#
# This file is part of LiteX.
#
# Copyright (c) 2018 William D. Jones <thor0505@comcast.net>
# Copyright (c) 2019 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.build.lattice import LatticePlatform
from litex.build.lattice.programmer import IceStormProgrammer

# IOs ----------------------------------------------------------------------------------------------

_io = [
    # Clk / Rst
    ("clk100", 0, Pins("P7"), IOStandard("LVCMOS33")),
    ("rst_n", 0, Pins("P8"), IOStandard("LVCMOS33")),

    # Leds
    ("user1_led", 0, Pins("J11 K11 K12 K14"), IOStandard("LVCMOS33")),
    ("user2_led", 0, Pins("L12 L14 M12 N14"), IOStandard("LVCMOS33")),

    # USB
    #("usb", 0,
    #    Subsignal("d_p", Pins("B4")),
    #    Subsignal("d_n", Pins("A4")),
    #    Subsignal("pullup", Pins("A3")),
    #    IOStandard("LVCMOS33")
    #),

    # SPIFlash
    ("spiflash", 0,
        Subsignal("cs_n", Pins("P13"), IOStandard("LVCMOS33")),
        Subsignal("clk",  Pins("P12"), IOStandard("LVCMOS33")),
        Subsignal("mosi", Pins("M11"), IOStandard("LVCMOS33")),
        Subsignal("miso", Pins("P11"), IOStandard("LVCMOS33")) 
    ),

    # Serial
    ("serial", 0,
        Subsignal("rx", Pins("P14")), 
        Subsignal("tx", Pins("M9"), Misc("PULLUP")),
        IOStandard("LVCMOS33")
    ),
]

# Connectors ---------------------------------------------------------------------------------------

_connectors = [
    # A2-H2, Pins 1-13
    # H9-A6, Pins 14-24
    # G1-J2, Pins 25-31
    ("GPIO",  "A1 A2 A3 A4 A5 A6 A7 A10"
              "A11 A12 B1 B14 C1 C3 C4 C5"
              "C6 C7 C9 C10 C11 C12 C14 D1"
              "D3 D4 D5 D6 D7 D9 D10 D11 D12"
              "D14 E1 E4 E11 E12 E14 F3 F4"
              "F11 F12 F14 G1 G3 G4 G11 G12"
              "G14 H1 H3 H4 H11 H12 J1 J3"
              "J12 K3 K4 L1 L4 L5 L6 L8"
              "L9 M1 M3 M4 M6 M7 N1 P1"
              "P2 P3 P4 P5 P9 P10"),
]

# Default peripherals
#serial = [
#    ("serial", 0,
#        Subsignal("rx", Pins("GPIO:79")),
#        Subsignal("tx", Pins("GPIO:80"), Misc("PULLUP")),
#        IOStandard("LVCMOS33")
#    )
#]


# Platform -----------------------------------------------------------------------------------------
class Platform(LatticePlatform):
    default_clk_name   = "clk100"
    default_clk_period = 1e9/100e6

    def __init__(self, toolchain="icestorm"):
        LatticePlatform.__init__(self, "ice40-hx8k-cb132", _io, _connectors, toolchain=toolchain)
#        self.add_extension(serial)

    def create_programmer(self):
        return IceStormProgrammer()

    def do_finalize(self, fragment):
        LatticePlatform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request("clk100", loose=True), 1e9/16e6)
