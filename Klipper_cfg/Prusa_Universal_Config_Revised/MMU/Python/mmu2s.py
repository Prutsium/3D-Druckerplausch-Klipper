# Major parts from https://github.com/kakou-fr/mmu2_1S_klipper_config and https://github.com/EtteGit/EnragedRabbitProject
# But modified to our needs

# setup:
# ln -s ~/klipper_config/MMU/Python/mmu2s.py ~/klipper/klippy/extras/mmu2s.py

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

        """
        for method in [func for func in dir(self) if callable(getattr(self, func)) and func.startswith("cmd_MMU_")]:
            self.gcode.register_command(method.replace("cmd_", ""), getattr(self, method), desc=getattr(self, method + "_help"))
        """

        self.gcode.register_command("MMU_LOAD_FILAMENT_TO_FINDA", self.cmd_MMU_LOAD_FILAMENT_TO_FINDA, desc=self.cmd_MMU_LOAD_FILAMENT_TO_FINDA_help)
        self.gcode.register_command("MMU_LOAD_FILAMENT_TO_EXTRUDER", self.cmd_MMU_LOAD_FILAMENT_TO_EXTRUDER, desc=self.cmd_MMU_LOAD_FILAMENT_TO_EXTRUDER_help)
        self.gcode.register_command("MMU_UNLOAD_FILAMENT_TO_FINDA", self.cmd_MMU_UNLOAD_FILAMENT_TO_FINDA, desc=self.cmd_MMU_UNLOAD_FILAMENT_TO_FINDA_help)
        self.gcode.register_command("MMU_CHANGE_TOOL", self.cmd_MMU_CHANGE_TOOL, desc=self.cmd_MMU_CHANGE_TOOL_help)
        self.gcode.register_command("MMU_MOVE_IDLER", self.cmd_MMU_MOVE_IDLER, desc=self.cmd_MMU_MOVE_IDLER_help)
        self.gcode.register_command("M702", self.cmd_M702, desc=self.cmd_M702_help)
        self.gcode.register_command("MMU_HOME", self.cmd_MMU_HOME, desc=self.cmd_MMU_HOME_help)
        self.gcode.register_command("MMU_HOME_IDLER", self.cmd_MMU_HOME_IDLER, desc=self.cmd_MMU_HOME_IDLER_help)
        self.gcode.register_command("MMU_HOME_SELECTOR", self.cmd_MMU_HOME_SELECTOR, desc=self.cmd_MMU_HOME_SELECTOR_help)
        self.gcode.register_command("MMU_UNLOCK", self.cmd_MMU_UNLOCK, desc=self.cmd_MMU_UNLOCK_help)
        self.gcode.register_command("MMU_CUT_FILAMENT", self.cmd_MMU_CUT_FILAMENT, desc=self.cmd_MMU_CUT_FILAMENT_help)
        self.gcode.register_command("MMU_TEST_LOAD", self.cmd_MMU_TEST_LOAD, desc=self.cmd_MMU_TEST_LOAD_help)

    def handle_connect(self):
        self.toolhead = self.printer.lookup_object('toolhead')
        for manual_stepper in self.printer.lookup_objects('manual_stepper'):
            rail_name = manual_stepper[1].get_steppers()[0].get_name()
            if rail_name == 'manual_stepper selector_stepper':
                self.selector_stepper = manual_stepper[1]
            if rail_name == 'manual_stepper idler_stepper':
                self.idler_stepper = manual_stepper[1]
        if self.selector_stepper is None:
            self.beep_and_pause("Manual_stepper selector_stepper must be specified")
        if self.idler_stepper is None:
            self.beep_and_pause("Manual_stepper idler_stepper must be specified")

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

    def extrude(self, length, feedrate):
        if length and feedrate:
            self.gcode.run_script_from_command("G92 E0")
            self.gcode.run_script_from_command("G1 E%s F%s" % (length, feedrate))
            self.gcode.run_script_from_command("G92 E0")
            self.gcode.run_script_from_command("M400")

    def retract(self, length, feedrate):
        if length and feedrate:
            self.extrude(-length, feedrate)

    def move_stepper(self, stepper, position, homing = False):
        if homing:
            stepper.do_homing_move(position, stepper.velocity, stepper.accel, True, True)
        else:
            stepper.do_move(position, stepper.velocity, stepper.accel, 0)
        self.gcode.run_script_from_command("M400")

    def load_filament(self, tool):
        if not self.locked:
            if self.finda_sensor_state():
                self.beep_and_pause("Filament in Finda - not changing anything!")
            if self.ir_sensor_state():
                self.beep_and_pause("Filament in Extruder - not changing anything!")
            self.gcode.respond_info("LT %s" % (tool))
            self.select_tool(tool)
            self.cmd_MMU_LOAD_FILAMENT_TO_EXTRUDER({"VALUE": tool})
            self.load_filament_into_nozzle()
            self.unselect_tool()
        else:
            self.beep_and_pause("NO LT MADE, MMU is locked")

    def load_filament_into_nozzle(self):
        hotend_length = self.common_variables.get("mmu_hotend_length", -1)
        if hotend_length == -1:
            self.gcode.respond_info("Hotend length for loading check not configured. Using and saving: 50mm")
            hotend_length = 50
            self.gcode.run_script_from_command("SAVE_VARIABLE VARIABLE=mmu_hotend_length VALUE=%s" % (hotend_length))

        if self.ir_sensor_state():
            self.extrude(hotend_length, 10*60)
            self.retract(hotend_length-2, 20*60)

            if self.ir_sensor_state():
                self.extrude(2, 10*60)
                self.gcode.respond_info("Check load filament to nozzle successful")
            else:
                self.beep_and_pause("Hotend possibly clogged!!")

    def unload_filament(self):
        if not self.locked:
            if self.selector_position != -1:
                self.gcode.respond_info("UT %s" % (self.idler_position))
                #self.gcode.run_script_from_command("_MMU_FORM_TIP")
                self.select_tool(self.selector_position)
                self.cmd_MMU_UNLOAD_FILAMENT_TO_FINDA({})
                self.unselect_tool()
            else:
                if self.finda_sensor_state() or self.ir_sensor_state():
                    self.beep_and_pause("NO UT MADE, no tool activated, but filament in finda/extruder!!!")
                else:
                    self.gcode.respond_info("No filament in finda/extruder. No unloading needed.")
        else:
            self.beep_and_pause("NO UT MADE, MMU is locked")

    def select_tool(self, tool):
        if not self.locked:
            if self.homed:
                self.gcode.respond_info("Select Tool %s" % (tool))
                self.cmd_MMU_MOVE_IDLER({"VALUE": tool})
                self.cmd_MMU_MOVE_SELECTOR({"VALUE": tool})
                if self.led_enabled:
                    self.gcode.run_script_from_command("LED_MMU VALUE=%s" % (tool))
                self.gcode.respond_info("Tool %s enabled" % (tool))
            else:
                self.beep_and_pause("Selected no tool, MMU is not homed")
        else:
            self.beep_and_pause("Selected no tool, MMU is locked")

    def unselect_tool(self):
        if not self.locked:
            if self.homed:
                self.cmd_MMU_MOVE_IDLER({"VALUE": -1})
            else:
                self.beep_and_pause("Did not unselect tool, MMU is not homed.")
        else:
            self.beep_and_pause("Did not unselect tool, MMU is locked.")

    def beep_and_pause(self, error_message):
        self.gcode.respond_info(error_message)
        idle_timeout = self.printer.lookup_object("idle_timeout")
        if idle_timeout.get_status(0)["state"] == "Printing":
            self.gcode.run_script_from_command("M300")
            self.gcode.run_script_from_command("M300")
            self.gcode.run_script_from_command("M300")
            self.gcode.run_script_from_command("PAUSE")

