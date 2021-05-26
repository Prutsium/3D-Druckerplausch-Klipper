This is a new approach to use the MMU as the basis from Kakou was to restricted

User settings to do:
variable_bowden_load_length1: 505
variable_bowden_load_length2: 5
variable_bowden_unload_length: 520
variable_load_in_extruder: 52 # how much filament to load into extruder
variable_unload_in_extruder1: 32 
variable_unload_in_extruder2: 50


Dont forget to update your start Gcode in SuperSlicer and make sure it exports Klipper Gcode.
SET_GCODE_VARIABLE MACRO=START_PRINT_MMU VARIABLE=BED_TEMP VALUE=[first_layer_bed_temperature]
SET_GCODE_VARIABLE MACRO=START_PRINT_MMU VARIABLE=EXTRUDER_TEMP VALUE=[first_layer_temperature]
SET_GCODE_VARIABLE MACRO=START_PRINT_MMU VARIABLE=LOAD VALUE=[initial_tool]
START_PRINT_MMU

And as end print Gcode: END_PRINT_MMU
