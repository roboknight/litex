#!/usr/bin/env python3

#
# This file is part of LiteX.
#
# Copyright (c) 2020 Brandon Warhurst <warhurst_002@yahoo.com>
# SPDX-License-Identifier: BSD-2-Clause
import os
import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.boards.platforms import alchitry_cu

from litex.soc.cores.spi_flash import SpiFlash
from litex.soc.cores.clock import iCE40PLL
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.builder import *
from litex.soc.interconnect import wishbone
from litex.soc.cores.led import LedChaser
from litex.soc.cores.led import LedCtrl
from litex.soc.interconnect.csr import *

kB = 1024
mB = 1024*kB

# CRG -----------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_por = ClockDomain(reset_less=True)

        # # #

        # Clk/Rst

        clk100 = platform.request("clk100")
        rst_n  = platform.request("rst_n")

        # Power On Reset
        por_count = Signal(16, reset=2**16-1)
        por_done = Signal()
        self.comb += self.cd_por.clk.eq(ClockSignal())
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        self.submodules.pll = pll = iCE40PLL(primitive="SB_PLL40_PAD")
        self.comb += pll.reset.eq(~rst_n | self.rst)
        pll.register_clkin(clk100, 100e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq, with_reset=False)
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~por_done | ~pll.locked)
        platform.add_period_constraint(self.cd_sys.clk, 1e9/sys_clk_freq)

# RandomFirmware
def RandomFirmwareROM(size):
    import random
    random.seed(2373)
    data = []
    for d in range(int(size/4)):
        data.append(random.getrandbits(32))
    print("Firmware {} bytes of random data".format(size))
    #wishbone.SRAM.__init__(self, size, read_only=True, init=data)
    return data

# BaseSoc --------------------------------------------------------------------------

class BaseSoC(SoCCore):
    mem_map = {
        **SoCCore.mem_map,
        **{"spiflash": 0x80000000},
    }
    def __init__(self, bios_flash_offset, sys_clk_freq=int(50e6), **kwargs):
        platform = alchitry_cu.Platform()
        kwargs["integrated_sram_size"] = 2*kB
        kwargs["integrated_main_ram_size"] = 0*kB
        kwargs["integrated_rom_size"] = 0*kB

        # Set CPU variant /reset address
        kwargs["cpu_reset_address"] = self.mem_map["rom"]

        # SoCCore ------------------------------------------
        SoCCore.__init__(self, 
            platform, 
            sys_clk_freq,
            ident          = "LiteX SoC on Alchitry-CU",
            ident_version  = True,
            **kwargs)

        # CRG ----------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        bios_size = 0x2400
        #self.submodules.firmware_ram = RandomFirmwareROM(bios_size)
        #self.add_constant("ROM_DISABLE", 1)
        self.add_rom("rom", origin = self.mem_map["rom"], size = bios_size)
        self.initialize_rom(RandomFirmwareROM(bios_size))

        # SPI Flash ----------------------------------------
        if not self.integrated_rom_size:
            self.config["SPIFLASH_PAGE_SIZE"] = 256
            self.config["SPIFLASH_SECTOR_SIZE"] = 0x10000
            #self.add_spi_flash(mode="1x", dummy_cycles=8, clk_freq=sys_clk_freq/2)
            #self.register_rom(self.spiflash.bus, 4*1024*1024)
            #self.bus.add_slave("spiflash", self.spiflash.bus, SoCRegion(origin=self.mem_map["spiflash"], size=512*kB))
	    
        # LEDs ---------------------------------------------
        led2_pads = platform.request_all("user2_led")
        self.submodules.blink = LedCtrl(
            pads         = led2_pads)
        self.add_csr("blink")

        led1_pads = platform.request_all("user1_led")
        self.submodules.leds = LedChaser(
            pads         = led1_pads,
            sys_clk_freq = sys_clk_freq)
        self.add_csr("leds")

# Flash ---------------------------------------------------------------------------

def pack():
    from litex.build.lattice.programmer import IceStormProgrammer
    bios_file = "build/alchitry_cu/software/bios/dummy.bin"
    bits_file = "build/alchitry_cu/gateware/alchitry_cu.bin"
    mem_file  = "build/alchitry_cu/gateware/mem_2.init"
    out_file  = "build/alchitry_cu/gateware/alchitry_cu-patched.bin"
    prog = IceStormProgrammer()
    result = os.system("ice40-repack {0} {1} {2} {3}".format(bits_file, mem_file, bios_file, out_file))
    prog.flash(0x0, out_file)
    exit()    

def flash(bios_flash_offset):
    from litex.build.lattice.programmer import IceStormProgrammer
#    bios_file = "build/alchitry_cu/software/bios/bios.bin"
    bios_file = "build/alchitry_cu/software/bios/dummy.bin"
    bits_file = "build/alchitry_cu/gateware/alchitry_cu.bin"
    mem_file  = "build/alchitry_cu/gateware/mem.init"
    out_file  = "build/alchitry_cu/gateware/alchitry_cu-patched.bin"
    prog = IceStormProgrammer()
    prog.flash(bios_flash_offset, bios_file)
    exit()

# Build ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Alchitry-Cu")
    parser.add_argument("--build",             action="store_true", help="Build bitstream")
    parser.add_argument("--load",              action="store_true", help="Load bitstream")
    parser.add_argument("--bios-flash-offset", default=0x40000, help="BIOS offset in SPI Flash (default: 0x40000)")
    parser.add_argument("--flash",             action="store_true", help="Flash bitstream")
    parser.add_argument("--pack",              action="store_true", help="Repack and flash bitstream")
    parser.add_argument("--sys-clk-freq",      default=24e6, help="System clock frequency (default: 50MHz)")

    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()

    soc = BaseSoC(
        bios_flash_offset=args.bios_flash_offset, 
        sys_clk_freq = int(float(args.sys_clk_freq)), 
        **soc_core_argdict(args)
    )
    builder = Builder(soc, **builder_argdict(args))
    builder.build(run=args.build)

    #rom = open("build/alchitry_cu/software/bios/dummy.bin","rb").read()

    #soc.initialize_rom(rom)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bin"))

    if args.flash:
        flash(args.bios_flash_offset)

    if args.pack:
        pack()

if __name__ == "__main__":
    main()

