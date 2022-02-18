# Major parts from https://github.com/kakou-fr/mmu2_1S_klipper_config and https://github.com/EtteGit/EnragedRabbitProject
# But modified to our needs

# setup:
# ln -s ~/klipper_config/MMU/Python/mmu2s.py ~/klipper/klippy/extras/mmu2s.py

import gc
from time import sleep

class Mmu2s:

    def __init__(self, config):
        # Config
        self.config = config
        self.printer = config.get_printer()
        self.common_variables = self.printer.lookup_object("save_variables").allVariables
        self.mmu_variables = self.printer.lookup_object("gcode_macro _VAR_MMU2S").variables
        self.printer.register_event_handler("klippy:connect", self.handle_connect)

        # Sensors
        self.ir_sensor = self.printer.lookup_object("filament_switch_sensor ir_sensor")
        self.finda_sensor = self.printer.lookup_object("filament_switch_sensor finda")

        # Initial values
        self.homed = False
        self.locked = False
        self.extruder_steppers_synced = False
        self.idler_position = -1
        self.selector_position = -1
        self.led_enabled = bool(self.mmu_variables["enable_led"])

        # Steppers
        self.selector_stepper = None
        self.idler_stepper = None

        # Gcode
        self.gcode = self.printer.lookup_object('gcode')
        self.register_gcode_commands()

    def register_gcode_commands(self):
        self.gcode.register_command('MMU_LOAD_FILAMENT_TO_FINDA',
                    self.cmd_MMU_LOAD_FILAMENT_TO_FINDA,
                    desc=self.cmd_MMU_LOAD_FILAMENT_TO_FINDA_help)
        
        self.gcode.register_command('MMU_LOAD_FILAMENT_TO_EXTRUDER',
                    self.cmd_MMU_LOAD_FILAMENT_TO_EXTRUDER,
                    desc=self.cmd_MMU_LOAD_FILAMENT_TO_EXTRUDER_help)

        self.gcode.register_command('MMU_UNLOAD_FILAMENT_TO_FINDA',
                    self.cmd_MMU_UNLOAD_FILAMENT_TO_FINDA,
                    desc=self.cmd_MMU_UNLOAD_FILAMENT_TO_FINDA_help)

        self.gcode.register_command('MMU_CHANGE_TOOL',
                    self.cmd_MMU_CHANGE_TOOL,
                    desc=self.cmd_MMU_CHANGE_TOOL_help)

        self.gcode.register_command('_MMU_LT',
                    self.cmd_MMU_LT,
                    desc=self.cmd_MMU_LT_help)

        self.gcode.register_command('_MMU_UT',
                    self.cmd_MMU_UT,
                    desc=self.cmd_MMU_UT_help)

        self.gcode.register_command('MMU_SELECT_TOOL',
                    self.cmd_MMU_SELECT_TOOL,
                    desc=self.cmd_MMU_SELECT_TOOL_help)

        self.gcode.register_command('MMU_UNSELECT_TOOL',
                    self.cmd_MMU_UNSELECT_TOOL,
                    desc=self.cmd_MMU_UNSELECT_TOOL_help)

        self.gcode.register_command('MMU_MOVE_IDLER',
                    self.cmd_MMU_MOVE_IDLER,
                    desc=self.cmd_MMU_MOVE_IDLER_help)

        self.gcode.register_command('MMU_MOVE_SELECTOR',
                    self.cmd_MMU_MOVE_SELECTOR,
                    desc=self.cmd_MMU_MOVE_SELECTOR_help)

        self.gcode.register_command('M702',
                    self.cmd_M702,
                    desc=self.cmd_M702_help)

        self.gcode.register_command('MMU_HOME',
                    self.cmd_MMU_HOME,
                    desc=self.cmd_MMU_HOME_help)

        self.gcode.register_command('MMU_HOME_FORCE',
                    self.cmd_MMU_HOME_FORCE,
                    desc=self.cmd_MMU_HOME_FORCE_help)

        self.gcode.register_command('MMU_HOME_ONLY',
                    self.cmd_MMU_HOME_ONLY,
                    desc=self.cmd_MMU_HOME_ONLY_help)

        self.gcode.register_command('MMU_UNLOCK',
                    self.cmd_MMU_UNLOCK,
                    desc=self.cmd_MMU_UNLOCK_help)

        self.gcode.register_command('MMU_RESUME',
                    self.cmd_MMU_RESUME,
                    desc=self.cmd_MMU_RESUME_help)

        self.gcode.register_command('MMU_CUT_FILAMENT',
                    self.cmd_MMU_CUT_FILAMENT,
                    desc=self.cmd_MMU_CUT_FILAMENT_help)

    def handle_connect(self):
        self.toolhead = self.printer.lookup_object('toolhead')
        for manual_stepper in self.printer.lookup_objects('manual_stepper'):
            rail_name = manual_stepper[1].get_steppers()[0].get_name()
            if rail_name == 'manual_stepper selector_stepper':
                self.selector_stepper = manual_stepper[1]
            if rail_name == 'manual_stepper idler_stepper':
                self.idler_stepper = manual_stepper[1]
        if self.selector_stepper is None:
            raise self.config.error("Manual_stepper selector_stepper must be specified")
        if self.idler_stepper is None:
            raise self.config.error("Manual_stepper idler_stepper must be specified")

    def sync_extruder_steppers(self):
        if not self.extruder_steppers_synced:
            self.gcode.run_script_from_command("SYNC_STEPPER_TO_EXTRUDER STEPPER=gear_stepper EXTRUDER=extruder")
            self.gcode.run_script_from_command("G92 E0")
            self.extruder_steppers_synced = True

    def unsync_extruder_steppers(self):
        if self.extruder_steppers_synced:
            self.gcode.run_script_from_command("SYNC_STEPPER_TO_EXTRUDER STEPPER=gear_stepper EXTRUDER=")
            self.gcode.run_script_from_command("G92 E0")
            self.extruder_steppers_synced = False

    def ir_sensor_state(self):
        return bool(self.ir_sensor.runout_helper.filament_present)

    def finda_sensor_state(self):
        return bool(self.finda_sensor.runout_helper.filament_present)

    cmd_MMU_LOAD_FILAMENT_TO_FINDA_help = "Load filament until Finda registers it"
    def cmd_MMU_LOAD_FILAMENT_TO_FINDA(self, gcmd):
        stepsize = 10
        loaded = False

        if self.finda_sensor_state():
            gcmd.respond_info("Filament already in finda")
        else:
            self.gcode.run_script_from_command("G92 E0")
            for i in range (0, 200, stepsize):
                if not self.finda_sensor_state():
                    gcmd.respond_info("Loaded %s mm of filament to finda." % (i))
                    self.extrude(stepsize, 40*60)
                else:
                    self.extrude(stepsize, 40*60)
                    loaded = True
                    break
            self.gcode.run_script_from_command("G92 E0")
            if loaded:
                gcmd.respond_info("Filament loaded successfully to finda")  
            else:
                gcmd.respond_info("FILAMENT NOT IN FINDA!!!")  

    def extrude(self, length, feedrate):
        if length and feedrate:
            self.gcode.run_script_from_command("G92 E0")
            self.gcode.run_script_from_command("G1 E%s F%s" % (length, feedrate))
            self.gcode.run_script_from_command("M400")

    def retract(self, length, feedrate):
        if length and feedrate:
            self.extrude(-length, feedrate)

    cmd_MMU_LOAD_FILAMENT_TO_EXTRUDER_help = "Load filament from Finda to Extruder"
    def cmd_MMU_LOAD_FILAMENT_TO_EXTRUDER(self, gcmd):
        stepsize = 30
        smallsteps = 3
        loaded = False
        final_load_startvalue = None
        final_load_endvalue = None
        bowden_length = self.common_variables.get("mmu_bowden_length", -1)

        if not self.finda_sensor_state():
            self.cmd_MMU_LOAD_FILAMENT_TO_FINDA(gcmd)

            if not self.finda_sensor_state():
                raise gcmd.error("Filament not in Finda!")

        if self.ir_sensor_state():
            gcmd.respond_info("Filament already in Extruder!")
            return
        else:
            self.gcode.run_script_from_command("G92 E0")
            
            if bowden_length == -1:    
                for i in range (0, 700, stepsize):
                    if not self.ir_sensor_state():
                        gcmd.respond_info("Approx. Loading: %s mm of filament to Extruder." % (i))
                        self.extrude(stepsize, 2400)
                    else:
                        loaded = True
                        final_load_startvalue = i - stepsize - 5
                        self.retract(stepsize+5, 2400)
                        break
                if not loaded:
                    raise gcmd.error("Extruded %s mm Filament, but nothing in Extruder!!" % (i))  
                    return
            else:
                final_load_startvalue = bowden_length*0.85
                gcmd.respond_info("Fast Loading with saved variable: %s mm of filament to Extruder." % (final_load_startvalue))
                self.extrude(final_load_startvalue, 3000)

            sleep(1)
            for j in range (0, stepsize * 10, smallsteps):
                if not self.ir_sensor_state():
                    gcmd.respond_info("Final Loading: %s mm of filament to Extruder." % (final_load_startvalue + j))
                    self.extrude(smallsteps, 600)
                else:
                    self.extrude(smallsteps, 600)
                    loaded = True
                    final_load_endvalue = final_load_startvalue + j
                    break

            self.gcode.run_script_from_command("G92 E0")
            if loaded:
                gcmd.respond_info("Filament loaded successfully to Extruder (%s mm)" % (final_load_endvalue))
                if bowden_length == -1:
                    self.gcode.run_script_from_command("SAVE_VARIABLE VARIABLE=mmu_bowden_length VALUE=%s" % (final_load_endvalue))
            else:
                gcmd.respond_info("FILAMENT NOT IN EXTRUDER!!!")  

    cmd_MMU_UNLOAD_FILAMENT_TO_FINDA_help = "Unload from extruder to the FINDA"
    def cmd_MMU_UNLOAD_FILAMENT_TO_FINDA(self, gcmd):
        paused = self.printer.lookup_object("gcode_macro MMU_PAUSE").variables["is_paused"]
        tool = self.printer.lookup_object("gcode_macro MMU_SELECT_TOOL").variables["tool_selected"]
        bowden_length = self.common_variables.get("mmu_bowden_length", -1)
        stepsize = 10

        if paused == 0:
            if tool != -1:
                if self.ir_sensor_state():
                    gcmd.respond_info("Unloading filament from extruder to FINDA ...")
                    self.retract(bowden_length*0.85, 3000)
                    
                if self.finda_sensor_state():
                    gcmd.respond_info("Unloading filament from FINDA ...")
                    self.gcode.run_script_from_command("G92 E0")
                    for i in range (0, 600, stepsize):
                        if self.finda_sensor_state():
                            gcmd.respond_info("Unloaded %s mm of filament to finda." % (i))
                            self.retract(i, 40*60)
                        else:
                            self.retract(i+5, 40*60)
                            break
                else:
                    self.retract(25, 1000)
                gcmd.respond_info("Unloading done from FINDA to extruder")
            else:
                gcmd.respond_info("Cannot unload from extruder to FINDA, tool not selected !!")  
                return
        else:
            gcmd.respond_info("MMU is paused!!")  
            return

    cmd_MMU_CHANGE_TOOL_help = "Changes the Extruder to the given tool VALUE (0-4)"
    def cmd_MMU_CHANGE_TOOL(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            raise gcmd.error("Integer VALUE has to be entered")

        if not 0 <= tool <= 4:
            raise gcmd.error("VALUE not between 0 and 4")

        if self.color_selected != tool:
            gcmd.respond_info("Changing Tool to %s" % (tool))
            self.cmd_MMU_UT(gcmd)
            self.cmd_MMU_LT(gcmd)
        else:
            gcmd.respond_info("No change needed. Tool %s already active." % (tool))

#
#Extrude Filament
    #Wait_for_finished
#Retract Filament
    #Wait_for_finished

    cmd_MMU_LT_help = "Load filament from MMU2S to nozzle"
    def cmd_MMU_LT(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            raise gcmd.error("Integer VALUE has to be entered")

        if not self.locked:
            gcmd.respond_info("LT %s" % (tool))
            self.cmd_MMU_SELECT_TOOL(gcmd)
            self.cmd_MMU_LOAD_FILAMENT_TO_EXTRUDER(gcmd)
            self.load_filament_into_nozzle(gcmd)
        else:
            raise gcmd.error("NO LT MADE, MMU is locked")

    cmd_MMU_UT_help = "Unload filament from nozzle to MMU2S"
    def cmd_MMU_UT(self, gcmd):
        if not self.locked:
            if self.idler_position != -1:
                gcmd.respond_info("UT %s" % (self.idler_position))
                self.gcode.run_script_from_command("MMU_UNLOAD_FILAMENT_IN_EXTRUDER")
                self.cmd_MMU_SELECT_TOOL({"VALUE": self.idler_position})
                self.cmd_MMU_UNLOAD_FILAMENT_TO_FINDA(gcmd)
            else:
                raise gcmd.error("NO UT MADE, no tool activate")
        else:
            raise gcmd.error("NO UT MADE, MMU is locked")

    def load_filament_into_nozzle(self, gcmd):
        hotend_length = self.common_variables.get("mmu_hotend_length", -1)
        if hotend_length == -1:
            gcmd.respond_info("Hotend length for loading check not configured. Using and saving: 50mm")
            hotend_length = 50
            self.gcode.run_script_from_command("SAVE_VARIABLE VARIABLE=mmu_hotend_length VALUE=%s" % (hotend_length))

        if self.ir_sensor_state():
            self.gcode.run_script_from_command("G92 E0")

            self.extrude(hotend_length, 10*60)
            self.retract(hotend_length-2, 20*60)

            if self.ir_sensor_state():
                self.extrude(hotend_length, 10*60)
                gcmd.respond_info("Check load filament to nozzle successful")
            else:
                raise gcmd.error("Hotend possibly clogged!!")

            self.gcode.run_script_from_command("G92 E0")

    cmd_MMU_SELECT_TOOL_help = "Select a tool. move the idler and then move the color selector (if needed)"
    def cmd_MMU_SELECT_TOOL(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            raise gcmd.error("Integer VALUE has to be entered")
        
        if not self.locked:
            if self.homed:
                gcmd.respond_info("Select Tool %s" % (tool))
                self.cmd_MMU_MOVE_IDLER(gcmd)
                self.cmd_MMU_MOVE_SELECTOR(gcmd)
                if self.led_enabled:
                    self.gcode.run_script_from_command("LED_MMU VALUE=%s" % (tool))
                gcmd.respond_info("Tool %s enabled" % (tool))
            else:
                raise gcmd.error("Selected no tool, MMU is not homed")
        else:
            raise gcmd.error("Selected no tool, MMU is locked")

    cmd_MMU_UNSELECT_TOOL_help = "Unselect a tool, only park the idler"
    def cmd_MMU_UNSELECT_TOOL(self, gcmd):
        if not self.locked:
            if self.homed:
                self.cmd_MMU_MOVE_IDLER({"VALUE": -1})
            else:
                raise gcmd.error("Did not unselect tool, MMU is not homed.")
        else:
            raise gcmd.error("Did not unselect tool, MMU is locked.")

    cmd_MMU_MOVE_IDLER_help = "Move the MMU Idler"
    def cmd_MMU_MOVE_IDLER(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            raise gcmd.error("Integer VALUE has to be entered")

        positions = self.mmu_variables["idler"]
        positions.append(self.mmu_variables["idler_home_position"]) # -1 = Home Position / Out of the way

        if not self.locked:
            if self.homed:
                self.gcode.run_script_from_command("MANUAL_STEPPER STEPPER=idler_stepper MOVE=%s" % (positions[tool]))
                self.idler_position = tool
                if tool == -1:
                    self.unsync_extruder_steppers()
                else:
                    self.sync_extruder_steppers()
            else:
                raise gcmd.error("Did not move idler, MMU is not homed.")
        else:
            raise gcmd.error("Did not move idler, MMU is locked.")

    cmd_MMU_MOVE_SELECTOR_help = "Move the MMU Selector"
    def cmd_MMU_MOVE_SELECTOR(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            raise gcmd.error("Integer VALUE has to be entered")

        positions = self.mmu_variables["selector"]
        positions.append(self.mmu_variables["selector_home_position"]) # -1 = Home Position / Out of the way

        if not self.locked:
            if self.homed:
                self.gcode.run_script_from_command("MANUAL_STEPPER STEPPER=selector_stepper MOVE=%s" % (positions[tool]))
                self.selector_position = tool
            else:
                raise gcmd.error("Did not move selector, MMU is not homed.")
        else:
            raise gcmd.error("Did not move selector, MMU is locked.")

    cmd_M702_help = "Unload filament if inserted into the IR sensor"
    def cmd_M702(self, gcmd):
        self.gcode.run_script_from_command("G91")
        self.gcode.run_script_from_command("G1 Z%s" % (self.mmu_variables["pause_z"]))
        sleep(1)
        self.gcode.run_script_from_command("G90")
        self.gcode.run_script_from_command("G1 X%s Y%s F3000" % (self.mmu_variables["pause_x"], self.mmu_variables["pause_y"]))
        self.cmd_MMU_UT(gcmd)
        if not self.finda_sensor_state():
            gcmd.respond_info("M702 ok ...")
        else:
            raise gcmd.error("M702 Error !!!")

    cmd_MMU_HOME_help = "Homes all MMU Axes if not already homed, ejects filament before"
    def cmd_MMU_HOME(self, gcmd):
        if not self.homed:
            self.cmd_MMU_HOME_FORCE(gcmd)
        else:
            gcmd.respond_info("MMU already homed, unlocking.")
            self.cmd_MMU_UNLOCK(gcmd)

    cmd_MMU_HOME_FORCE_help = "Forces Homing of all MMU axes, ejects filament before"
    def cmd_MMU_HOME_FORCE(self, gcmd):
        self.ir_sensor.sensor_enabled = False
        gcmd.respond_info("Homing MMU ...")        
        if not self.locked:
            if self.ir_sensor_state():
                gcmd.respond_info("Filament in extruder, trying to eject it ..")
                self.gcode.run_script_from_command("MMU_UNLOAD_FILAMENT_IN_EXTRUDER")
            self.gcode.run_script_from_command("_MMU_IS_FILAMENT_STUCK_IN_EXTRUDER")
            self.gcode.run_script_from_command("MMU_ENDSTOPS_STATUS")

            if bool(self.finda.runout_helper.filament_present):
                self.cmd_MMU_UNLOAD_FILAMENT_TO_FINDA(gcmd)
                self.gcode.run_script_from_command("_IS_FILAMENT_STUCK_IN_FINDA")
        self.cmd_MMU_HOME_ONLY(gcmd)

    cmd_MMU_HOME_ONLY_help = "Home the MMU without Ejecting before"
    def cmd_MMU_HOME_ONLY(self, gcmd):
        if not self.locked:
            self.gcode.run_script_from_command("MMU_HOME_IDLER")
            self.gcode.run_script_from_command("MMU_HOME_SELECTOR")
            self.gcode.run_script_from_command("MANUAL_STEPPER STEPPER=idler_stepper MOVE=0")
            self.cmd_MMU_UNSELECT_TOOL(gcmd)
            self.gcode.run_script_from_command("M400")
            if self.led_enabled:
                self.gcode.run_script_from_command("LEDHOMEOK")
            self.homed = True
            gcmd.respond_info("Homing MMU ended ...")
        else:
            if self.led_enabled:
                self.gcode.run_script_from_command("LEDHOMENOK")
            raise gcmd.error("Homing MMU failed, MMU is paused, unlock it ...")

    cmd_MMU_UNLOCK_help = "Park the idler, stop the delayed stop of the heater"
    def cmd_MMU_UNLOCK(self, gcmd):
        gcmd.respond_info("Unlocking MMU")
        self.gcode.run_script_from_command("MMU_HOME_IDLER")
        if self.locked:
            self.locked = False
            self.gcode.run_script_from_command("MMU_HOME_IDLER")
            self.gcode.run_script_from_command("UPDATE_DELAYED_GCODE ID=disable_heater DURATION=0")
            extruder_temp = int(self.printer.lookup_object("gcode_macro MMU_PAUSE").variables["extruder_temp"])
            gcmd.respond_info("Waiting for MMU Pause Extruder temperature. (%s°C)" % (extruder_temp))
            self.gcode.run_script_from_command("M109 S%s" % (extruder_temp))

    cmd_MMU_RESUME_help = "Macro to CORRECTLY RESUME with MMU check."
    def cmd_MMU_RESUME(self, gcmd):
        if not self.locked:
            if self.ir_sensor_state():
                gcmd.respond_info("Resuming print")
                self.gcode.run_script_from_command("RESUME")
            else:
                raise gcmd.error("Filament not in extruder, could not resume")
        else:
            raise gcmd.error("MMU is in locked state - execute MMU_UNLOCK before resuming")

    cmd_MMU_CUT_FILAMENT_help = "Cuts Filament of the given tool VALUE (0-4)"
    def cmd_MMU_CUT_FILAMENT(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            raise gcmd.error("Integer VALUE has to be entered")

        if not 0 <= tool <= 4:
            raise gcmd.error("VALUE not between 0 and 4")

        gcmd.respond_info("Cutting Filament %s" % (tool))
        if self.selector_position != tool+1:
            if self.idler_position != tool:
                self.cmd_MMU_MOVE_IDLER(gcmd)
            if tool != 4:
                self.cmd_MMU_MOVE_SELECTOR({"VALUE":tool+1})
            else:
                self.cmd_MMU_MOVE_SELECTOR({"VALUE":-1})
        self.extrude(8, 1200)
        self.gcode.run_script_from_command("G92 E0")
        self.gcode.run_script_from_command("SET_TMC_CURRENT STEPPER=selector_stepper CURRENT=1.00 HOLDCURRENT=0.400")
        self.gcode.run_script_from_command("INIT_TMC STEPPER=selector_stepper")
        self.cmd_MMU_MOVE_SELECTOR({"VALUE": 0})
        self.gcode.run_script_from_command("SET_TMC_CURRENT STEPPER=selector_stepper CURRENT=0.400 HOLDCURRENT=0.200")
        self.gcode.run_script_from_command("INIT_TMC STEPPER=selector_stepper")
        self.gcode.run_script_from_command("MMU_HOME_SELECTOR")
        self.cmd_MMU_MOVE_SELECTOR(gcmd)

def load_config(config):
    return Mmu2s(config)