###########################################
# GCode Section of the class              #
###########################################

    cmd_MMU_LOAD_FILAMENT_TO_FINDA_help = "Load filament until Finda registers it"
    def cmd_MMU_LOAD_FILAMENT_TO_FINDA(self, gcmd):
        stepsize = 10
        loaded = False

        if self.finda_sensor_state():
            self.gcode.respond_info("Filament already in finda")
        else:
            self.gcode.run_script_from_command("G92 E0")
            for i in range (0, 200, stepsize):
                if not self.finda_sensor_state():
                    self.gcode.respond_info("Loaded %s mm of filament to finda." % (i))
                    self.extrude(stepsize, 40*60)
                else:
                    self.extrude(stepsize, 40*60)
                    loaded = True
                    break
            self.gcode.run_script_from_command("G92 E0")
            if loaded:
                self.gcode.respond_info("Filament loaded successfully to finda")  
            else:
                self.gcode.respond_info("FILAMENT NOT IN FINDA!!!")  

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
                self.beep_and_pause("Filament not in Finda!")

        if self.ir_sensor_state():
            self.gcode.respond_info("Filament already in Extruder!")
            return
        else:
            self.gcode.run_script_from_command("G92 E0")
            
            if bowden_length == -1:    
                for i in range (0, 700, stepsize):
                    if not self.ir_sensor_state():
                        self.gcode.respond_info("Approx. Loading: %s mm of filament to Extruder." % (i))
                        self.extrude(stepsize, 2400)
                    else:
                        loaded = True
                        final_load_startvalue = i - stepsize - 5
                        self.retract(stepsize+5, 2400)
                        break
                if not loaded:
                    self.beep_and_pause("Extruded %s mm Filament, but nothing in Extruder!!" % (i))  
                    return
            else:
                final_load_startvalue = bowden_length*0.85
                self.gcode.respond_info("Fast Loading with saved variable: %s mm of filament to Extruder." % (final_load_startvalue))
                self.extrude(final_load_startvalue, 3000)

            for j in range (0, stepsize * 10, smallsteps):
                if not self.ir_sensor_state():
                    self.gcode.respond_info("Final Loading: %s mm of filament to Extruder." % (final_load_startvalue + j))
                    self.extrude(smallsteps, 600)
                else:
                    self.extrude(smallsteps, 600)
                    loaded = True
                    final_load_endvalue = final_load_startvalue + j
                    break

            self.gcode.run_script_from_command("G92 E0")
            if loaded:
                self.gcode.respond_info("Filament loaded successfully to Extruder (%s mm)" % (final_load_endvalue))
                if bowden_length == -1:
                    self.gcode.run_script_from_command("SAVE_VARIABLE VARIABLE=mmu_bowden_length VALUE=%s" % (final_load_endvalue))
            else:
                self.gcode.respond_info("FILAMENT NOT IN EXTRUDER!!!")  

    cmd_MMU_UNLOAD_FILAMENT_TO_FINDA_help = "Unload from extruder to the FINDA"
    def cmd_MMU_UNLOAD_FILAMENT_TO_FINDA(self, gcmd):
        bowden_length = self.common_variables.get("mmu_bowden_length", -1)
        finda_unload = self.mmu_variables.get("finda_unload_length", 25)
        stepsize = 10

        if not self.locked:
            if self.idler_position != -1 or not self.homed:
                if self.ir_sensor_state():
                    self.gcode.respond_info("Unloading filament from extruder to FINDA ...")
                    self.retract(bowden_length*0.85, 3000)
                    
                if self.finda_sensor_state():
                    self.gcode.respond_info("Unloading filament from FINDA ...")
                    for i in range (0, 600, stepsize):
                        if self.finda_sensor_state():
                            self.gcode.respond_info("Unloaded %s mm of filament to finda." % (i))
                            self.retract(stepsize, 40*60)
                        else:
                            break
                self.retract(finda_unload, 1000)
                self.gcode.respond_info("Unloading done from FINDA to extruder")
            else:
                self.gcode.respond_info("Cannot unload from extruder to FINDA, idler not in needed position !!")  
                return
        else:
            self.gcode.respond_info("MMU is paused!!")  
            return

    cmd_MMU_CHANGE_TOOL_help = "Changes the Extruder to the given tool VALUE (0-4)"
    def cmd_MMU_CHANGE_TOOL(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            self.beep_and_pause("Integer VALUE has to be entered")

        if not 0 <= tool <= 4:
            self.beep_and_pause("VALUE not between 0 and 4")

        if self.selector_position != tool:
            self.gcode.respond_info("Changing Tool to %s" % (tool))
            self.unload_filament()
            self.load_filament(tool)
            self.gcode.run_script_from_command("G90")
            self.gcode.run_script_from_command("M400")
        else:
            self.gcode.respond_info("No change needed. Tool %s already active." % (tool))

    cmd_MMU_MOVE_IDLER_help = "Move the MMU Idler"
    def cmd_MMU_MOVE_IDLER(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            self.beep_and_pause("Integer VALUE has to be entered")

        positions = self.mmu_variables["idler"]
        positions.append(self.mmu_variables["idler_home_position"]) # -1 = Home Position / Out of the way

        if not self.locked:
            if not self.homed:
                self.cmd_MMU_HOME_IDLER(gcmd)
            self.move_stepper(self.idler_stepper, positions[tool], False)
            self.idler_position = tool
            if tool == -1:
                self.unsync_extruder_steppers()
            else:
                self.sync_extruder_steppers()
        else:
            self.beep_and_pause("Did not move idler, MMU is locked.")

    cmd_MMU_MOVE_SELECTOR_help = "Move the MMU Selector"
    def cmd_MMU_MOVE_SELECTOR(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            self.beep_and_pause("Integer VALUE has to be entered")

        positions = self.mmu_variables["selector"]
        positions.append(self.mmu_variables["selector_home_position"]) # -1 = Home Position / Out of the way

        if not self.locked:
            if self.homed:
                self.move_stepper(self.selector_stepper, positions[tool], False)
                self.selector_position = tool
            else:
                self.beep_and_pause("Did not move selector, MMU is not homed.")
        else:
            self.beep_and_pause("Did not move selector, MMU is locked.")

    cmd_M702_help = "Unload filament if inserted into the IR sensor"
    def cmd_M702(self, gcmd):
        self.gcode.run_script_from_command("G91")
        self.gcode.run_script_from_command("G1 Z%s" % (self.mmu_variables["pause_z"]))
        sleep(1)
        self.gcode.run_script_from_command("G90")
        self.gcode.run_script_from_command("G1 X%s Y%s F3000" % (self.mmu_variables["pause_x"], self.mmu_variables["pause_y"]))
        self.unload_filament()
        if not self.finda_sensor_state():
            self.gcode.respond_info("M702 ok ...")
        else:
            self.beep_and_pause("M702 Error !!!")

    cmd_MMU_HOME_help = "Homes all MMU Axes if not already homed, ejects filament before"
    def cmd_MMU_HOME(self, gcmd):
        try:
            force = bool(gcmd.get('FORCE', 0))
        except ValueError:
            self.beep_and_pause("FORCE value has to be 0 or 1")

        if not self.homed or force:
            self.ir_sensor.sensor_enabled = False
                
            if not self.locked:
                if self.ir_sensor_state():
                    self.gcode.respond_info("Filament in extruder, trying to eject it ..")
                    self.sync_extruder_steppers() # hopefully the idler is in correct position
                    self.gcode.run_script_from_command("_MMU_FORM_TIP")
                    self.cmd_MMU_UNLOAD_FILAMENT_TO_FINDA(gcmd)
            else:
                if self.led_enabled:
                    self.gcode.run_script_from_command("LEDHOMENOK")
                self.beep_and_pause("MMU is locked, issue MMU_UNLOCK first!!!")
            if not self.finda_sensor_state():
                self.gcode.respond_info("Homing MMU ...")
                self.cmd_MMU_HOME_IDLER(gcmd)
                self.move_stepper(self.idler_stepper, 0, False)
                self.cmd_MMU_HOME_SELECTOR(gcmd)
                self.homed = True
                self.unselect_tool()
                self.gcode.run_script_from_command("M400")
                if self.led_enabled:
                    self.gcode.run_script_from_command("LEDHOMEOK")
                self.gcode.respond_info("Homing MMU ended ...")   
            else:
                if self.led_enabled:
                    self.gcode.run_script_from_command("LEDHOMENOK")
                self.beep_and_pause("Filament in finda. Cancelling homing!!!")
        else:
            if self.led_enabled:
                    self.gcode.run_script_from_command("LEDHOMENOK")
            self.gcode.respond_info("MMU already homed, unlocking & homing idler only. If you want to home anyway, enter FORCE=1 !")
            self.cmd_MMU_UNLOCK(gcmd)

    cmd_MMU_HOME_IDLER_help = "Home the MMU Idler"
    def cmd_MMU_HOME_IDLER(self, gcmd):
        self.gcode.respond_info("Homing idler")
        self.idler_stepper.do_set_position(0)
        self.move_stepper(self.idler_stepper, 7, False)
        self.move_stepper(self.idler_stepper, -95, True)
        self.move_stepper(self.idler_stepper, 2, False)
        self.move_stepper(self.idler_stepper, self.mmu_variables["idler_home_position"], False)

    cmd_MMU_HOME_SELECTOR_help = "Home the MMU Selector"
    def cmd_MMU_HOME_SELECTOR(self, gcmd):
        self.gcode.respond_info("Homing Selector")
        self.selector_stepper.do_set_position(0)
        self.move_stepper(self.selector_stepper, -90, True)
        self.selector_stepper.do_set_position(0)

    cmd_MMU_UNLOCK_help = "Park the idler, unlock the MMU"
    def cmd_MMU_UNLOCK(self, gcmd):
        self.gcode.respond_info("Unlocking MMU")
        self.cmd_MMU_HOME_IDLER(gcmd)
        if self.locked:
            self.locked = False

    cmd_MMU_CUT_FILAMENT_help = "Cuts Filament of the given tool VALUE (0-4)"
    def cmd_MMU_CUT_FILAMENT(self, gcmd):
        try:
            tool = int(gcmd.get('VALUE'))
        except ValueError:
            self.beep_and_pause("Integer VALUE has to be entered")

        if not 0 <= tool <= 4:
            self.beep_and_pause("VALUE not between 0 and 4")

        self.gcode.respond_info("Cutting Filament %s" % (tool))
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
        self.cmd_MMU_HOME_SELECTOR(gcmd)
        self.cmd_MMU_MOVE_SELECTOR(gcmd)

    cmd_MMU_TEST_LOAD_help = "Test loading of all filament slots 2 times (e.g. TOOLS=5, TESTS=1)"
    def cmd_MMU_TEST_LOAD(self, gcmd):
        self.gcode.run_script_from_command("G1 X100 Z100 F2000")
        #Slot Anzahl
        #Versuchsanzahl
        try:
            tool_count = int(gcmd.get('TOOLS'))
        except ValueError:
            self.beep_and_pause("Integer TOOLS count has to be entered")

        try:
            test_count = int(gcmd.get('TESTS'))
        except ValueError:
            self.beep_and_pause("Integer TESTS count has to be entered")

        for i in range(test_count):
            self.gcode.respond_info("Test No. %s / %s" % (i, test_count))
            for j in range(tool_count):
                self.cmd_MMU_CHANGE_TOOL({ "VALUE": j })
                self.extrude(30, 2000)

def load_config(config):
    return Mmu2s(config)
